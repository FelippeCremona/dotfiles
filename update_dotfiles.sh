git clone https://github.com/FelippeCremona/dotfiles.git ~/dotfiles
cp ~/.bashrc .
cp ~/.tmux.conf .
cp -r ~/.tmuxinator .
cp ~/.config/starship.toml .
git add .
git commit -m "atualizando"
git push
rm -rf ~/dotfiles
