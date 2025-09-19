"""
Vector storage for semantic search using ChromaDB
"""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

from ..utils.config import Config


class VectorStorage:
    """
    Manages vector embeddings for semantic search
    """
    
    def __init__(self, config: Config):
        """
        Initialize vector storage
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(config.vector_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(config.embedding_model)
        
        # Create collections
        self.documents_collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Document embeddings for semantic search"}
        )
        
        self.sections_collection = self.client.get_or_create_collection(
            name="sections", 
            metadata={"description": "Document section embeddings"}
        )
    
    def add_document(self, 
                    document_id: int,
                    title: str,
                    abstract: str,
                    content: str,
                    metadata: Dict[str, Any] = None) -> None:
        """
        Add document embeddings to vector store
        
        Args:
            document_id: Document ID
            title: Document title
            abstract: Document abstract
            content: Full document content
            metadata: Additional metadata
        """
        try:
            # Prepare document text for embedding
            full_text = f"{title}\n\n{abstract}\n\n{content}"
            
            # Generate embedding
            embedding = self.embedding_model.encode([full_text])[0].tolist()
            
            # Store in ChromaDB
            self.documents_collection.add(
                embeddings=[embedding],
                documents=[full_text],
                metadatas=[{
                    'document_id': document_id,
                    'title': title,
                    'abstract': abstract[:500],  # Truncate for metadata
                    **(metadata or {})
                }],
                ids=[f"doc_{document_id}"]
            )
            
            # Also add title and abstract separately for better granular search
            if title:
                title_embedding = self.embedding_model.encode([title])[0].tolist()
                self.sections_collection.add(
                    embeddings=[title_embedding],
                    documents=[title],
                    metadatas=[{
                        'document_id': document_id,
                        'section_type': 'title',
                        'content': title
                    }],
                    ids=[f"doc_{document_id}_title"]
                )
            
            if abstract:
                abstract_embedding = self.embedding_model.encode([abstract])[0].tolist()
                self.sections_collection.add(
                    embeddings=[abstract_embedding],
                    documents=[abstract],
                    metadatas=[{
                        'document_id': document_id,
                        'section_type': 'abstract',
                        'content': abstract[:1000]  # Store first 1000 chars
                    }],
                    ids=[f"doc_{document_id}_abstract"]
                )
            
            self.logger.info(f"Added document {document_id} to vector store")
            
        except Exception as e:
            self.logger.error(f"Error adding document {document_id} to vector store: {str(e)}")
            raise
    
    def add_document_sections(self,
                            document_id: int,
                            sections: List[Dict[str, Any]]) -> None:
        """
        Add document sections as separate embeddings
        
        Args:
            document_id: Document ID
            sections: List of section dictionaries with 'content', 'type', etc.
        """
        try:
            for i, section in enumerate(sections):
                if not section.get('content'):
                    continue
                
                content = section['content']
                section_type = section.get('type', 'section')
                
                # Generate embedding
                embedding = self.embedding_model.encode([content])[0].tolist()
                
                # Store in sections collection
                self.sections_collection.add(
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        'document_id': document_id,
                        'section_type': section_type,
                        'section_index': i,
                        'page': section.get('page'),
                        'content': content[:1000]  # Store first 1000 chars in metadata
                    }],
                    ids=[f"doc_{document_id}_section_{i}"]
                )
            
            self.logger.info(f"Added {len(sections)} sections for document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Error adding sections for document {document_id}: {str(e)}")
            raise
    
    def semantic_search(self, 
                       query: str,
                       n_results: int = 10,
                       search_sections: bool = False,
                       filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search
        
        Args:
            query: Search query
            n_results: Number of results to return
            search_sections: Whether to search sections instead of full documents
            filter_metadata: Metadata filters
            
        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Choose collection
            collection = self.sections_collection if search_sections else self.documents_collection
            
            # Perform search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error performing semantic search: {str(e)}")
            raise
    
    def find_similar_documents(self, 
                             document_id: int,
                             n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document
        
        Args:
            document_id: Reference document ID
            n_results: Number of similar documents to return
            
        Returns:
            List of similar documents
        """
        try:
            # Get the document from vector store
            doc_result = self.documents_collection.get(
                ids=[f"doc_{document_id}"],
                include=['embeddings']
            )
            
            if not doc_result['embeddings']:
                return []
            
            # Use the document's embedding to find similar ones
            doc_embedding = doc_result['embeddings'][0]
            
            results = self.documents_collection.query(
                query_embeddings=[doc_embedding],
                n_results=n_results + 1,  # +1 because it will include itself
                where={'document_id': {'$ne': document_id}}  # Exclude the query document
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error finding similar documents: {str(e)}")
            raise
    
    def get_document_embedding(self, document_id: int) -> Optional[List[float]]:
        """
        Get embedding for a specific document
        
        Args:
            document_id: Document ID
            
        Returns:
            Document embedding vector
        """
        try:
            result = self.documents_collection.get(
                ids=[f"doc_{document_id}"],
                include=['embeddings']
            )
            
            if result['embeddings']:
                return result['embeddings'][0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting document embedding: {str(e)}")
            return None
    
    def delete_document(self, document_id: int) -> None:
        """
        Delete document embeddings
        
        Args:
            document_id: Document ID to delete
        """
        try:
            # Delete from documents collection
            self.documents_collection.delete(ids=[f"doc_{document_id}"])
            
            # Delete from sections collection (all sections for this document)
            # First, find all sections for this document
            sections_result = self.sections_collection.get(
                where={'document_id': document_id},
                include=['metadatas']
            )
            
            if sections_result['ids']:
                self.sections_collection.delete(ids=sections_result['ids'])
            
            self.logger.info(f"Deleted embeddings for document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting document {document_id} embeddings: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collections"""
        try:
            docs_count = self.documents_collection.count()
            sections_count = self.sections_collection.count()
            
            return {
                'documents_count': docs_count,
                'sections_count': sections_count,
                'embedding_model': self.config.embedding_model,
                'embedding_dimension': len(self.embedding_model.encode(["test"])[0])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {str(e)}")
            return {}