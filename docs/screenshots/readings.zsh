source ~/.config/athanor/athanor.zsh 2>/dev/null
cd "$ATHANOR_DEMO_REPO"
clear
case $1 in
  tarot)
    print -rP -- "${PROMPT}athanor hour"
    athanor hour
    print -rP -- "${PROMPT}athanor draw 3"
    athanor draw --card "the magician" --card "the devil" --card "temperance"
    ;;
  tomb)
    print -rP -- "${PROMPT}athanor tomb"
    athanor tomb --demo
    ;;
  sigil)
    print -rP -- "${PROMPT}athanor sigil"
    uv run --quiet --project "$ATHANOR_REPO" python -c '
import hashlib
from athanor import sigil
d = hashlib.sha256(b"ariel").digest()
print(sigil.text(sigil.grid(d)))
print(sigil.fingerprint_text(d))'
    ;;
esac
print -rnP -- "${PROMPT}"
sleep 3600
