#!/usr/bin/env python3
"""
Batch processing script for mathematics education literature collection

This script demonstrates how to process a large collection of PDFs
and perform analysis on the results.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lit_review.utils.config import Config
from lit_review.cli import process_directory, initialize_database, show_statistics
from lit_review.storage.document_storage import DocumentStorage
from lit_review.analysis.citation_analyzer import CitationAnalyzer
from lit_review.analysis.coauthorship_analyzer import CoAuthorshipAnalyzer


def setup_logging():
    """Configure logging for batch processing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('batch_processing.log')
        ]
    )


def main():
    """Main batch processing workflow"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Configuration
    config = Config()
    
    logger.info("Starting batch processing for mathematics education literature collection")
    
    # Step 1: Initialize database if needed
    logger.info("Initializing database...")
    initialize_database(config)
    
    # Step 2: Check if we have PDFs to process
    pdf_directory = input("Enter the path to your PDF collection: ").strip()
    if not os.path.exists(pdf_directory):
        logger.error(f"Directory not found: {pdf_directory}")
        return
    
    pdf_files = list(Path(pdf_directory).glob('**/*.pdf'))
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    if len(pdf_files) == 0:
        logger.warning("No PDF files found in the specified directory")
        return
    
    # Step 3: Process PDFs
    max_files = input(f"Process all {len(pdf_files)} files? Enter max number or 'all': ").strip()
    if max_files.lower() != 'all':
        try:
            max_files = int(max_files)
        except ValueError:
            max_files = None
    else:
        max_files = None
    
    logger.info("Starting PDF processing...")
    try:
        process_directory(pdf_directory, config, use_docling=True, max_files=max_files)
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        logger.info("Trying with fallback processor...")
        process_directory(pdf_directory, config, use_docling=False, max_files=max_files)
    
    # Step 4: Show statistics
    logger.info("Processing complete. Generating statistics...")
    show_statistics(config)
    
    # Step 5: Perform analysis
    logger.info("Performing citation and collaboration analysis...")
    analyze_collection(config)
    
    logger.info("Batch processing complete!")
    logger.info("You can now start the web interface with: python -m lit_review.cli web")


def analyze_collection(config: Config):
    """Perform analysis on the processed collection"""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize analyzers
        storage = DocumentStorage(config)
        citation_analyzer = CitationAnalyzer(storage)
        coauthorship_analyzer = CoAuthorshipAnalyzer(storage)
        
        logger.info("Analyzing citation patterns...")
        citation_analysis = citation_analyzer.analyze_citation_patterns()
        
        logger.info("Citation Analysis Results:")
        logger.info(f"  Total papers: {citation_analysis.get('total_papers', 0)}")
        logger.info(f"  Total citations: {citation_analysis.get('total_citations', 0)}")
        logger.info(f"  Average citations per paper: {citation_analysis.get('average_citations_per_paper', 0):.2f}")
        
        # Get most cited papers
        most_cited = citation_analyzer.get_most_cited_papers(5)
        if most_cited:
            logger.info("Top 5 most cited papers:")
            for i, paper in enumerate(most_cited, 1):
                logger.info(f"  {i}. {paper['document']['title']} ({paper['citation_count']} citations)")
        
        logger.info("Analyzing collaboration patterns...")
        collab_analysis = coauthorship_analyzer.analyze_author_centrality()
        
        logger.info("Collaboration Analysis Results:")
        logger.info(f"  Total authors: {collab_analysis.get('total_authors', 0)}")
        logger.info(f"  Total collaborations: {collab_analysis.get('total_collaborations', 0)}")
        logger.info(f"  Average collaborators per author: {collab_analysis.get('average_collaborators_per_author', 0):.2f}")
        
        # Get most collaborative authors
        most_collaborative = coauthorship_analyzer.get_most_collaborative_authors(5)
        if most_collaborative:
            logger.info("Top 5 most collaborative authors:")
            for i, author in enumerate(most_collaborative, 1):
                logger.info(f"  {i}. {author['name']} ({author['unique_collaborators']} collaborators)")
        
        # Find research communities
        communities = coauthorship_analyzer.find_research_communities()
        if communities:
            logger.info(f"Found {len(communities)} research communities:")
            for i, community in enumerate(communities[:3], 1):
                logger.info(f"  Community {i}: {community['size']} authors, {community['total_papers']} papers")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")


def demonstrate_queries():
    """Demonstrate example queries for mathematics education research"""
    logger = logging.getLogger(__name__)
    
    logger.info("Example queries you can try in the web interface:")
    
    queries = [
        "cognitively guided instruction",
        "mathematical reasoning and problem solving",
        "number sense development",
        "algebraic thinking in elementary students",
        "fraction understanding",
        "mathematical discourse and communication",
        "technology integration in mathematics",
        "formative assessment in mathematics",
        "collaborative learning mathematics",
        "mathematical modeling and real world applications"
    ]
    
    for query in queries:
        logger.info(f"  - {query}")


if __name__ == "__main__":
    main()