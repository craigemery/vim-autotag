"""
(c) Craig Emery 2017-2020
AutoTag.py
"""

from __future__ import print_function
import sys
import os
import fileinput
import logging
from collections import defaultdict
import subprocess
from traceback import format_exc
import multiprocessing as mp
from glob import glob
import vim  # pylint: disable=import-error

__all__ = ["autotag"]

# global vim config variables used (all are g:autotag<name>):
# name purpose
# ExcludeSuffixes suffixes to not ctags on
# VerbosityLevel logging verbosity (as in Python logging module)
# CtagsCmd name of ctags command
# TagsFile name of tags file to look for
# Disabled Disable autotag (enable by setting to any non-blank value)
# StopAt stop looking for a tags file (and make one) at this directory (defaults to $HOME)
GLOBALS_DEFAULTS = dict(ExcludeSuffixes="tml.xml.text.txt",
                        VerbosityLevel=logging.WARNING,
                        CtagsCmd="ctags",
                        TagsFile="tags",
                        TagsDir="",
                        Disabled=0,
                        StopAt=0,
                        StartMethod="")


def do_cmd(cmd, cwd):
    """ Abstract subprocess """
    proc = subprocess.Popen(cmd,
                            cwd=cwd,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    stdout = proc.communicate()[0]
    return stdout.split("\n")


def vim_global(name, kind=str):
    """ Get global variable from vim, cast it appropriately """
    ret = GLOBALS_DEFAULTS.get(name, None)
    try:
        vname = "autotag" + name
        v_buffer = "b:" + vname
        exists_buffer = (vim.eval("exists('%s')" % v_buffer) == "1")
        v_global = "g:" + vname
        exists_global = (vim.eval("exists('%s')" % v_global) == "1")
        if exists_buffer:
            ret = vim.eval(v_buffer)
        elif exists_global:
            ret = vim.eval(v_global)
        else:
            if isinstance(ret, int):
                vim.command("let %s=%s" % (v_global, ret))
            else:
                vim.command("let %s=\"%s\"" % (v_global, ret))
    finally:
        if kind == bool:
            ret = (ret in [1, "1", "true", "yes"])
        elif kind == int:
            try:
                val = int(ret)
            except TypeError:
                val = ret
            except ValueError:
                val = ret
            ret = val
        elif kind == str:
            ret = str(ret)
    return ret


def init_multiprocessing():
    """ Init multiprocessing, set_executable() & get the context we'll use """
    wanted_start_method = vim_global("StartMethod") or None
    used_start_method = mp.get_start_method()
    if wanted_start_method in mp.get_all_start_methods():
        used_start_method = wanted_start_method
    else:
        wanted_start_method = None
    # here wanted_start_method is either a valid method or None
    # used_start_method is what the module has as the default or our overriden value
    ret = mp.get_context(wanted_start_method)  # wanted_start_method might be None
    try:
        mp.set_executable
    except AttributeError:
        return ret
    if used_start_method == 'spawn':
        suff = os.path.splitext(sys.executable)[1]
        pat1 = "python*%s" % suff
        pat2 = os.path.join("bin", pat1)
        exes = glob(os.path.join(sys.exec_prefix, pat1)) + glob(os.path.join(sys.exec_prefix, pat2))
        if exes:
            win = [exe for exe in exes if exe.endswith("w%s" % suff)]
            if win:
                # In Windows pythonw.exe is best
                ret.set_executable(win[0])
            else:
                # This isn't great, for now pick the first one
                ret.set_executable(exes[0])
    return ret


CTX = init_multiprocessing()


class VimAppendHandler(logging.Handler):
    """ Logger handler that finds a buffer and appends the log message as a new line """
    def __init__(self, name):
        logging.Handler.__init__(self)
        self.__name = name
        self.__formatter = logging.Formatter()

    def __find_buffer(self):
        """ Look for the named buffer """
        for buff in vim.buffers:
            if buff and buff.name and buff.name.endswith(self.__name):
                yield buff

    def emit(self, record):
        """ Emit the logging message """
        for buff in self.__find_buffer():
            buff.append(self.__formatter.format(record))


def set_logger_verbosity():
    """ Set the verbosity of the logger """
    level = vim_global("VerbosityLevel", kind=int)
    LOGGER.setLevel(level)


def make_and_add_handler(logger, name):
    """ Make the handler and add it to the standard logger """
    ret = VimAppendHandler(name)
    logger.addHandler(ret)
    return ret


try:
    LOGGER
except NameError:
    DEBUG_NAME = "autotag_debug"
    LOGGER = logging.getLogger(DEBUG_NAME)
    HANDLER = make_and_add_handler(LOGGER, DEBUG_NAME)
    set_logger_verbosity()


class AutoTag():  # pylint: disable=too-many-instance-attributes
    """ Class that does auto ctags updating """
    LOG = LOGGER
    AUTOFILETYPES = ["python"]
    FILETYPES = {}

    def __init__(self):
        self.locks = {}
        self.tags = defaultdict(list)
        self.excludesuffix = ["." + s for s in vim_global("ExcludeSuffixes").split(".")]
        self.excludefiletype = vim_global("ExcludeFiletypes").split(",")
        set_logger_verbosity()
        self.sep_used_by_ctags = '/'
        self.ctags_cmd = vim_global("CtagsCmd")
        self.tags_file = str(vim_global("TagsFile"))
        self.tags_dir = str(vim_global("TagsDir"))
        self.parents = os.pardir * (len(os.path.split(self.tags_dir)) - 1)
        self.count = 0
        self.stop_at = vim_global("StopAt")

    def find_tag_file(self, source):
        """ Find the tag file that belongs to the source file """
        AutoTag.LOG.info('source = "%s"', source)
        (drive, fname) = os.path.splitdrive(source)
        ret = None
        while ret is None:
            fname = os.path.dirname(fname)
            AutoTag.LOG.info('drive = "%s", file = "%s"', drive, fname)
            tags_dir = os.path.join(drive, fname)
            tags_file = os.path.join(tags_dir, self.tags_dir, self.tags_file)
            AutoTag.LOG.info('testing tags_file "%s"', tags_file)
            if os.path.isfile(tags_file):
                stinf = os.stat(tags_file)
                if stinf:
                    size = getattr(stinf, 'st_size', None)
                    if size is None:
                        AutoTag.LOG.warning("Could not stat tags file %s", tags_file)
                        ret = ""
                ret = (fname, tags_file)
            elif tags_dir and tags_dir == self.stop_at:
                AutoTag.LOG.info("Reached %s. Making one %s", self.stop_at, tags_file)
                open(tags_file, 'wb').close()
                ret = (fname, tags_file)
                ret = ""
            elif not fname or fname == os.sep or fname == "//" or fname == "\\\\":
                AutoTag.LOG.info('bail (file = "%s")', fname)
                ret = ""
        return ret or None

    def add_source(self, source, filetype):
        """ Make a note of the source file, ignoring some etc """
        if not source:
            AutoTag.LOG.warning('No source')
            return
        if os.path.basename(source) == self.tags_file:
            AutoTag.LOG.info("Ignoring tags file %s", self.tags_file)
            return
        suff = os.path.splitext(source)[1]
        if suff:
            AutoTag.LOG.info("Source %s has suffix %s, so filetype doesn't count!", source, suff)
            filetype = None
        else:
            AutoTag.LOG.info("Source %s has no suffix, so filetype counts!", source)

        if suff in self.excludesuffix:
            AutoTag.LOG.info("Ignoring excluded suffix %s for file %s", suff, source)
            return
        if filetype in self.excludefiletype:
            AutoTag.LOG.info("Ignoring excluded filetype %s for file %s", filetype, source)
            return
        found = self.find_tag_file(source)
        if found:
            (tags_dir, tags_file) = found
            relative_source = os.path.splitdrive(source)[1][len(tags_dir):]
            if relative_source[0] == os.sep:
                relative_source = relative_source[1:]
            if os.sep != self.sep_used_by_ctags:
                relative_source = relative_source.replace(os.sep, self.sep_used_by_ctags)
            key = (tags_dir, tags_file, filetype)
            self.tags[key].append(relative_source)
            if key not in self.locks:
                self.locks[key] = CTX.Lock()

    @staticmethod
    def good_tag(line, excluded):
        """ Filter method for stripping tags """
        if line[0] == '!':
            return True
        fields = line.split('\t')
        AutoTag.LOG.log(1, "read tags line:%s", str(fields))
        if len(fields) > 3 and fields[1] not in excluded:
            return True
        return False

    def strip_tags(self, tags_file, sources):
        """ Strip all tags for a given source file """
        AutoTag.LOG.info("Stripping tags for %s from tags file %s", ",".join(sources), tags_file)
        backup = ".SAFE"
        try:
            with fileinput.FileInput(files=tags_file, inplace=True, backup=backup) as source:
                for line in source:
                    line = line.strip()
                    if self.good_tag(line, sources):
                        print(line)
        finally:
            try:
                os.unlink(tags_file + backup)
            except IOError:
                pass

    def _vim_ft_to_ctags_ft(self, name):
        """ convert vim filetype strings to ctags strings """
        if name in AutoTag.AUTOFILETYPES:
            return name
        return self.FILETYPES.get(name, None)

    def update_tags_file(self, key, sources):
        """ Strip all tags for the source file, then re-run ctags in append mode """
        (tags_dir, tags_file, filetype) = key
        lock = self.locks[key]
        if self.tags_dir:
            sources = [os.path.join(self.parents + s) for s in sources]
        cmd = [self.ctags_cmd]
        if self.tags_file:
            cmd += ["-f", self.tags_file]
        if filetype:
            ctags_filetype = self._vim_ft_to_ctags_ft(filetype)
            if ctags_filetype:
                cmd += ["--language-force=%s" % ctags_filetype]
        cmd += ["-a"]

        def is_file(src):
            """ inner """
            return os.path.isfile(os.path.join(tags_dir, self.tags_dir, src))

        srcs = list(filter(is_file, sources))
        if not srcs:
            return

        cmd += ['"%s"' % s for s in srcs]
        cmd = " ".join(cmd)
        with lock:
            self.strip_tags(tags_file, sources)
            AutoTag.LOG.log(1, "%s: %s", tags_dir, cmd)
            for line in do_cmd(cmd, self.tags_dir or tags_dir):
                AutoTag.LOG.log(10, line)

    def rebuild_tag_files(self):
        """ rebuild the tags file thread worker """
        for (key, sources) in self.tags.items():
            AutoTag.LOG.info('Process(%s, %s)', key, ",".join(sources))
            proc = CTX.Process(target=self.update_tags_file, args=(key, sources))
            proc.daemon = True
            proc.start()


def autotag():
    """ Do the work """
    try:
        if not vim_global("Disabled", bool):
            runner = AutoTag()
            runner.add_source(vim.eval("expand(\"%:p\")"), vim.eval("&ft"))
            runner.rebuild_tag_files()
    except Exception:  # pylint: disable=broad-except
        logging.warning(format_exc())
