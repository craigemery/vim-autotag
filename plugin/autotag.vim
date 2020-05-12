"
" (c) Craig Emery 2017-2020
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
" so this script (implemented in Python) finds a tags file for the file vim has
" just saved, removes all entries for that source file and *then* runs ctags -a

if has("python3")
   python3 import sys, os, vim
   python3 sys.path.insert(0, os.path.dirname(vim.eval('expand("<sfile>")')))
   python3 import autotag

   function! AutoTag()
      if exists("b:netrw_method")
         return
      endif
      python3 autotag.autotag()
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

endif " has("python3")

" vim:shiftwidth=3:ts=3
