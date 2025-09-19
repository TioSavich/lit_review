"""
Literature Review Platform for Mathematics Education Research

This package provides tools for processing, storing, and querying
large collections of academic PDFs with focus on mathematics education.
"""

__version__ = "0.1.0"
__author__ = "Literature Review Platform"
__email__ = "lit_review@example.com"

from .models import Document, Author, Citation
from .processors import PDFProcessor, DoclingProcessor
from .storage import DocumentStorage, VectorStorage
from .analysis import CitationAnalyzer, CoAuthorshipAnalyzer
from .web import create_app

__all__ = [
    "Document",
    "Author", 
    "Citation",
    "PDFProcessor",
    "DoclingProcessor",
    "DocumentStorage",
    "VectorStorage",
    "CitationAnalyzer",
    "CoAuthorshipAnalyzer",
    "create_app",
]