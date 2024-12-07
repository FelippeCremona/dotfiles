#!/bin/bash

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # Sem cor

# Função para listar arquivos modificados
list_files() {
    svn status | awk '{print $2}'
}

# Adicionar opção de selecionar todos
files=$( (list_files; echo "TODOS") | fzf --multi --preview 'svn diff' | awk '{print $1}')

# Verificar se a opção "Selecionar todos" foi escolhida
echo $files
if [[ "$files" == "TODOS" ]]; then
    files=$(list_files)
fi

# Verificar se algum arquivo foi selecionado
if [ -z "$files" ]; then
    echo "Nenhum arquivo selecionado."
    exit 1
fi

# Listar os arquivos selecionados com cores e sinais
echo "Arquivos selecionados:"
for filepath in $files; do
    action=$(svn status "$filepath" | awk '{print $1}')
    if [[ $action == "?" ]]; then
        echo -e "${GREEN}+ $filepath${NC}" # Adicionado
    elif [[ $action == "!" ]]; then
        echo -e "${RED}- $filepath${NC}" # Excluído
    else
        echo -e "${YELLOW}~ $filepath${NC}" # Alterado
    fi
done

# Perguntar se deseja adicionar ou remover os arquivos selecionados
read -p "Deseja atualizar os arquivos selecionados? (s/n): " confirm
if [[ "$confirm" != "s" ]]; then
    echo "Operação cancelada."
    exit 1
fi

# Iterar sobre os arquivos selecionados
for filepath in $files; do
    action=$(svn status "$filepath" | awk '{print $1}')

    if [[ $action == "?" ]]; then
        # Adicionar arquivo não versionado
        svn add "$filepath"
    elif [[ $action == "!" ]]; then
        # Remover arquivo deletado
        svn delete "$filepath"
    fi
done

# Solicitar a mensagem de commit
read -p "Digite a mensagem de commit: " commit_message

# Commitar as mudanças com a mensagem fornecida
svn commit -m "$commit_message" $files
