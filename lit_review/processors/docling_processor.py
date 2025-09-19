"""
Docling-based PDF processor for extracting structured content
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption
except ImportError:
    logging.warning("Docling not available. Please install docling>=2.3.1")
    DocumentConverter = None

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


class DoclingProcessor:
    """
    PDF processor using Docling for structured content extraction
    """
    
    def __init__(self, 
                 preserve_images: bool = True,
                 preserve_equations: bool = True,
                 extract_tables: bool = True):
        """
        Initialize DoclingProcessor
        
        Args:
            preserve_images: Whether to preserve images in the output
            preserve_equations: Whether to preserve mathematical equations
            extract_tables: Whether to extract table structures
        """
        if DocumentConverter is None:
            raise ImportError("Docling is required but not installed. Please install docling>=2.3.1")
        
        self.preserve_images = preserve_images
        self.preserve_equations = preserve_equations
        self.extract_tables = extract_tables
        
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=extract_tables,
            table_structure_options={
                "do_cell_matching": True,
                "mode": "accurate"
            }
        )
        
        # Initialize converter
        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
        
        self.converter = DocumentConverter(
            format_options=format_options
        )
        
        self.logger = logging.getLogger(__name__)
    
    def process_pdf(self, pdf_path: str) -> ProcessedDocument:
        """
        Process a PDF file and extract structured content
        
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
            # Convert document
            result = self.converter.convert(str(pdf_path))
            
            # Extract structured content
            content_data = self._extract_content(result)
            
            # Extract metadata
            metadata = self._extract_metadata(result, pdf_path)
            
            # Extract sections
            sections = self._extract_sections(result)
            
            # Process text content
            title = self._extract_title(content_data)
            abstract = self._extract_abstract(content_data)
            full_content = content_data.get('text', '')
            
            # Extract entities
            authors = self._extract_authors(content_data, metadata)
            keywords = self._extract_keywords(content_data)
            citations = self._extract_citations(content_data)
            
            return ProcessedDocument(
                title=title,
                abstract=abstract,
                content=full_content,
                authors=authors,
                keywords=keywords,
                citations=citations,
                metadata=metadata,
                sections=sections
            )
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
    
    def _extract_content(self, result) -> Dict[str, Any]:
        """Extract content from docling result"""
        try:
            # Get document content
            content = {
                'text': result.document.export_to_text(),
                'markdown': result.document.export_to_markdown(),
                'json': result.document.export_to_dict()
            }
            return content
        except Exception as e:
            self.logger.error(f"Error extracting content: {str(e)}")
            return {'text': '', 'markdown': '', 'json': {}}
    
    def _extract_metadata(self, result, pdf_path: Path) -> Dict[str, Any]:
        """Extract metadata from docling result"""
        metadata = {
            'file_name': pdf_path.name,
            'file_size': pdf_path.stat().st_size,
            'docling_version': '2.3.1',  # Track docling version used
        }
        
        try:
            # Extract document metadata if available
            doc_dict = result.document.export_to_dict()
            if 'metadata' in doc_dict:
                metadata.update(doc_dict['metadata'])
            
            # Add page count and other structural info
            if hasattr(result.document, 'pages'):
                metadata['page_count'] = len(result.document.pages)
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    def _extract_sections(self, result) -> List[Dict[str, Any]]:
        """Extract document sections with structure"""
        sections = []
        
        try:
            doc_dict = result.document.export_to_dict()
            
            # Extract hierarchical structure
            if 'main-text' in doc_dict:
                for item in doc_dict['main-text']:
                    if item.get('prov', [{}])[0].get('page') is not None:
                        section = {
                            'type': item.get('label', 'unknown'),
                            'content': item.get('text', ''),
                            'page': item.get('prov', [{}])[0].get('page'),
                            'bbox': item.get('prov', [{}])[0].get('bbox'),
                        }
                        sections.append(section)
            
        except Exception as e:
            self.logger.error(f"Error extracting sections: {str(e)}")
        
        return sections
    
    def _extract_title(self, content_data: Dict[str, Any]) -> str:
        """Extract document title"""
        try:
            # Try to extract from structured data first
            doc_json = content_data.get('json', {})
            
            # Look for title in document structure
            if 'main-text' in doc_json:
                for item in doc_json['main-text']:
                    if item.get('label') == 'title':
                        return clean_text(item.get('text', ''))
            
            # Fallback: extract from beginning of text
            text = content_data.get('text', '')
            lines = text.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if len(line) > 10 and len(line) < 200:  # Reasonable title length
                    return clean_text(line)
            
            return "Untitled Document"
            
        except Exception as e:
            self.logger.error(f"Error extracting title: {str(e)}")
            return "Untitled Document"
    
    def _extract_abstract(self, content_data: Dict[str, Any]) -> str:
        """Extract document abstract"""
        try:
            doc_json = content_data.get('json', {})
            
            # Look for abstract in structured data
            if 'main-text' in doc_json:
                for item in doc_json['main-text']:
                    if item.get('label') == 'abstract':
                        return clean_text(item.get('text', ''))
            
            # Fallback: search in text
            text = content_data.get('text', '')
            abstract_pattern = r'(?i)abstract\s*[:.]?\s*(.*?)(?=\n\s*(?:keywords|introduction|1\.|i\.)|$)'
            match = re.search(abstract_pattern, text, re.DOTALL)
            if match:
                return clean_text(match.group(1))
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting abstract: {str(e)}")
            return ""
    
    def _extract_authors(self, content_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        """Extract document authors"""
        try:
            # Try metadata first
            if 'authors' in metadata:
                return metadata['authors']
            
            # Extract from text
            text = content_data.get('text', '')
            authors = extract_authors_from_text(text)
            return authors
            
        except Exception as e:
            self.logger.error(f"Error extracting authors: {str(e)}")
            return []
    
    def _extract_keywords(self, content_data: Dict[str, Any]) -> List[str]:
        """Extract keywords from document"""
        try:
            text = content_data.get('text', '')
            
            # Look for explicit keywords section
            keywords_pattern = r'(?i)keywords?\s*[:.]?\s*(.*?)(?=\n\s*(?:introduction|1\.|i\.)|$)'
            match = re.search(keywords_pattern, text, re.DOTALL)
            if match:
                keywords_text = match.group(1)
                # Split by common delimiters
                keywords = re.split(r'[,;]', keywords_text)
                return [clean_text(kw) for kw in keywords if clean_text(kw)]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    def _extract_citations(self, content_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract citations from document"""
        try:
            text = content_data.get('text', '')
            citations = extract_citations(text)
            return citations
            
        except Exception as e:
            self.logger.error(f"Error extracting citations: {str(e)}")
            return []