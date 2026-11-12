"""
Shared pytest fixtures/helpers for tests under tests/API/, used by two or more service
directories. Fixtures/helpers needed by only one service belong in that service's own
conftest.py instead.
"""

import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Files for upload tests
# ---------------------------------------------------------------------------

_DOCUMENT_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def pick_random_document() -> tuple[str, bytes, str]:
    """
    Returns (filename, content, content_type) for a random file from data/files/ — ready to
    pass as files={...} when uploading a document.
    """
    files_dir = Path("./data/files")
    doc_files = [f for f in files_dir.iterdir() if f.is_file() and f.suffix.lower() in _DOCUMENT_MIME_TYPES]
    if not doc_files:
        raise FileNotFoundError(f"No document files found in {files_dir}")

    chosen = random.choice(doc_files)
    return chosen.name, chosen.read_bytes(), _DOCUMENT_MIME_TYPES[chosen.suffix.lower()]


_IMAGE_MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def pick_random_image() -> tuple[str, bytes, str]:
    """
    Returns (filename, content, content_type) for a random IMAGE from data/files/ — unlike
    pick_random_document(), excludes .pdf, for endpoints that expect an actual image.
    """
    files_dir = Path("./data/files")
    image_files = [f for f in files_dir.iterdir() if f.is_file() and f.suffix.lower() in _IMAGE_MIME_TYPES]
    if not image_files:
        raise FileNotFoundError(f"No image files found in {files_dir}")

    chosen = random.choice(image_files)
    return chosen.name, chosen.read_bytes(), _IMAGE_MIME_TYPES[chosen.suffix.lower()]
