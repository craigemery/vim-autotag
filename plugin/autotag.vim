" (c) Craig Emery 2016
"
" Increment the number below for a dynamic #include guard
let s:autotag_vim_version=1

if exists("g:autotag_vim_version_sourced")
   if s:autotag_vim_version == g:autotag_vim_version_sourced
      finish
   endif
endif

let g:autotag_vim_version_sourced=s:autotag_vim_version

" This file supplies automatic tag regeneration when saving files
" There's a problem with ctags when run with -a (append)
" ctags doesn't remove entries for the supplied source file that no longer exist
" so this script (implemented in python) finds a tags file for the file vim has
" just saved, removes all entries for that source file and *then* runs ctags -a

if has("python") || has("python3")
   if has("python")
      python  import sys, os, vim
      python  sys.path.insert(0, os.path.dirname(vim.eval('expand("<sfile>")')))
      python  from __future__ import print_function
      python  from autotag import autotag
   else
      python3 import sys, os, vim
      python3 sys.path.insert(0, os.path.dirname(vim.eval('expand("<sfile>")')))
      python3 from autotag import autotag
   endif

   function! AutoTag()
      if has("python")
         python  autotag()
      else
         python3 autotag()
      endif
      if exists(":TlistUpdate")
         TlistUpdate
      endif
   endfunction

   function! AutoTagDebug()
      new
      file autotag_debug
      setlocal buftype=nowrite
      setlocal bufhidden=delete
      setlocal noswapfile
      normal 
   endfunction

   augroup autotag
      au!
      autocmd BufWritePost,FileWritePost * call AutoTag ()
   augroup END

endif " has("python") or has("python3")

" vim:shiftwidth=3:ts=3
