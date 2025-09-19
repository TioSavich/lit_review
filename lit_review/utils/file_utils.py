"""
File utilities for the literature review platform
"""

import os
import hashlib
from pathlib import Path
from typing import Optional


def ensure_directory(path: str) -> Path:
    """
    Ensure a directory exists, create if it doesn't
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_file_hash(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file
    
    Args:
        file_path: Path to file
        
    Returns:
        Hex digest of file hash
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)


def is_pdf_file(file_path: str) -> bool:
    """Check if file is a PDF"""
    return Path(file_path).suffix.lower() == '.pdf'