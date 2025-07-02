#!/bin/zsh

find ~/.zshrc \
     ~/.npmrc \
     ~/.tmux.conf \
     ~/.config/nvim/ \
     ~/trabalho/programas/documentos/scripts/ \
     ~/.config/shell/ \
     ~/.tmuxinator/ \
     ~/mnt/c/Arquivos\ de\ Programas/WezTerm/wezterm.lua \
  -type d -name '.*' -prune -false -o -type f | fzf | xargs -r nvim
