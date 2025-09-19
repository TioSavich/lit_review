"""
Fallback PDF processor using PyMuPDF and other libraries
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from ..utils.text_processing import extract_citations, extract_authors_from_text, clean_text


@dataclass
class ProcessedDocument:
    """Container for processed document data"""
    title: str
    abstract: str
    content: str
    authors: List[str]
    keywords: List[str]
    citations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    sections: List[Dict[str, Any]]


class PDFProcessor:
    """
    Fallback PDF processor using PyMuPDF and PyPDF2
    """
    
    def __init__(self, preserve_images: bool = True):
        """
        Initialize PDF processor
        
        Args:
            preserve_images: Whether to preserve images (not implemented in fallback)
        """
        self.preserve_images = preserve_images
        self.logger = logging.getLogger(__name__)
        
        if not PYMUPDF_AVAILABLE and not PYPDF2_AVAILABLE:
            raise ImportError("Either PyMuPDF or PyPDF2 is required for PDF processing")
    
    def process_pdf(self, pdf_path: str) -> ProcessedDocument:
        """
        Process a PDF file and extract content
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ProcessedDocument containing extracted data
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.logger.info(f"Processing PDF: {pdf_path}")
        
        try:
            # Try PyMuPDF first (better text extraction)
            if PYMUPDF_AVAILABLE:
                return self._process_with_pymupdf(pdf_path)
            elif PYPDF2_AVAILABLE:
                return self._process_with_pypdf2(pdf_path)
            else:
                raise ImportError("No PDF processing library available")
                
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
    
    def _process_with_pymupdf(self, pdf_path: Path) -> ProcessedDocument:
        """Process PDF using PyMuPDF"""
        doc = fitz.open(str(pdf_path))
        
        # Extract text from all pages
        full_text = ""
        sections = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            full_text += page_text + "\n"
            
            # Create basic sections by page
            sections.append({
                'type': 'page',
                'content': page_text,
                'page': page_num + 1,
                'bbox': None
            })
        
        doc.close()
        
        # Extract document components
        metadata = self._extract_pdf_metadata(pdf_path)
        title = self._extract_title(full_text)
        abstract = self._extract_abstract(full_text)
        authors = self._extract_authors(full_text)
        keywords = self._extract_keywords(full_text)
        citations = self._extract_citations(full_text)
        
        return ProcessedDocument(
            title=title,
            abstract=abstract,
            content=full_text,
            authors=authors,
            keywords=keywords,
            citations=citations,
            metadata=metadata,
            sections=sections
        )
    
    def _process_with_pypdf2(self, pdf_path: Path) -> ProcessedDocument:
        """Process PDF using PyPDF2"""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from all pages
            full_text = ""
            sections = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                full_text += page_text + "\n"
                
                # Create basic sections by page
                sections.append({
                    'type': 'page',
                    'content': page_text,
                    'page': page_num + 1,
                    'bbox': None
                })
        
        # Extract document components
        metadata = self._extract_pdf_metadata(pdf_path)
        metadata.update(self._extract_pypdf2_metadata(pdf_path))
        
        title = self._extract_title(full_text)
        abstract = self._extract_abstract(full_text)
        authors = self._extract_authors(full_text)
        keywords = self._extract_keywords(full_text)
        citations = self._extract_citations(full_text)
        
        return ProcessedDocument(
            title=title,
            abstract=abstract,
            content=full_text,
            authors=authors,
            keywords=keywords,
            citations=citations,
            metadata=metadata,
            sections=sections
        )
    
    def _extract_pdf_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract basic file metadata"""
        stat = pdf_path.stat()
        return {
            'file_name': pdf_path.name,
            'file_size': stat.st_size,
            'processor': 'fallback_pdf_processor',
            'created_time': stat.st_ctime,
            'modified_time': stat.st_mtime
        }
    
    def _extract_pypdf2_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract PDF metadata using PyPDF2"""
        metadata = {}
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if pdf_reader.metadata:
                    pdf_metadata = pdf_reader.metadata
                    metadata.update({
                        'pdf_title': pdf_metadata.get('/Title', ''),
                        'pdf_author': pdf_metadata.get('/Author', ''),
                        'pdf_subject': pdf_metadata.get('/Subject', ''),
                        'pdf_creator': pdf_metadata.get('/Creator', ''),
                        'pdf_producer': pdf_metadata.get('/Producer', ''),
                        'pdf_creation_date': str(pdf_metadata.get('/CreationDate', '')),
                        'pdf_modification_date': str(pdf_metadata.get('/ModDate', ''))
                    })
                
                metadata['page_count'] = len(pdf_reader.pages)
        except Exception as e:
            self.logger.warning(f"Could not extract PDF metadata: {str(e)}")
        
        return metadata
    
    def _extract_title(self, text: str) -> str:
        """Extract document title from text"""
        lines = text.split('\n')
        
        # Look for title in first few lines
        for line in lines[:10]:
            line = line.strip()
            
            # Skip very short or very long lines
            if len(line) < 10 or len(line) > 200:
                continue
            
            # Skip lines that look like headers/footers
            if re.match(r'^\d+$', line) or 'page' in line.lower():
                continue
            
            # If line has reasonable title characteristics
            if len(line.split()) >= 3:  # At least 3 words
                return clean_text(line)
        
        return "Untitled Document"
    
    def _extract_abstract(self, text: str) -> str:
        """Extract abstract from text"""
        # Look for abstract section
        abstract_pattern = r'(?i)abstract\s*[:.]?\s*(.*?)(?=\n\s*(?:keywords|introduction|1\.|i\.)|$)'
        match = re.search(abstract_pattern, text, re.DOTALL)
        
        if match:
            abstract_text = match.group(1).strip()
            # Clean up the abstract
            abstract_text = re.sub(r'\s+', ' ', abstract_text)
            return clean_text(abstract_text)
        
        return ""
    
    def _extract_authors(self, text: str) -> List[str]:
        """Extract authors from text"""
        return extract_authors_from_text(text)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Look for keywords section
        keywords_pattern = r'(?i)keywords?\s*[:.]?\s*(.*?)(?=\n\s*(?:introduction|1\.|i\.)|$)'
        match = re.search(keywords_pattern, text, re.DOTALL)
        
        if match:
            keywords_text = match.group(1)
            # Split by common delimiters
            keywords = re.split(r'[,;]', keywords_text)
            return [clean_text(kw) for kw in keywords if clean_text(kw)]
        
        return []
    
    def _extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from text"""
        return extract_citations(text)