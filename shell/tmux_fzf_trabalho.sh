#!/bin/zsh

find \
  ~/trabalho/caixa/sistemas/sinaf/des/ \
  ~/trabalho/caixa/sistemas/simcn/des/ \
  ~/trabalho/caixa/sistemas/sicvr/des/ \
  ~/trabalho/caixa/servidores/jboss-eap-7.1-simcn/standalone/configuration/standalone.xml \
  ~/trabalho/caixa/servidores/jboss-eap-7.1-sinaf/standalone/configuration/standalone.xml \
  ~/trabalho/caixa/servidores/jboss-eap-7.1-sinaf-acoes-lote/standalone/configuration/standalone.xml \
  -type d -name '.*' -prune -false -o \
  -type d -name 'node_modules' -prune -false -o \
  -type d -name 'target' -prune -false -o \
  -type f -name '*.class' -prune -false -o \
  -type f | fzf | xargs -r nvim
