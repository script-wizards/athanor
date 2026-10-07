autoload -Uz vcs_info
setopt prompt_subst
zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:*' check-for-changes true
zstyle ':vcs_info:*' unstagedstr '*'
zstyle ':vcs_info:*' stagedstr '+'
zstyle ':vcs_info:git:*' formats ' %F{6}%b%f%F{1}%u%c%f'
zstyle ':vcs_info:git:*' actionformats ' %F{6}%b%f %F{3}(%a)%f%F{1}%u%c%f'
precmd_functions+=(vcs_info)

PROMPT='%(?.%F{3}.%F{1})@%f %1~${vcs_info_msg_0_} %F{8}»%f '

_athanor_set_title() {
  [[ ${ATHANOR_TITLE:-1} == 0 || -n $TMUX || $TERM == (dumb|linux|screen*) ]] && return
  print -rn -- $'\e]2;'"${1//[[:cntrl:]]/}"$'\a'
}

_athanor_title_folder() {
  _athanor_set_title "${(%):-%1~}"
}

_athanor_title_command() {
  local -a words=(${(z)1})
  while [[ $words[1] =~ '^[A-Za-z_][A-Za-z0-9_]*=' ]]; do shift words; done
  local title=${(Q)words[1]:t}
  [[ -n $words[2] && $words[2] != [-\;\|\&\<\>\(]* ]] && title+=" ${(Q)words[2]:t}"
  _athanor_set_title "$title"
}

# A script that sources this still runs preexec, with an empty command line.
if [[ -o interactive ]]; then
  precmd_functions+=(_athanor_title_folder)
  preexec_functions+=(_athanor_title_command)
fi

if [[ -o interactive && -x ~/.local/bin/athanor ]]; then
  ~/.local/bin/athanor room --once
fi
