"""
Configuration management for the literature review platform
"""

import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv


class Config:
    """Configuration manager for the application"""
    
    def __init__(self, env_file: str = None):
        """
        Initialize configuration
        
        Args:
            env_file: Path to .env file
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to load from default locations
            for env_path in ['.env', '.env.local']:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    break
    
    @property
    def database_url(self) -> str:
        """Database connection URL"""
        return os.getenv('DATABASE_URL', 'sqlite:///lit_review.db')
    
    @property
    def document_storage_path(self) -> Path:
        """Path for storing original documents"""
        path = os.getenv('DOCUMENT_STORAGE_PATH', './documents')
        return Path(path).absolute()
    
    @property
    def processed_storage_path(self) -> Path:
        """Path for storing processed documents"""
        path = os.getenv('PROCESSED_STORAGE_PATH', './processed')
        return Path(path).absolute()
    
    @property
    def vector_db_path(self) -> Path:
        """Path for vector database"""
        path = os.getenv('VECTOR_DB_PATH', './vector_db')
        return Path(path).absolute()
    
    @property
    def flask_host(self) -> str:
        """Flask host"""
        return os.getenv('FLASK_HOST', '0.0.0.0')
    
    @property
    def flask_port(self) -> int:
        """Flask port"""
        return int(os.getenv('FLASK_PORT', 5000))
    
    @property
    def flask_debug(self) -> bool:
        """Flask debug mode"""
        return os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    @property
    def batch_size(self) -> int:
        """Batch size for processing"""
        return int(os.getenv('BATCH_SIZE', 10))
    
    @property
    def max_workers(self) -> int:
        """Maximum number of worker processes"""
        return int(os.getenv('MAX_WORKERS', 4))
    
    @property
    def embedding_model(self) -> str:
        """Sentence transformer model for embeddings"""
        return os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    
    @property
    def spacy_model(self) -> str:
        """spaCy model for NLP"""
        return os.getenv('SPACY_MODEL', 'en_core_web_sm')
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        self.document_storage_path.mkdir(parents=True, exist_ok=True)
        self.processed_storage_path.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)