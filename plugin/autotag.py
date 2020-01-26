"""
(c) Craig Emery 2018
AutoTag.py
"""

from __future__ import print_function
import os
import os.path
import fileinput
import sys
import logging
from collections import defaultdict
import vim  # pylint: disable=import-error

# global vim config variables used (all are g:autotag<name>):
# name purpose
# maxTagsFileSize a cap on what size tag file to strip etc
# ExcludeSuffixes suffixes to not ctags on
# VerbosityLevel logging verbosity (as in Python logging module)
# CtagsCmd name of ctags command
# TagsFile name of tags file to look for
# Disabled Disable autotag (enable by setting to any non-blank value)
# StopAt stop looking for a tags file (and make one) at this directory (defaults to $HOME)
GLOBALS_DEFAULTS = dict(maxTagsFileSize=1024 * 1024 * 7,
                        ExcludeSuffixes="tml.xml.text.txt",
                        VerbosityLevel=logging.WARNING,
                        CtagsCmd="ctags",
                        TagsFile="tags",
                        TagsDir="",
                        Disabled=0,
                        StopAt=0)

# Just in case the ViM build you're using doesn't have subprocess
if sys.version < '2.4':
    def do_cmd(cmd, cwd):
        """ Python 2.3 has no subprocess """
        old_cwd = os.getcwd()
        os.chdir(cwd)
        ch_out = os.popen2(cmd)[1]  # pylint: disable=deprecated-method
        for _ in ch_out:
            pass
        os.chdir(old_cwd)

    from traceback import format_exception  # pylint: disable=wrong-import-position,wrong-import-order

    def format_exc():
        """ replace missing format_exc() """
        return ''.join(format_exception(*list(sys.exc_info())))

else:
    import subprocess  # pylint: disable=wrong-import-position,wrong-import-order

    KW = {"shell": True,
          "stdin": subprocess.PIPE,
          "stdout": subprocess.PIPE,
          "stderr": subprocess.PIPE}
    if sys.version >= '3':
        KW["universal_newlines"] = True

    def do_cmd(cmd, cwd):
        """ Abstract subprocess """
        proc = subprocess.Popen(cmd, cwd=cwd, **KW)
        stdout = proc.communicate()[0]
        return stdout.split("\n")

    from traceback import format_exc  # pylint: disable=wrong-import-position,wrong-import-order,ungrouped-imports


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
            ret = (ret not in [0, "0"])
        elif kind == int:
            ret = int(ret)
        elif kind == str:
            ret = str(ret)  # pylint: disable=redefined-variable-type
    return ret


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
                return buff

    def emit(self, record):
        """ Emit the logging message """
        buff = self.__find_buffer()
        if buff:
            buff.append(self.__formatter.format(record))


def set_logger_verbosity():
    """ Set the verbosity of the logger """
    try:
        level = int(vim_global("VerbosityLevel"))
    except ValueError:
        level = GLOBALS_DEFAULTS["VerbosityLevel"]
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


class AutoTag(object):  # pylint: disable=too-many-instance-attributes
    """ Class that does auto ctags updating """
    MAXTAGSFILESIZE = int(vim_global("maxTagsFileSize"))
    LOG = LOGGER

    def __init__(self):
        self.tags = defaultdict(list)
        self.excludesuffix = ["." + s for s in vim_global("ExcludeSuffixes").split(".")]
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
        while fname:
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
                        AutoTag.LOG.warn("Could not stat tags file %s", tags_file)
                        break
                    if size > AutoTag.MAXTAGSFILESIZE:
                        AutoTag.LOG.info("Ignoring too big tags file %s", tags_file)
                        break
                ret = (fname, tags_file)
                break
            elif tags_dir and tags_dir == self.stop_at:
                AutoTag.LOG.info("Reached %s. Making one %s", self.stop_at, tags_file)
                open(tags_file, 'wb').close()
                ret = (fname, tags_file)
                break
            elif not fname or fname == os.sep or fname == "//" or fname == "\\\\":
                AutoTag.LOG.info('bail (file = "%s")', fname)
                break
        return ret

    def add_source(self, source):
        """ Make a note of the source file, ignoring some etc """
        if not source:
            AutoTag.LOG.warn('No source')
            return
        if os.path.basename(source) == self.tags_file:
            AutoTag.LOG.info("Ignoring tags file %s", self.tags_file)
            return
        suff = os.path.splitext(source)[1]
        if suff in self.excludesuffix:
            AutoTag.LOG.info("Ignoring excluded suffix %s for file %s", source, suff)
            return
        found = self.find_tag_file(source)
        if found:
            (tags_dir, tags_file) = found  # pylint: disable=W0633
            relative_source = os.path.splitdrive(source)[1][len(tags_dir):]
            if relative_source[0] == os.sep:
                relative_source = relative_source[1:]
            if os.sep != self.sep_used_by_ctags:
                relative_source = relative_source.replace(os.sep, self.sep_used_by_ctags)
            self.tags[(tags_dir, tags_file)].append(relative_source)

    @staticmethod
    def good_tag(line, excluded):
        """ Filter method for stripping tags """
        if line.startswith(b'!'):
            return True
        else:
            fields = line.split(b'\t')
            AutoTag.LOG.log(1, "read tags line:%s", str(fields))
            if len(fields) > 3 and fields[1] not in excluded:
                return True
        return False

    def strip_tags(self, tags_file, sources):
        """ Strip all tags for a given source file """
        AutoTag.LOG.info("Stripping tags for %s from tags file %s", ",".join(sources), tags_file)
        backup = ".SAFE"
        source = fileinput.FileInput(files=tags_file, inplace=True, backup=backup, mode='rb')
        try:
            for line in source:
                line = line.strip()
                if self.good_tag(line, sources):
                    print(line.decode('utf-8', errors='replace'))
        finally:
            source.close()
            try:
                os.unlink(tags_file + backup)
            except StandardError:
                pass

    def update_tags_file(self, tags_dir, tags_file, sources):
        """ Strip all tags for the source file, then re-run ctags in append mode """
        if self.tags_dir:
            sources = [os.path.join(self.parents + s) for s in sources]
        self.strip_tags(tags_file, sources)
        if self.tags_file:
            cmd = "%s -f %s -a " % (self.ctags_cmd, self.tags_file)
        else:
            cmd = "%s -a " % (self.ctags_cmd,)
        for source in sources:
            if os.path.isfile(os.path.join(tags_dir, self.tags_dir, source)):
                cmd += ' "%s"' % source
        AutoTag.LOG.log(1, "%s: %s", tags_dir, cmd)
        for line in do_cmd(cmd, self.tags_dir or tags_dir):
            AutoTag.LOG.log(10, line)

    def rebuild_tag_files(self):
        """ rebuild the tags file """
        for ((tags_dir, tags_file), sources) in self.tags.items():
            self.update_tags_file(tags_dir, tags_file, sources)


def autotag():
    """ Do the work """
    try:
        if not vim_global("Disabled", bool):
            runner = AutoTag()
            runner.add_source(vim.eval("expand(\"%:p\")"))
            runner.rebuild_tag_files()
    except Exception:  # pylint: disable=W0703
        logging.warning(format_exc())
