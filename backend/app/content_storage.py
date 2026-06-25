"""Server-side storage helpers for the admin content library.

These functions own the path-traversal safety guarantees for uploaded files.
The golden rule: a candidate (or admin) never supplies a path component that is
joined to ``content_dir``.  ``file_key`` and ``stored_filename`` are both
server-generated; the client's original filename is only ever used for display
and for the ``Content-Disposition`` download header.
"""

import re
from pathlib import Path
from uuid import uuid4

# The only categories the UI offers / the API accepts.
ALLOWED_CATEGORIES: set[str] = {"brief", "data", "reference"}

# A stored filename is always "<32 hex chars>" optionally followed by a short,
# lowercase, alphanumeric extension.  Anything else is rejected before it is
# ever turned into a filesystem path.
_STORED_FILENAME_RE = re.compile(r"^[0-9a-f]{32}(\.[a-z0-9]{1,12})?$")


def allocate_file_key() -> str:
    """Return a fresh opaque, URL-safe, PII-free key (uuid4 hex)."""
    return uuid4().hex


def safe_extension(original_filename: str) -> str:
    """Return a sanitised, lowercase extension (incl. leading dot) or ''.

    Only ``.ext`` made of 1-12 alphanumeric chars is kept; everything else
    (no extension, multi-dot, odd characters) collapses to an empty string so
    the stored filename stays inside the strict whitelist pattern.
    """
    suffix = Path(original_filename).suffix.lower()  # e.g. ".pdf"
    if not suffix:
        return ""
    ext = suffix[1:]
    if re.fullmatch(r"[a-z0-9]{1,12}", ext):
        return f".{ext}"
    return ""


def stored_filename_for(file_key: str, original_filename: str) -> str:
    """Build the on-disk filename for a freshly allocated *file_key*."""
    return f"{file_key}{safe_extension(original_filename)}"


def resolve_stored_path(stored_filename: str, content_dir: str) -> Path | None:
    """Return the absolute Path for *stored_filename* inside *content_dir*, or None.

    Guards (defense-in-depth — stored_filename is already server-generated):
    - Rejects anything not matching the strict ``<hex>[.ext]`` whitelist.
    - Rejects anything that resolves outside *content_dir*.
    - Returns None if the file does not exist / is not a regular file.
    """
    if not _STORED_FILENAME_RE.fullmatch(stored_filename):
        return None

    base = Path(content_dir).resolve()
    path = (base / stored_filename).resolve()
    if base != path.parent and base not in path.parents:
        return None
    if path.exists() and path.is_file():
        return path
    return None
