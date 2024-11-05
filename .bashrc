# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

### ARCHIVE EXTRACTION
# usage: ex <file>
ex ()
{
  if [ -f "$1" ] ; then
    case $1 in
      *.tar.bz2)   tar xjf $1   ;;
      *.tar.gz)    tar xzf $1   ;;
      *.bz2)       bunzip2 $1   ;;
      *.rar)       unrar x $1   ;;
      *.gz)        gunzip $1    ;;
      *.tar)       tar xf $1    ;;
      *.tbz2)      tar xjf $1   ;;
      *.tgz)       tar xzf $1   ;;
      *.zip)       unzip $1     ;;
      *.Z)         uncompress $1;;
      *.7z)        7z x $1      ;;
      *.deb)       ar x $1      ;;
      *.tar.xz)    tar xf $1    ;;
      *.tar.zst)   unzstd $1    ;;
      *)           echo "'$1' cannot be extracted via ex()" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
# shopt -s checkwinsize

# if [ -f ~/.bash_aliases ]; then
#     . ~/.bash_aliases
# fi

# Configuracao UBUNTU
alias sobe="~/dotfiles/sobe.sh"
alias desce="~/dotfiles/desce.sh"

# Tmuxinator
alias tm="tmuxinator $1"

# Comandos linux
alias ls="exa -lah --color=auto"
alias vi="nvim"
alias celar="clear"

alias findf="find . -type f -name $1"
alias findd="find . -type d -name $1"

alias ihost="cat /mnt/c/Windows/System32/drivers/etc/hosts | fzf | awk 'system(\"ping \" \$1)'"

# Comandos WSL
alias downloads="cd /mnt/c/Users/cremo/Downloads $1"
alias firefox="'/mnt/c/Program Files/Mozilla Firefox/firefox.exe'"

# Comandos git
alias gl="tig"
# alias glu="git log --date=iso --pretty='%C(Yellow)%h %C(reset)%cd %C(Cyan)%an: %C(reset)%s'"
alias gadd="git ls-files --others --exclude-standard -m | fzf --multi --preview 'git diff' | awk '{print \$1}' | xargs git add"
alias gus="git diff --name-only --cached | fzf --multi --preview 'git diff' | awk '{print \$1}' | xargs git restore --staged"

# Comandos svn
alias scommit="~/trabalho/programas/documentos/scripts/svn/svncommit.sh"
alias srevert="~/trabalho/programas/documentos/scripts/svn/svnrevert.sh"

# Comandos sistemas
alias sc="~/trabalho/programas/documentos/scripts/fzf_arquivos.sh"
alias docs="~/trabalho/programas/documentos/scripts/fzf_docs.sh"

# Comandos quarkus
alias quarkusd="quarkus dev -Dquarkus.console.enabled='false'"

# Comandos spring
alias springd="mvn spring-boot:run"
alias springinit="spring init -g=com -d=web,jpa,lombok,h2,devtools --build=maven -n=$1"

# Comandos node
alias caixa="sudo n v14.20.1 ;  cp ~/trabalho/programas/maven/settings_caixa.xml ~/.m2/settings.xml"
alias pessoal="sudo n v16.14.2 ; cp ~/trabalho/programas/maven/settings_padrao.xml ~/.m2/settings.xml"

eval "$(starship init bash)"

[ -f ~/.fzf.bash ] && source ~/.fzf.bash

# zoxide
export PATH=/home/cremona/.local/bin:$PATH
eval "$(zoxide init bash --cmd cd)"

export PATH="/opt/apache-maven-3.6.3/bin:$PATH"

# Generated for envman. Do not edit.
[ -s "$HOME/.config/envman/load.sh" ] && source "$HOME/.config/envman/load.sh"

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"
# . "$HOME/.cargo/env"

# alias python=python3


# Load Angular CLI autocompletion.
# source <(ng completion script)

# Load Spring CLI autocompletion.
# . ~/.sdkman/candidates/springboot/current/shell-completion/bash/spring
