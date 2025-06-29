#!/bin/zsh

# Atualiza a lista de branches remotas
git fetch --prune

# Lista branches locais e remotas, remove duplicações e formata
branches=$(git branch --all | grep -v HEAD | sed 's/^[* ]*//' | sort -u)

# Usa fzf para selecionar a branch
selected=$(echo "$branches" | fzf --prompt="Selecione a branch: ")

# Se o usuário cancelou
[ -z "$selected" ] && echo "Nenhuma branch selecionada." && exit 0

# Remove o prefixo 'remotes/origin/' caso exista
branch_name=$(echo "$selected" | sed 's#^remotes/origin/##')

# Faz checkout
git checkout "$branch_name"

# Atualiza a branch com o conteúdo do repositório remoto (se for uma tracking branch)
git pull
