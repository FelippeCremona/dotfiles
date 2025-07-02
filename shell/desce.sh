#!/usr/bin/env zsh

cd ~/dotfiles/
git pull
cp .bashrc ~
cp .zshrc ~
cp .zprofile ~
cp -r shell ~/.config/
cp .tmux.conf ~
cp -r .tmuxinator ~
cp starship.toml ~/.config/
cp wezterm.lua /mnt/c/Arquivos\ de\ Programas/WezTerm/

pushd ~/.config/nvim/ && git pull

# Copia scripts e aplica permissionamento de execucao
mkdir -p ~/trabalho/programas/ 
cp -r ~/dotfiles/documentos/ ~/trabalho/programas/ 
find ~/trabalho/programas/documentos -type f -name "*.sh" -exec chmod +x {} \;
