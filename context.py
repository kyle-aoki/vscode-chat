import sys
import re


class ContextFile:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath) as f:
            self.file_contents = f.read()

    def __str__(self):
        return f"## FILE: {self.filepath}\n{self.file_contents}\n## END FILE"


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


def main():
    if len(sys.argv) != 2:
        print("Usage: python context.py <input_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath) as f:
        text = f.read()

    lines = text.splitlines()
    start, end, paths = get_context_range(text)

    if not paths:
        print("No context paths found.")
        sys.exit(0)

    replacement = [str(ContextFile(p)) for p in paths]
    lines[start:end] = replacement

    with open(filepath, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
