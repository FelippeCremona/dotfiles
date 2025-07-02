echo "************ APT UPDATE ***********"
sudo apt update

echo "************ APT UPGRADE ***********"
sudo apt upgrade -y

echo "************ ZSH ***********"
sudo apt install zsh
chsh -s $(which zsh)
mkdir -p ~/.zsh

echo "************ PLUGINS ZSH ***********"
git clone https://github.com/zsh-users/zsh-syntax-highlighting ~/.zsh/zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-autosuggestions ~/.zsh/zsh-autosuggestions
git clone https://github.com/Aloxaf/fzf-tab ~/.zsh/fzf-tab

echo "************ PYTHON3-PIP ***********"
sudo apt install python3-pip -y

echo "************ PYTHON2.7-minimal ***********"
sudo apt-get install -y python2.7-minimal
ln -s /usr/bin/python2.7 /usr/bin/python 

echo "************ RIPGREP ***********"
sudo apt-get -y install ripgrep

echo "************ FZF ***********"
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf && ~/.fzf/install

echo "************ UPDATE GIT ***********"
sudo add-apt-repository -y ppa:git-core/ppa
sudo apt-get update
sudo apt-get install git -y

echo "************ UPDATE SVN ***********"
sudo apt-get install subversion

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

echo "************ Define java 17 como padrao ***********"
sdk default java 17-open 

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

echo "************ Install typescript language server ************"
sudo npm install -g typescript typescript-language-server 

echo "************ Install typescript language server ************"
sudo apt install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
sudo apt update
sudo apt install docker-ce

echo "************ CARGO ***********"
sudo apt-get install cargo

echo "************ NEOVIM ***********"
sudo add-apt-repository ppa:neovim-ppa/unstable -y
sudo apt-get install neovim -y
git clone https://github.com/FelippeCremona/nvim-config.git ~/.config/nvim

echo "************ HABILITA copiar e colar dentro NEOVIM ***********"
curl -sLo /tmp/win32yank.zip https://github.com/equalsraf/win32yank/releases/download/v0.0.4/win32yank-x64.zip
unzip -p /tmp/win32yank.zip win32yank.exe > /tmp/win32yank.exe
chmod +x /tmp/win32yank.exe
sudo mv /tmp/win32yank.exe /usr/local/bin/

echo "************ RUST ***********"
curl https://sh.rustup.rs -sSf | sh

echo "************ EZA ***********"
sudo apt install -y gpg wget
sudo mkdir -p /etc/apt/keyrings
wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | sudo gpg --dearmor -o /etc/apt/keyrings/gierens.gpg
echo "deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main" | sudo tee /etc/apt/sources.list.d/gierens.list

sudo apt install -y eza

echo "************ TIG ***********"
sudo apt install tig

echo "************ ATUALIZA DOTFILES ***********"
./desce.sh
