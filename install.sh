echo "************ APT UPDATE ***********"
sudo apt update

echo "************ PYTHON3-PIP ***********"
sudo apt install python3-pip

echo "************ RIPGREP ***********"
sudo apt-get install ripgrep

echo "************ FZF ***********"
sudo apt install fzf

echo "************ OKCLI ***********"
sudo pip install okcli


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

echo "************ CARGO ***********"
sudo apt-get install cargo

# sudo apt-get install software-properties-common
echo "************ NEOVIM 8 ***********"
sudo add-apt-repository ppa:neovim-ppa/unstable
sudo apt-get install neovim

echo "************ LVIM ***********"
bash <(curl -s https://raw.githubusercontent.com/lunarvim/lunarvim/master/utils/installer/install.sh)
rm -rf ~/.config/lvim
git clone https://github.com/FelippeCremona/lvim_config.git ~/.config/lvim

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

