"""
Command-line interface for the literature review platform
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List
import os

from .utils.config import Config
from .processors.docling_processor import DoclingProcessor
from .processors.pdf_processor import PDFProcessor  
from .storage.document_storage import DocumentStorage
from .storage.vector_storage import VectorStorage
from .web.app import create_app


def setup_logging(level: str = 'INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('lit_review.log')
        ]
    )


def process_single_pdf(pdf_path: str, config: Config, use_docling: bool = True) -> bool:
    """
    Process a single PDF file
    
    Args:
        pdf_path: Path to PDF file
        config: Configuration object
        use_docling: Whether to use docling or fallback processor
        
    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Choose processor
        if use_docling:
            try:
                processor = DoclingProcessor()
                logger.info(f"Using Docling processor for {pdf_path}")
            except ImportError:
                logger.warning("Docling not available, falling back to basic PDF processor")
                processor = PDFProcessor()
        else:
            processor = PDFProcessor()
            logger.info(f"Using fallback PDF processor for {pdf_path}")
        
        # Process the PDF
        processed_doc = processor.process_pdf(pdf_path)
        
        # Store in database
        storage = DocumentStorage(config)
        document = storage.store_document(
            title=processed_doc.title,
            content=processed_doc.content,
            file_path=pdf_path,
            abstract=processed_doc.abstract,
            authors=processed_doc.authors,
            keywords=processed_doc.keywords,
            citations=processed_doc.citations,
            metadata=processed_doc.metadata
        )
        
        # Store in vector database
        vector_storage = VectorStorage(config)
        vector_storage.add_document(
            document_id=document.id,
            title=processed_doc.title,
            abstract=processed_doc.abstract,
            content=processed_doc.content,
            metadata=processed_doc.metadata
        )
        
        # Add document sections if available
        if processed_doc.sections:
            vector_storage.add_document_sections(
                document_id=document.id,
                sections=processed_doc.sections
            )
        
        logger.info(f"Successfully processed and stored: {processed_doc.title}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return False


def process_directory(directory: str, config: Config, use_docling: bool = True, max_files: int = None) -> None:
    """
    Process all PDF files in a directory
    
    Args:
        directory: Directory containing PDF files
        config: Configuration object
        use_docling: Whether to use docling or fallback processor
        max_files: Maximum number of files to process (None for all)
    """
    logger = logging.getLogger(__name__)
    
    pdf_files = list(Path(directory).glob('**/*.pdf'))
    
    if max_files:
        pdf_files = pdf_files[:max_files]
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    successful = 0
    failed = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"Processing file {i}/{len(pdf_files)}: {pdf_file.name}")
        
        if process_single_pdf(str(pdf_file), config, use_docling):
            successful += 1
        else:
            failed += 1
        
        # Progress update
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(pdf_files)} files processed ({successful} successful, {failed} failed)")
    
    logger.info(f"Processing complete. {successful} successful, {failed} failed out of {len(pdf_files)} total files.")


def run_web_server(config: Config) -> None:
    """Run the web server"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting web server on {config.flask_host}:{config.flask_port}")
    
    app = create_app(config)
    app.run(
        host=config.flask_host,
        port=config.flask_port,
        debug=config.flask_debug
    )


def initialize_database(config: Config) -> None:
    """Initialize the database and create tables"""
    logger = logging.getLogger(__name__)
    logger.info("Initializing database...")
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Initialize storage (this creates tables)
    storage = DocumentStorage(config)
    vector_storage = VectorStorage(config)
    
    logger.info("Database initialization complete")


def show_statistics(config: Config) -> None:
    """Show collection statistics"""
    storage = DocumentStorage(config)
    vector_storage = VectorStorage(config)
    
    stats = storage.get_statistics()
    vector_stats = vector_storage.get_collection_stats()
    
    print("\n=== Literature Review Collection Statistics ===")
    print(f"Total Documents: {stats.get('total_documents', 0)}")
    print(f"Total Authors: {stats.get('total_authors', 0)}")
    print(f"Total Keywords: {stats.get('total_keywords', 0)}")
    print(f"Total Citations: {stats.get('total_citations', 0)}")
    print(f"Vector Documents: {vector_stats.get('documents_count', 0)}")
    print(f"Vector Sections: {vector_stats.get('sections_count', 0)}")
    
    year_dist = stats.get('year_distribution', {})
    if year_dist:
        print("\n=== Publication Years ===")
        for year in sorted(year_dist.keys()):
            print(f"{year}: {year_dist[year]} papers")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Literature Review Platform CLI')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--config', help='Path to configuration file')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize database and directories')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process PDF files')
    process_parser.add_argument('input', help='PDF file or directory to process')
    process_parser.add_argument('--no-docling', action='store_true', help='Use fallback processor instead of docling')
    process_parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    
    # Web server command
    web_parser = subparsers.add_parser('web', help='Start web server')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show collection statistics')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Load configuration
    if args.config:
        config = Config(args.config)
    else:
        config = Config()
    
    # Execute command
    if args.command == 'init':
        initialize_database(config)
    
    elif args.command == 'process':
        input_path = Path(args.input)
        use_docling = not args.no_docling
        
        if not input_path.exists():
            print(f"Error: {input_path} does not exist")
            sys.exit(1)
        
        if input_path.is_file():
            if input_path.suffix.lower() == '.pdf':
                process_single_pdf(str(input_path), config, use_docling)
            else:
                print(f"Error: {input_path} is not a PDF file")
                sys.exit(1)
        elif input_path.is_dir():
            process_directory(str(input_path), config, use_docling, args.max_files)
        else:
            print(f"Error: {input_path} is neither a file nor directory")
            sys.exit(1)
    
    elif args.command == 'web':
        run_web_server(config)
    
    elif args.command == 'stats':
        show_statistics(config)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()