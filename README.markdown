autotag.vim
============

If you use ctags to make tags files of your source, it's nice to be able to re-run ctags on a source file when you save it.

However, using ctags -a will only change existing entries in a tags file or add new ones. It doesn't delete entries that no longer exist. Should you delete an entity from your source file that's represented by an entry in a tags file, that entry will remain after calling ctags -a.

This python function will do two things:

1) It will search for a tags file starting in the directory where your source file resides and moving up a directory at a time until it either finds one or runs out of directories to try.

2) Should it find a tags file, it will then delete all entries in said tags file referencing the source file you've just saved and then execute ctags -a on that source file using the relative path to the source file from the tags file.

This way, every time you save a file, your tags file will be seamlessly updated.

Installation
------------

Currently I suggest you simply
    cd
    git clone git://github.com/craigemery/vim-autotag.git
    cd ~/.vim/
    mkdir -p plugin
    cp ~/vim-autotag.git/plugin/autotag.vim plugin/

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
