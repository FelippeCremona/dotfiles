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

# Tmuxinator
alias tm="tmuxinator $1"

# Comandos linux
alias ls="exa -lah --color=auto"
alias vi="nvim"
alias celar="clear"

alias findf="find . -type f -name $1"
alias findd="find . -type d -name $1"

# Comandos WSL
alias downloads="cd /mnt/c/Users/cremo/Downloads $1"

# Comandos git
alias gl="git log --oneline"
alias glu="git log --date=iso --pretty='%C(Yellow)%h %C(reset)%cd %C(Cyan)%an: %C(reset)%s'"

# Comandos sistemas
alias sc="~/trabalho/programas/documentos/fzf_arquivos.sh"
alias docs="~/trabalho/programas/documentos/fzf_docs.sh"
alias projetos="~/trabalho/programas/documentos/fzf_projetos.sh"

alias quarkusd="quarkus dev -Dquarkus.console.enabled='false'"

eval "$(starship init bash)"

[ -f ~/.fzf.bash ] && source ~/.fzf.bash



glog (){
	git log \
		--color=always \
		--format="%C(cyan)%h %C(blue)%ar%C(auto)%d \
			 %C(yellow)%s%+b %C(black)%ae" "$@" |
	    fzf -i -e +s \
		--tiebreak=index \
        --reverse \
		--no-multi \
		--ansi \
		--preview="echo {} |
			   grep -o '[a-f0-9]\{7\}' |
			   head -1 |
			   xargs -I % sh -c 'git show --color=always % |
			   diff-so-fancy'" \
		--header "enter: view, C-c: copy hash" \
		--bind "enter:execute:$_viewGitLogLine | less -R" \
		--bind "ctrl-c:execute:$_gitLogLineToHash |
			xclip -r -selection clipboard"
}


# diff-so-fancy
export PATH=$PATH:~/bin

# conectar ao oracle
export LD_LIBRARY_PATH=/opt/oracle/instantclient_21_8:$LD_LIBRARY_PATH

# zoxide
# export ZOXIDE_HOME=$HOME/.local/opt/zoxide                                
# export PATH=$PATH:$ZOXIDE_HOME/bin                                        
export PATH=/home/cremona/.local/bin:$PATH
eval "$(zoxide init bash)"

# Generated for envman. Do not edit.
[ -s "$HOME/.config/envman/load.sh" ] && source "$HOME/.config/envman/load.sh"

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"
# . "$HOME/.cargo/env"
