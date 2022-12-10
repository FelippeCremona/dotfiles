export EDITOR="/home/cremona/.local/bin/lvim"

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

# zoxide
export PATH=/home/cremona/.local/bin:$PATH
eval "$(zoxide init bash)"
