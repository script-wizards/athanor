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

if [[ -o interactive && -x ~/.local/bin/athanor ]]; then
  ~/.local/bin/athanor room --once
fi
