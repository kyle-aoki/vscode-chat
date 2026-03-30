q () {
    claude --print --model=sonnet
}

qq () {
    claude --model=sonnet "$*"
}

chat () {
    python3 "$(dirname "${BASH_SOURCE[0]:-$0}")/chat.py" "$@"
}
