from datetime import UTC, datetime
from pathlib import Path


def get_latest_file(
    file: Path | None = None,
    prefix: str | None = None,
    extension: str = ".parquet",
    directory: Path = Path("."),
) -> Path | None:
    """
    Returns the latest file matching the prefix and extension in the directory.

    Args:
        file (Path, optional): The file path without the timestamp. Defaults to None.
        prefix (str): The prefix of the file name. Defaults to None.
        extension (str, optional): The extension of the file. Defaults to ".parquet".
        directory (Path, optional): The directory to search in. Defaults to Path(".")

    Returns:
        path: The path to the latest file.
    """
    if file is None and prefix is None:
        raise ValueError("Either file or prefix must be provided.")
    if file:
        prefix = file.stem
        extension = file.suffix
        directory = file.parent

    if files := list(directory.glob(f"{prefix}_2*{extension}")):
        return max(files, key=lambda x: x.stem)
    else:
        return None


def timestamp_file(file: Path) -> Path:
    ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    return file.with_name(f"{file.stem}_{ts}{file.suffix}")
