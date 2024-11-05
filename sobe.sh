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
git push
