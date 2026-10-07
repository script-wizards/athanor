source ~/.config/athanor/athanor.zsh 2>/dev/null
cd "$ATHANOR_DEMO_REPO"
_athanor_title_folder
clear
athanor room
echo
athanor sheet
echo
print -rP -- "${PROMPT}git log --oneline -4"
git --no-pager log --oneline -4 --color=always
print -rP -- "${PROMPT}cc -o planetary planetary.c && ./planetary"
cc -std=c11 -O2 -o planetary planetary.c && ./planetary
print -rP -- "${PROMPT}athanor status"
athanor status
print -rnP -- "${PROMPT}"
sleep 3600
