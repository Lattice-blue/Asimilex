"""
Local document connector.
Scans `mirror/files/` for PDFs/books and extracts tables of contents into the DB.
"""
from pathlib import Path

FILES_DIR = Path(__file__).resolve().parent.parent / "mirror" / "files"

def scan_files():
    """Finds newly added books/documents in mirror/files/"""
    return list(FILES_DIR.glob("*"))