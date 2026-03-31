import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)


class ContextFile:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath) as f:
            self.file_contents = f.read()

    def __str__(self):
        label = f"## File: {self.filepath} "
        padding = max(0, 80 - len(label))
        return f"{label}{'#' * padding}\n{self.file_contents}"


def expand_path(path: str) -> list["ContextFile"]:
    p = Path(path)
    if p.is_dir():
        files = [f for f in sorted(p.iterdir()) if f.is_file()]
        for f in files:
            logger.info(f"loading context file: {f}")
        return [ContextFile(str(f)) for f in files]
    logger.info(f"loading context file: {p}")
    return [ContextFile(path)]


def get_context_range(text: str) -> tuple[int, int, list[str]]:
    lines = text.splitlines()

    start = None
    end = None

    for i, line in enumerate(lines):
        if start is None and "# Chat File Context" in line.strip():
            start = i + 1
        elif start is not None and "# " in line:
            end = i
            break

    if start is None:
        return (0, 0, [])
    if end is None:
        end = len(lines)

    paths = [
        line
        for line in lines[start:end]
        if line.strip() and not line.strip().startswith("Workspace:")
    ]
    return (start, end, paths)


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


def load_context_from_file(context_path: str) -> str:
    with open(context_path) as f:
        paths = [line.strip() for line in f if line.strip()]

    header = "# Chat File Context ############################################################\n"
    footer = "# End Chat File Context ########################################################\n"
    parts = [header, f"Workspace: {os.getcwd()}\n"]
    for p in paths:
        for cf in expand_path(p):
            parts.append(str(cf))
    parts.append(footer)
    return "\n".join(parts) + "\n"
