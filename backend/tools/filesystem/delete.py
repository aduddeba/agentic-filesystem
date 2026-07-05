"""Delete a file or directory."""

import shutil
from pathlib import Path


def delete(path: str) -> None:
    """Delete the file or directory at `path`.

    Directories are removed recursively. Raises FileNotFoundError if
    nothing exists at `path`.
    """
    target = Path(path)
    if target.is_dir():
        shutil.rmtree(target)
    elif target.is_file():
        target.unlink()
    else:
        raise FileNotFoundError(f"Path not found: {path}")
