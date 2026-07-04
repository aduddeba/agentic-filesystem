"""Write text contents to a file."""

from pathlib import Path


def write(file: str, content: str) -> None:
    """Write `content` to `file`, creating parent directories as needed."""
    path = Path(file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
