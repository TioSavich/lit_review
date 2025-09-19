"""
Text processing utilities for extracting information from academic documents
"""

import re
from typing import List, Dict, Any
import logging


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    return text.strip()


def extract_authors_from_text(text: str) -> List[str]:
    """
    Extract author names from document text
    
    Args:
        text: Document text
        
    Returns:
        List of author names
    """
    authors = []
    
    # Look for author patterns after title
    lines = text.split('\n')[:20]  # Check first 20 lines
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip very short or very long lines
        if len(line) < 5 or len(line) > 200:
            continue
        
        # Check if line contains potential author names
        # Look for patterns like "John Smith, Jane Doe" or "J. Smith and J. Doe"
        author_patterns = [
            r'^[A-Z][a-z]+ [A-Z][a-z]+(?:,\s*[A-Z][a-z]+ [A-Z][a-z]+)*$',
            r'^[A-Z]\.\s*[A-Z][a-z]+(?:,\s*[A-Z]\.\s*[A-Z][a-z]+)*$',
            r'^[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+(?:,\s*[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)*$',
        ]
        
        for pattern in author_patterns:
            if re.match(pattern, line):
                # Split by comma and clean
                author_list = [clean_text(author) for author in re.split(r',|\s+and\s+', line)]
                authors.extend([author for author in author_list if author])
                break
    
    return list(set(authors))  # Remove duplicates


def extract_citations(text: str) -> List[Dict[str, Any]]:
    """
    Extract citations from document text
    
    Args:
        text: Document text
        
    Returns:
        List of citation dictionaries
    """
    citations = []
    
    # Pattern for references section
    references_pattern = r'(?i)(?:references|bibliography|works\s+cited)\s*\n(.*?)(?=\n\s*(?:appendix|index|$))'
    
    match = re.search(references_pattern, text, re.DOTALL)
    if match:
        references_text = match.group(1)
        
        # Split references by common patterns
        ref_patterns = [
            r'\n\s*\[\d+\]',  # [1], [2], etc.
            r'\n\s*\d+\.',    # 1., 2., etc.
            r'\n\s*[A-Z][a-z]+,\s*[A-Z]',  # Author last name pattern
        ]
        
        for pattern in ref_patterns:
            refs = re.split(pattern, references_text)
            if len(refs) > 3:  # If we found multiple references
                for ref in refs[1:]:  # Skip first empty split
                    ref = clean_text(ref)
                    if len(ref) > 20:  # Minimum citation length
                        citation = _parse_citation(ref)
                        if citation:
                            citations.append(citation)
                break
    
    # Also look for in-text citations
    in_text_citations = _extract_in_text_citations(text)
    citations.extend(in_text_citations)
    
    return citations


def _parse_citation(citation_text: str) -> Dict[str, Any]:
    """Parse a single citation text into structured data"""
    citation = {
        'text': citation_text,
        'authors': [],
        'title': '',
        'year': None,
        'journal': '',
        'doi': ''
    }
    
    # Extract DOI
    doi_pattern = r'(?:doi:|DOI:)\s*(10\.\d+/[^\s]+)'
    doi_match = re.search(doi_pattern, citation_text, re.IGNORECASE)
    if doi_match:
        citation['doi'] = doi_match.group(1)
    
    # Extract year
    year_pattern = r'\b(19|20)\d{2}\b'
    year_matches = re.findall(year_pattern, citation_text)
    if year_matches:
        citation['year'] = int(year_matches[0] + year_matches[0][2:])
    
    # Extract title (often in quotes or italics)
    title_patterns = [
        r'"([^"]+)"',
        r''([^']+)'',
        r'["""]([^"""]+)["""]'
    ]
    
    for pattern in title_patterns:
        title_match = re.search(pattern, citation_text)
        if title_match:
            citation['title'] = clean_text(title_match.group(1))
            break
    
    # Extract journal name (often after title, before year)
    if citation['title']:
        # Remove title from text for journal extraction
        text_without_title = citation_text.replace(citation['title'], '')
        # Look for italicized text or text patterns that could be journal names
        journal_pattern = r'\b([A-Z][a-zA-Z\s&]+(?:Journal|Review|Magazine|Quarterly|Annual))\b'
        journal_match = re.search(journal_pattern, text_without_title)
        if journal_match:
            citation['journal'] = clean_text(journal_match.group(1))
    
    return citation


def _extract_in_text_citations(text: str) -> List[Dict[str, Any]]:
    """Extract in-text citations like (Smith, 2020) or [1]"""
    citations = []
    
    # Pattern for author-year citations
    author_year_pattern = r'\(([A-Z][a-zA-Z]+(?:\s+(?:and|&)\s+[A-Z][a-zA-Z]+)*),\s*(\d{4})\)'
    
    for match in re.finditer(author_year_pattern, text):
        authors_text = match.group(1)
        year = int(match.group(2))
        
        # Split authors
        authors = re.split(r'\s+(?:and|&)\s+', authors_text)
        
        citation = {
            'type': 'in_text',
            'authors': [clean_text(author) for author in authors],
            'year': year,
            'text': match.group(0)
        }
        citations.append(citation)
    
    # Pattern for numbered citations
    numbered_pattern = r'\[(\d+)\]'
    
    for match in re.finditer(numbered_pattern, text):
        citation = {
            'type': 'numbered',
            'number': int(match.group(1)),
            'text': match.group(0)
        }
        citations.append(citation)
    
    return citations


def extract_math_education_keywords(text: str) -> List[str]:
    """
    Extract mathematics education specific keywords
    
    Args:
        text: Document text
        
    Returns:
        List of relevant keywords
    """
    # Mathematics education specific terms
    math_ed_terms = [
        'cognitively guided instruction', 'cgi', 'problem solving',
        'mathematical reasoning', 'number sense', 'algebraic thinking',
        'geometric reasoning', 'statistical literacy', 'mathematical modeling',
        'conceptual understanding', 'procedural fluency', 'strategic competence',
        'adaptive reasoning', 'productive disposition', 'mathematics anxiety',
        'mathematics discourse', 'mathematical communication', 'representation',
        'mathematical practices', 'inquiry-based learning', 'constructivism',
        'sociocultural theory', 'zone of proximal development', 'scaffolding',
        'differentiated instruction', 'formative assessment', 'summative assessment',
        'mathematical proof', 'mathematical argumentation', 'visual mathematics',
        'manipulatives', 'technology integration', 'calculator use',
        'dynamic geometry', 'computer algebra systems', 'graphing calculators',
        'fraction understanding', 'decimal concepts', 'rational numbers',
        'proportional reasoning', 'functions', 'algebra', 'geometry',
        'measurement', 'data analysis', 'probability', 'statistics',
        'calculus', 'discrete mathematics', 'mathematical connections',
        'problem-based learning', 'collaborative learning', 'peer tutoring',
        'mathematics teacher education', 'professional development',
        'mathematics curriculum', 'standards-based mathematics',
        'common core', 'nctm standards', 'mathematical literacy'
    ]
    
    found_keywords = []
    text_lower = text.lower()
    
    for term in math_ed_terms:
        if term.lower() in text_lower:
            found_keywords.append(term)
    
    return found_keywords