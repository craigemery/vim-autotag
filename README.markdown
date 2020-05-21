autotag.vim
============

If you use ctags to make tags files of your source, it's nice to be able to re-run ctags on a source file when you save it.

However, using `ctags -a` will only change existing entries in a tags file or add new ones. It doesn't delete entries that no longer exist. Should you delete an entity from your source file that's represented by an entry in a tags file, that entry will remain after calling `ctags -a`.

This python function will do two things:

1) It will search for a tags file starting in the directory where your source file resides and moving up a directory at a time until it either finds one or runs out of directories to try.

2) Should it find a tags file, it will then delete all entries in said tags file referencing the source file you've just saved and then execute `ctags -a` on that source file using the relative path to the source file from the tags file.

This way, every time you save a file, your tags file will be seamlessly updated.

Installation
------------

Currently I suggest you use Vundle and install as a normal Bundle

From the Vim command-line

    :BundleInstall 'craigemery/vim-autotag'

And add to your ~/.vimrc

    Bundle 'craigemery/vim-autotag'

Or you can manually install
    cd
    git clone git://github.com/craigemery/vim-autotag.git
    cd ~/.vim/
    mkdir -p plugin
    cp ~/vim-autotag.git/plugin/* plugin/

### Install as a Pathogen bundle
```
git clone git://github.com/craigemery/vim-autotag.git ~/.vim/bundle/vim-autotag
```

Getting round other ctags limitations
-------------------------------------
ctags is very file name suffix driven. When the file has no suffix, ctags can fail to detect the file type.  
The easiest way to replicate this is when using a #! shebang. I've seen "#!/usr/bin/env python3" in a 
shebang not get detected by ctags.  
But Vim is better at this. So Vim's filetype buffer setting can help.  
So when the buffer being written has no suffix to th efile name then the Vim filetype value will be ued instead.  
So far I've only implemented "python" as one that is given to ctags --language-force=<here> as is.  
Other filetypes could be mapped. There's a dict in the AutTag class.  
To not map a filetype to a forced language kind, add the vim file type to the comma "," separated
list in autotagExcludeFiletypes.

Configuration
-------------
Autotag can be configured using the following global variables:

| Name | Purpose |
| ---- | ------- |
| `g:autotagExcludeSuffixes` | suffixes to not ctags on |
| `g:autotagExcludeFiletypes` | filetypes to not try & force a language choice on ctags |
| `g:autotagVerbosityLevel` | logging verbosity (as in Python logging module) |
| `g:autotagCtagsCmd` | name of ctags command |
| `g:autotagTagsFile` | name of tags file to look for |
| `g:autotagDisabled` | Disable autotag (enable by setting to any non-blank value) |
| `g:autotagStopAt` | stop looking for a tags file (and make one) at this directory (defaults to $HOME) |
| `g:autotagStartMethod` | Now AutoTag uses Python multiprocessing, the start method is an internal aspect that Python uses.

These can be overridden with buffer specific ones. b: instead of g:
Example:
```
let g:autotagTagsFile=".tags"
```

macOS, Python 3.8 and 'spawn'
-----------------------------
With the release of Python 3.8, the default start method for multiprocessing on macOS has become 'spawn'
At the time of writing there are issues with 'spawn' and I advise making AutoTag ask Python to use 'fork'
i.e. before loading the plugin:
```
let g:autotagStartMethod='fork'
```

Self-Promotion
--------------

Like autotag.vim? Follow the repository on
[GitHub](https://github.com/craigemery/vim-autotag) and vote for it on
[vim.org](http://www.vim.org/scripts/script.php?script_id=1343).  And if
you're feeling especially charitable, follow [craigemery] on
[GitHub](https://github.com/craigemery).

License
-------

Copyright (c) Craig Emery.  Distributed under the same terms as Vim itself.
See `:help license`.
