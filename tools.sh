q () {
    claude --print --model=sonnet
}

qq () {
    claude --model=sonnet "$*"
}

CHAT_DIR="chat"

add_context_header() {
    local file="$1"
    echo "# Context ######################################################################" >> "$file"
    echo "" >> "$file"
    echo "" >> "$file"
    echo "" >> "$file"
}

add_user_message_header() {
    local file="$1"
    echo "# User #########################################################################" >> "$file"
    echo "" >> "$file"
}

add_claude_message_header() {
    local file="$1"
    local model="$2"
    local prefix="# Claude ($model) "
    local hash_count=$((80 - ${#prefix}))
    local hashes=$(printf '%*s' "$hash_count" '' | tr ' ' '#')
    echo "" >> "$file"
    echo "${prefix}${hashes}" >> "$file"
}

add_claude_message() {
    local file="$1"
    local msg="$2"
    echo "" >> "$file"
    echo "$msg" >> "$file"
    echo "" >> "$file"
}

run_chat() {
    local debug=false
    if [[ "$1" == "--debug" ]]; then
        debug=true
        shift
    fi
    local filename="$1"
    local model="${2:-sonnet}"
    if [[ -n "$filename" ]]; then
        mkdir -p "$CHAT_DIR"
        local file="$CHAT_DIR/$filename"
    else
        echo "missing chat file argument"
        return
    fi

    if [[ ! -f "$file" ]]; then
        add_user_message_header "$file"
        return
    fi

    tmp=$(mktemp)
    echo "Below is a conversation history in markdown. You are Claude." >> "$tmp"
    echo "Continue the conversation by responding to the latest User message." >> "$tmp"
    echo "Output ONLY your response (no ## Claude header, no preamble)." >> "$tmp"
    echo "" >> "$tmp"

    cat "$file" >> "$tmp"
    python3 context.py "$tmp"

    chat=$(<"$tmp")
    rm "$tmp"

    if $debug; then
        echo "$chat"
        return
    fi

    add_claude_message_header "$file" "$model"
    RESPONSE=$(claude --print --model="$model" "$chat")

    add_claude_message "$file" "$RESPONSE"
    add_user_message_header "$file"
    echo "ran chat for $filename"
}

watch_chat () {
    mkdir -p "$CHAT_DIR"

    echo "watching all files in $CHAT_DIR for ~ (opus), 2~ (sonnet), 3~ (haiku) trigger..."
    while true; do
        for file in "$CHAT_DIR"/*.md; do
            [[ -f "$file" ]] || continue
            if [[ ! -s "$file" ]]; then
                add_context_header "$file"
                add_user_message_header "$file"
                continue
            fi
            last_line=$(tail -1 "$file")
            local model=""
            case "$last_line" in
                "3~") model="haiku" ;;
                "2~") model="sonnet" ;;
                "~")  model="opus" ;;
            esac
            if [[ -n "$model" ]]; then
                sed -i '' '$ d' "$file"
                local basename="${file#$CHAT_DIR/}"
                echo "running claude ($model) for $basename"
                run_chat "$basename" "$model" &
            fi
        done
        sleep .5
    done
}
