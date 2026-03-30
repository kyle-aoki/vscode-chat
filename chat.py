#!/usr/bin/env python3
import os
import re
import subprocess
import time
import argparse
import logging
from pathlib import Path


CHAT_DIR = Path("chat")

PREAMBLE = """\
> Below is a conversation history in markdown. You are Claude.
> Output ONLY your response (no ## Claude header, no preamble).
>
> Document structure:
> - "# Context" contains the file contents of the specified filepath. Use them but don't repeat their contents back.
> - "# User" sections are user messages. Respond to the LAST one.
> - "# Claude (...)" sections are your prior responses in this conversation.

"""

verbose = False
debug = False
logger = logging.getLogger(__name__)

MODELS = {
    "~": "opus",
    "2~": "sonnet",
    "3~": "haiku",
}


class ContextFile:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath) as f:
            self.file_contents = f.read()

    def __str__(self):
        return f"## START FILE: {self.filepath}\n{self.file_contents}\n## END FILE"


def get_context_range(text: str) -> tuple[int, int, list[str]]:
    lines = text.splitlines()

    start = None
    end = None

    for i, line in enumerate(lines):
        if start is None and "# Context" in line.strip():
            start = i + 1
        elif start is not None and "# " in line:
            end = i
            break

    if start is None:
        return (0, 0, [])
    if end is None:
        end = len(lines)

    paths = [line for line in lines[start:end] if line.strip()]
    return (start, end, paths)


def expand_path(path: str) -> list[ContextFile]:
    p = Path(path)
    if p.is_dir():
        files = [f for f in sorted(p.iterdir()) if f.is_file()]
        for f in files:
            logger.info(f"loading context file: {f}")
        return [ContextFile(str(f)) for f in files]
    logger.info(f"loading context file: {p}")
    return [ContextFile(path)]


def load_context(text: str) -> str:
    lines = text.splitlines()
    start, end, paths = get_context_range(text)

    if not paths:
        return text

    replacement: list[str] = []
    for p in paths:
        replacement.extend(str(cf) for cf in expand_path(p))
    lines[start:end] = replacement
    return "\n".join(lines) + "\n"


def add_context_header(chat: Path):
    with open(chat, "a") as f:
        f.write(
            "# Context ######################################################################\n"
        )
        f.write("\n\n\n")


def add_user_message_header(chat: Path):
    with open(chat, "a") as f:
        f.write(
            "# User #########################################################################\n"
        )
        f.write("\n")


def add_claude_message_header(chat: Path, model: str):
    prefix = f"# Claude ({model}) "
    hashes = "#" * (80 - len(prefix))
    with open(chat, "a") as f:
        f.write(f"\n{prefix}{hashes}\n")


def add_claude_message(chat: Path, msg: str):
    with open(chat, "a") as f:
        f.write(f"\n{msg}\n\n")


def run_chat(chat_name: str, model: str = "sonnet"):
    CHAT_DIR.mkdir(exist_ok=True)
    chat = CHAT_DIR / chat_name

    if not chat.exists():
        add_user_message_header(chat)
        return

    with open(chat) as f:
        content = f.read()

    prompt = load_context(PREAMBLE + content)
    prompt = re.sub(r" #{5,}", "", prompt)

    if debug:
        print(prompt)

    add_claude_message_header(chat, model)
    result = subprocess.run(
        ["claude", "--print", f"--model={model}", prompt],
        capture_output=True,
        text=True,
    )
    add_claude_message(chat, result.stdout.rstrip())
    add_user_message_header(chat)
    print(f"ran chat for {chat_name}")


def read_last_line(path: Path) -> tuple[str, int]:
    """Return (last_line, byte_offset) where offset is the start of that line."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        end = f.tell()
        if end == 0:
            return "", 0
        pos = end - 1
        # skip trailing newline(s)
        while pos > 0:
            f.seek(pos)
            if f.read(1) != b"\n":
                break
            pos -= 1
        # find the start of the last line
        while pos > 0:
            pos -= 1
            f.seek(pos)
            if f.read(1) == b"\n":
                line_start = pos + 1
                return f.read().decode().strip(), line_start
        f.seek(0)
        return f.read().decode().strip(), 0


def watch_chat():
    CHAT_DIR.mkdir(exist_ok=True)
    triggers = ", ".join(f"{k} ({v})" for k, v in MODELS.items())
    print(f"watching {CHAT_DIR}/ for triggers: {triggers}")

    while True:
        for chat in CHAT_DIR.glob("*.md"):
            if chat.stat().st_size == 0:
                add_context_header(chat)
                add_user_message_header(chat)
                continue

            last_line, line_offset = read_last_line(chat)
            model = MODELS.get(last_line)
            if model is None:
                continue

            # Remove the trigger line
            os.truncate(chat, line_offset)

            print(f"running claude ({model}) for {chat.name}")
            pid = os.fork()
            if pid == 0:
                try:
                    run_chat(chat.name, model)
                finally:
                    os._exit(0)

        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    global verbose, debug
    verbose = args.verbose
    debug = args.debug
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug("verbose mode enabled")

    if args.chat:
        run_chat(args.chat, args.model)
    elif args.watch:
        watch_chat()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
