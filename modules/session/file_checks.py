"""Check that an uploaded file really is what its extension says.

The extension alone is not trusted: a renamed HTML or script file must not be
stored as ".png". Images are fully parsed with Pillow (also rejecting
decompression bombs), PDFs must start with the PDF signature and Office files
must be ZIP packages with the expected parts. Nothing is decompressed.
"""
import io
import zipfile

MAX_IMAGE_PIXELS = 40_000_000  # ~ 6300 x 6300, far above any sensible upload

IMAGE_FORMATS = {
    ".png": {"PNG"},
    ".jpg": {"JPEG", "MPO"},
    ".jpeg": {"JPEG", "MPO"},
    ".gif": {"GIF"},
    ".webp": {"WEBP"},
}
OFFICE_PARTS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
}


def _is_image(ext, data):
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in IMAGE_FORMATS[ext]:
                return False
            width, height = img.size
            if width * height > MAX_IMAGE_PIXELS:
                return False
            img.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return False


def _is_pdf(data):
    return b"%PDF-" in data[:1024]


def _is_office(ext, data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except (zipfile.BadZipFile, ValueError):
        return False
    return "[Content_Types].xml" in names and OFFICE_PARTS[ext] in names


def content_matches(ext, data):
    """True if ``data`` is a genuine file of type ``ext`` (e.g. ".png")."""
    if ext in IMAGE_FORMATS:
        return _is_image(ext, data)
    if ext == ".pdf":
        return _is_pdf(data)
    if ext in OFFICE_PARTS:
        return _is_office(ext, data)
    return False
