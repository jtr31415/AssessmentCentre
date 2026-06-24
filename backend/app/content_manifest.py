"""Content manifest — the single source of truth for downloadable assessment files.

Only filenames listed here can ever be served. ``resolve_path`` enforces this by
never joining arbitrary user-supplied input; it looks up the ``file_key`` in
MANIFEST and uses the hard-coded ``filename`` field, preventing path traversal.
"""

from pathlib import Path

MANIFEST: list[dict] = [
    {
        "file_key": "exercise_brief",
        "filename": "exercise_brief.pdf",
        "label": "Exercise Brief",
        "category": "brief",
        "media_type": "application/pdf",
    },
    {
        "file_key": "turbine_data",
        "filename": "turbine_data.csv",
        "label": "Turbine Data",
        "category": "data",
        "media_type": "text/csv",
    },
    {
        "file_key": "weather_limits",
        "filename": "weather_limits.csv",
        "label": "Weather Limits",
        "category": "data",
        "media_type": "text/csv",
    },
    {
        "file_key": "wind_data_20yr",
        "filename": "wind_data_20yr.xlsx",
        "label": "20-Year Wind Data",
        "category": "data",
        "media_type": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    },
    {
        "file_key": "terminology",
        "filename": "terminology.pdf",
        "label": "Terminology Reference",
        "category": "reference",
        "media_type": "application/pdf",
    },
    {
        "file_key": "build_process",
        "filename": "build_process.pdf",
        "label": "Build Process Guide",
        "category": "reference",
        "media_type": "application/pdf",
    },
]

# Build an O(1) lookup index from file_key → entry
_INDEX: dict[str, dict] = {entry["file_key"]: entry for entry in MANIFEST}


def get_entry(file_key: str) -> dict | None:
    """Return the manifest entry for *file_key*, or None if not found."""
    return _INDEX.get(file_key)


def resolve_path(file_key: str, content_dir: str) -> Path | None:
    """Return the absolute Path for *file_key* inside *content_dir*, or None.

    Guards:
    - Returns None for any *file_key* not present in MANIFEST (unknown key).
    - Returns None if the file does not exist or is not a regular file on disk.
    - NEVER joins the raw *file_key* (or any other user input) to the directory;
      only the hard-coded ``filename`` from the manifest entry is ever used.
    """
    entry = _INDEX.get(file_key)
    if entry is None:
        return None

    path = Path(content_dir) / entry["filename"]
    if path.exists() and path.is_file():
        return path
    return None
