#!/bin/zsh

find \
  ~/trabalho/caixa/sistemas/sinaf/des/ \
  ~/trabalho/caixa/sistemas/simcn/des/ \
  ~/trabalho/caixa/sistemas/sicvr/des/ \
  -type d -name '.*' -prune -false -o \
  -type d -name 'node_modules' -prune -false -o \
  -type d -name 'target' -prune -false -o \
  -type f -name '*.class' -prune -false -o \
  -type f | fzf | xargs -r nvim
