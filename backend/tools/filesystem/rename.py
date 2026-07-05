"""Rename or move a file or directory."""

from pathlib import Path


def rename(src: str, dst: str) -> None:
    """Move the file or directory at `src` to `dst`.

    Creates `dst`'s parent directories as needed. Raises FileNotFoundError
    if `src` does not exist, and FileExistsError if `dst` already does.
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Path not found: {src}")
    if dst_path.exists():
        raise FileExistsError(f"Path already exists: {dst}")

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.rename(dst_path)
