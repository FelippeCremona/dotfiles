test ! -d "/home/cremona/dotfiles" && git clone https://github.com/FelippeCremona/dotfiles.git ~/dotfiles
cd ~/dotfiles
cp ~/.bashrc .
cp ~/.tmux.conf .
cp -r ~/.tmuxinator .
cp ~/.config/starship.toml .
cp -r ~/trabalho/programas/documentos/ .
cp /mnt/c/Arquivos\ de\ Programas/WezTerm/wezterm.lua .
git add .
git commit -m "atualizando"
BILHETE1=ghp_5wBYqy5Gtz2n
BILHETE2=Iwpnd4bKDCoBQpauC115jeft
git push https://$BILHETE1$BILHETE2@github.com/FelippeCremona/dotfiles.git
