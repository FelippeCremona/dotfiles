#!/bin/bash

# Função de pré-visualização para fzf
preview() {
    local file=$1
    svn diff --color=always "$file"
}

list_files() {
  svn status | awk '{print $2}'
}

# Listar arquivos modificados no repositório
files=$((list_files; echo "TODOS") | fzf --multi --preview 'preview {}' | awk '{print $1}')

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

# Listar os arquivos selecionados
echo "Arquivos selecionados para reverter:"
for filepath in $files; do
    echo "$filepath"
done

# Confirmar a reversão
read -p "Tem certeza que deseja reverter os arquivos selecionados? (s/n): " confirm
if [[ $confirm != "s" ]]; then
    echo "Reversão cancelada."
    exit 1
fi

# Reverter os arquivos selecionados
for filepath in $files; do
    svn revert "$filepath"
done

echo "Arquivos revertidos com sucesso."
