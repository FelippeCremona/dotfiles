#!/bin/zsh

# Atualiza a lista de branches remotas
git fetch --prune

# Coleta branches locais com upstreams configurados
local_with_tracking=$(git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads | awk '$2 != "" {print $2}')

# Lista todas as branches (locais e remotas), exceto HEAD
all_branches=$(git branch --all | grep -v HEAD | sed 's/^[* ]*//')

# Remove duplicadas
all_branches=$(echo "$all_branches" | sort -u)

# Filtra as remotas que já têm local com upstream
filtered=$(echo "$all_branches" | while read branch; do
    # Verifica se é uma branch remota
    if [[ "$branch" =~ ^remotes/origin/ ]]; then
        # Remove prefixo
        base_branch="${branch#remotes/origin/}"
        # Verifica se essa branch já tem uma local com upstream
        if echo "$local_with_tracking" | grep -q "^origin/$base_branch$"; then
            continue  # Já existe uma local sincronizada, ignora
        fi
    fi
    echo "$branch"
done)

# Usa fzf para seleção
selected=$(echo "$filtered" | fzf --prompt="Selecione a branch: ")

# Se o usuário cancelou
[ -z "$selected" ] && echo "Nenhuma branch selecionada." && exit 0

# Remove prefixo 'remotes/origin/' se for branch remota
branch_name=$(echo "$selected" | sed 's#^remotes/origin/##')

# Faz checkout
git checkout "$branch_name"

git pull
