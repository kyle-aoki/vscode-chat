#!/usr/bin/env python3
import os
import re
import subprocess
import time
import argparse
import logging
from pathlib import Path

from context import load_context, load_context_from_file


PREAMBLE = """\
> Below is a conversation history in markdown. You are Claude.
> Output ONLY your response (no ## Claude header, no preamble).
>
> Document structure:
> - "# Chat File Context" contains the file contents of the specified filepath. Use them but don't repeat their contents back.
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


def add_context_header(chat: Path):
    with open(chat, "a") as f:
        f.write(
            "# Chat File Context ############################################################\n"
        )
        f.write(f"Workspace: {os.getcwd()}\n")
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


def run_chat(chat_path: str, model: str = "sonnet"):
    chat = Path(chat_path)
    chat.parent.mkdir(parents=True, exist_ok=True)

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
    print(f"ran chat for {chat.name}")


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


def watch_chat(watch_dir: str):
    chat_dir = Path(watch_dir)
    chat_dir.mkdir(parents=True, exist_ok=True)
    triggers = ", ".join(f"{k} ({v})" for k, v in MODELS.items())
    print(f"watching {chat_dir}/ for triggers: {triggers}")

    while True:
        for chat in chat_dir.glob("*.md"):
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
                    run_chat(str(chat), model)
                finally:
                    os._exit(0)

        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat")
    parser.add_argument("--watch", help="directory to watch for chat files")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--context", help="path to a context .txt file")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    global verbose, debug
    verbose = args.verbose
    debug = args.debug
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug("verbose mode enabled")

    if args.context:
        logging.disable(logging.CRITICAL)
        print(load_context_from_file(args.context))
    elif args.chat:
        run_chat(args.chat, args.model)
    elif args.watch:
        watch_chat(args.watch)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
