"""
Document storage and database management
"""

import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from ..models import Base, Document, Author, Citation, Keyword, VectorEmbedding
from ..utils.config import Config


class DocumentStorage:
    """
    Manages document storage in SQL database
    """
    
    def __init__(self, config: Config):
        """
        Initialize document storage
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.engine = create_engine(config.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def store_document(self, 
                      title: str,
                      content: str,
                      file_path: str,
                      abstract: str = None,
                      authors: List[str] = None,
                      keywords: List[str] = None,
                      citations: List[Dict[str, Any]] = None,
                      metadata: Dict[str, Any] = None,
                      **kwargs) -> Document:
        """
        Store a document in the database
        
        Args:
            title: Document title
            content: Full document content
            file_path: Path to original file
            abstract: Document abstract
            authors: List of author names
            keywords: List of keywords
            citations: List of citation data
            metadata: Additional metadata
            **kwargs: Additional document fields
            
        Returns:
            Stored Document object
        """
        session = self.get_session()
        
        try:
            # Create document
            document = Document(
                title=title,
                content=content,
                file_path=file_path,
                abstract=abstract or "",
                docling_metadata=json.dumps(metadata or {}),
                **kwargs
            )
            
            session.add(document)
            session.flush()  # Get document ID
            
            # Add authors
            if authors:
                for author_name in authors:
                    author = self._get_or_create_author(session, author_name)
                    document.authors.append(author)
            
            # Add keywords
            if keywords:
                for keyword_name in keywords:
                    keyword = self._get_or_create_keyword(session, keyword_name)
                    document.keywords.append(keyword)
            
            # Add citations
            if citations:
                for citation_data in citations:
                    citation = Citation(
                        citing_document_id=document.id,
                        citation_text=citation_data.get('text', ''),
                        external_title=citation_data.get('title', ''),
                        external_authors=citation_data.get('authors_text', ''),
                        external_year=citation_data.get('year'),
                        external_doi=citation_data.get('doi', '')
                    )
                    session.add(citation)
            
            session.commit()
            self.logger.info(f"Stored document: {title}")
            return document
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing document {title}: {str(e)}")
            raise
        finally:
            session.close()
    
    def _get_or_create_author(self, session: Session, name: str) -> Author:
        """Get existing author or create new one"""
        author = session.query(Author).filter(Author.name == name).first()
        if not author:
            author = Author(name=name)
            session.add(author)
            session.flush()
        return author
    
    def _get_or_create_keyword(self, session: Session, name: str) -> Keyword:
        """Get existing keyword or create new one"""
        keyword = session.query(Keyword).filter(Keyword.name == name).first()
        if not keyword:
            keyword = Keyword(name=name)
            session.add(keyword)
            session.flush()
        return keyword
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        session = self.get_session()
        try:
            return session.query(Document).filter(Document.id == document_id).first()
        finally:
            session.close()
    
    def get_documents_by_author(self, author_name: str) -> List[Document]:
        """Get all documents by a specific author"""
        session = self.get_session()
        try:
            return (session.query(Document)
                   .join(Document.authors)
                   .filter(Author.name.ilike(f'%{author_name}%'))
                   .all())
        finally:
            session.close()
    
    def search_documents(self, 
                        query: str = None,
                        author: str = None, 
                        year: int = None,
                        keywords: List[str] = None,
                        limit: int = 100) -> List[Document]:
        """
        Search documents with various filters
        
        Args:
            query: Text query (searches title, abstract, content)
            author: Author name filter
            year: Publication year filter
            keywords: Keyword filters
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        session = self.get_session()
        
        try:
            query_obj = session.query(Document)
            
            # Text search
            if query:
                query_obj = query_obj.filter(
                    Document.title.ilike(f'%{query}%') |
                    Document.abstract.ilike(f'%{query}%') |
                    Document.content.ilike(f'%{query}%')
                )
            
            # Author filter
            if author:
                query_obj = (query_obj
                           .join(Document.authors)
                           .filter(Author.name.ilike(f'%{author}%')))
            
            # Year filter
            if year:
                query_obj = query_obj.filter(Document.publication_year == year)
            
            # Keywords filter
            if keywords:
                for keyword in keywords:
                    query_obj = (query_obj
                               .join(Document.keywords)
                               .filter(Keyword.name.ilike(f'%{keyword}%')))
            
            return query_obj.limit(limit).all()
            
        finally:
            session.close()
    
    def get_citation_network(self, document_id: int) -> Dict[str, Any]:
        """
        Get citation network for a document
        
        Args:
            document_id: Document ID
            
        Returns:
            Citation network data
        """
        session = self.get_session()
        
        try:
            document = session.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {}
            
            # Get citations made by this document
            citations_made = session.query(Citation).filter(
                Citation.citing_document_id == document_id
            ).all()
            
            # Get citations received by this document
            citations_received = session.query(Citation).filter(
                Citation.cited_document_id == document_id
            ).all()
            
            return {
                'document': document.to_dict(),
                'citations_made': [
                    {
                        'text': c.citation_text,
                        'external_title': c.external_title,
                        'external_authors': c.external_authors,
                        'external_year': c.external_year,
                        'cited_document': c.cited_document.to_dict() if c.cited_document else None
                    }
                    for c in citations_made
                ],
                'citations_received': [
                    {
                        'text': c.citation_text,
                        'citing_document': c.citing_document.to_dict()
                    }
                    for c in citations_received
                ]
            }
            
        finally:
            session.close()
    
    def get_coauthorship_network(self, author_name: str = None) -> Dict[str, Any]:
        """
        Get co-authorship network data
        
        Args:
            author_name: Specific author to focus on (optional)
            
        Returns:
            Co-authorship network data
        """
        session = self.get_session()
        
        try:
            # Get all author collaborations
            collaborations = {}
            
            if author_name:
                # Focus on specific author
                author = session.query(Author).filter(
                    Author.name.ilike(f'%{author_name}%')
                ).first()
                
                if author:
                    documents = author.documents
                    for doc in documents:
                        authors = [a.name for a in doc.authors]
                        for i, auth1 in enumerate(authors):
                            for auth2 in authors[i+1:]:
                                key = tuple(sorted([auth1, auth2]))
                                collaborations[key] = collaborations.get(key, 0) + 1
            else:
                # Get all collaborations
                documents = session.query(Document).all()
                for doc in documents:
                    authors = [a.name for a in doc.authors]
                    for i, auth1 in enumerate(authors):
                        for auth2 in authors[i+1:]:
                            key = tuple(sorted([auth1, auth2]))
                            collaborations[key] = collaborations.get(key, 0) + 1
            
            return {
                'collaborations': [
                    {
                        'authors': list(key),
                        'count': count
                    }
                    for key, count in collaborations.items()
                ]
            }
            
        finally:
            session.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        session = self.get_session()
        
        try:
            stats = {
                'total_documents': session.query(Document).count(),
                'total_authors': session.query(Author).count(),
                'total_keywords': session.query(Keyword).count(),
                'total_citations': session.query(Citation).count(),
            }
            
            # Year distribution
            year_dist = (session.query(Document.publication_year, 
                                     session.query(Document)
                                     .filter(Document.publication_year == Document.publication_year)
                                     .count().label('count'))
                        .filter(Document.publication_year.isnot(None))
                        .group_by(Document.publication_year)
                        .all())
            
            stats['year_distribution'] = {year: count for year, count in year_dist}
            
            return stats
            
        finally:
            session.close()