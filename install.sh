echo "************ APT UPDATE ***********"
sudo apt update

echo "************ APT UPGRADE ***********"
sudo apt upgrade -y

echo "************ PYTHON3-PIP ***********"
sudo apt install python3-pip -y

echo "************ PYTHON2.7-minimal ***********"
sudo apt-get install -y python2.7-minimal
ln -s /usr/bin/python2.7 /usr/bin/python 

echo "************ RIPGREP ***********"
RIPGREP_VERSION=$(curl -s "https://api.github.com/repos/BurntSushi/ripgrep/releases/latest" | grep -Po '"tag_name": "\K[0-9.]+')
curl -Lo ripgrep.deb "https://github.com/BurntSushi/ripgrep/releases/latest/download/ripgrep_${RIPGREP_VERSION}_amd64.deb"
sudo apt install -y ./ripgrep.deb
rm -rf ripgrep.deb

echo "************ FZF ***********"
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf && ~/.fzf/install

# echo "************ OKCLI ***********"
# sudo pip install okcli

echo "************ UPDATE GIT ***********"
sudo add-apt-repository -y ppa:git-core/ppa
sudo apt-get update
sudo apt-get install git -y

echo "************ TMUXINATOR ***********"
sudo apt-get install -y tmuxinator

echo "************ ZOXIDE ***********"
curl -sS https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | bash

echo "************ SDKMAN ***********"
curl -s "https://get.sdkman.io" | bash
. ~/.sdkman/bin/sdkman-init.sh


echo "************ QUARKUS ***********"
sdk install quarkus

echo "************ JAVA 11.0.2 ***********"
sdk install java 11.0.2-open
echo "************ JAVA 17 ***********"
sdk install java 17-open
echo "************ JAVA 19 ***********"
sdk install java 19-open

echo "************ STARSHIP ***********"
curl -sS https://starship.rs/install.sh | sh

echo "************ NODE 14 ***********"
curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -
sudo apt -y install nodejs

echo "************ NPM ***********"
sudo apt install npm

echo "************ Altera Versão Node ************"
sudo npm install -g n
sudo n 14.20.1

echo "************ CLI Angular ************"
sudo npm install -g @angular/cli

echo "************ CARGO ***********"
sudo apt-get install cargo

# sudo apt-get install software-properties-common
echo "************ NEOVIM 8 ***********"
sudo add-apt-repository ppa:neovim-ppa/unstable -y
sudo apt-get install neovim -y
git clone https://github.com/FelippeCremona/nvim-config.git ~/.config/nvim

echo "************ LVIM ***********"
# bash <(curl -s https://raw.githubusercontent.com/lunarvim/lunarvim/master/utils/installer/install.sh)
# rm -rf ~/.config/lvim
# git clone https://github.com/FelippeCremona/lvim_config.git ~/.config/lvim

echo "************ LAZYGIT ***********"
curl -Lo lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
sudo tar xf lazygit.tar.gz -C /usr/local/bin lazygit
rm lazygit.tar.gz

echo "************ DIFF-SO-FANCY ***********"
npm i diff-so-fancy


echo "************ RUST ***********"
curl https://sh.rustup.rs -sSf | sh

echo "************ EXA ***********"
wget -c https://github.com/ogham/exa/releases/download/v0.8.0/exa-linux-x86_64-0.8.0.zip
unzip exa-linux-x86_64-0.8.0.zip
sudo mv exa-linux-x86_64 /usr/local/bin/exa
rm ~/exa-linux-x86_64-0.8.0.zip

echo "************ ATUALIZA DOTFILES ***********"
./restore_dotfiles.sh
