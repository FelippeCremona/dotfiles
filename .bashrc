# Enable the subsequent settings only in interactive sessions
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

# Path to your oh-my-bash installation.
# export OSH='/home/cremona/.oh-my-bash'

# Set name of the theme to load. Optionally, if you set this to "random"
# it'll load a random theme each time that oh-my-bash is loaded.
# OSH_THEME="half-life"

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion. Case
# sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment the following line to disable bi-weekly auto-update checks.
# DISABLE_AUTO_UPDATE="true"

# Uncomment the following line to change how often to auto-update (in days).
# export UPDATE_OSH_DAYS=13

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.  One of the following values can
# be used to specify the timestamp format.
# * 'mm/dd/yyyy'     # mm/dd/yyyy + time
# * 'dd.mm.yyyy'     # dd.mm.yyyy + time
# * 'yyyy-mm-dd'     # yyyy-mm-dd + time
# * '[mm/dd/yyyy]'   # [mm/dd/yyyy] + [time] with colors
# * '[dd.mm.yyyy]'   # [dd.mm.yyyy] + [time] with colors
# * '[yyyy-mm-dd]'   # [yyyy-mm-dd] + [time] with colors
# If not set, the default value is 'yyyy-mm-dd'.
# HIST_STAMPS='yyyy-mm-dd'

# Uncomment the following line if you do not want OMB to overwrite the existing
# aliases by the default OMB aliases defined in lib/*.sh
# OMB_DEFAULT_ALIASES="check"

# Would you like to use another custom folder than $OSH/custom?
# OSH_CUSTOM=/path/to/new-custom-folder

# To disable the uses of "sudo" by oh-my-bash, please set "false" to
# this variable.  The default behavior for the empty value is "true".
OMB_USE_SUDO=true

# Which completions would you like to load? (completions can be found in ~/.oh-my-bash/completions/*)
# Custom completions may be added to ~/.oh-my-bash/custom/completions/
# Example format: completions=(ssh git bundler gem pip pip3)
# Add wisely, as too many completions slow down shell startup.
completions=(
  git
  composer
  ssh
)

# Which aliases would you like to load? (aliases can be found in ~/.oh-my-bash/aliases/*)
# Custom aliases may be added to ~/.oh-my-bash/custom/aliases/
# Example format: aliases=(vagrant composer git-avh)
# Add wisely, as too many aliases slow down shell startup.
aliases=(
  general
)

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-bash/plugins/*)
# Custom plugins may be added to ~/.oh-my-bash/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(
  git
  bashmarks
  z
)

# Which plugins would you like to conditionally load? (plugins can be found in ~/.oh-my-bash/plugins/*)
# Custom plugins may be added to ~/.oh-my-bash/custom/plugins/
# Example format: 
#  if [ "$DISPLAY" ] || [ "$SSH" ]; then
#      plugins+=(tmux-autoattach)
#  fi

# source "$OSH"/oh-my-bash.sh

# SDKMAN! Configuration
source "$HOME/.sdkman/bin/sdkman-init.sh"

# User configuration
# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

export EDITOR="/home/cremona/.local/bin/lvim"

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# ssh
# export SSH_KEY_PATH="~/.ssh/rsa_id"

# Set personal aliases, overriding those provided by oh-my-bash libs,
# plugins, and themes. Aliases can be placed here, though oh-my-bash
# users are encouraged to define aliases within the OSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases

# Arquivos de configuração
alias bashrc="lvim ~/.bashrc"
alias vimrc="lvim ~/.config/lvim/"
alias strc="lvim ~/.config/starship.toml"

# Tmuxinator
alias tm="tmuxinator $1"

# Comandos linux
alias ls="exa -lah --color=auto"
# alias nvim="lvim"
alias vi="lvim"

# Comandos WSL
alias downloads="cd /mnt/c/Users/cremo/Downloads $1"

# Comandos git
alias gl="git log --oneline"
alias glu="git log --date=iso --pretty='%C(Yellow)%h %C(reset)%cd %C(Cyan)%an: %C(reset)%s'"

# Comandos sistemas
alias scripts="~/trabalho/programas/documentos/fzf_arquivos.sh"
alias docs="~/trabalho/programas/documentos/fzf_docs.sh"
alias projetos="~/trabalho/programas/documentos/fzf_projetos.sh"

alias cvrb="lvim ~/trabalho/spread/sistemas/sicvr/des/bnd"
alias cvrf="lvim ~/trabalho/spread/sistemas/sicvr/des/fnd/web/"
alias cvra="lvim ~/trabalho/spread/sistemas/sicvr/des/api"

alias mcns="lvim ~/trabalho/spread/sistemas/simcn/des/mcn/"
# alias ohmybash="mate ~/.oh-my-bash"

alias quarkusd="quarkus dev -Dquarkus.console.enabled='false'"

# Load Angular CLI autocompletion.
# source <(ng completion script)

# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
# [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

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

. "$HOME/.cargo/env"

# Generated for envman. Do not edit.
[ -s "$HOME/.config/envman/load.sh" ] && source "$HOME/.config/envman/load.sh"

