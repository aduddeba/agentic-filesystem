"""Create a directory."""

from pathlib import Path


def make_directory(path: str) -> None:
    """Create `path` as a directory, including any missing parents.

    A no-op if the directory already exists.
    """
    Path(path).mkdir(parents=True, exist_ok=True)
