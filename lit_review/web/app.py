"""
Flask web application for the literature review platform
"""

import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from typing import Dict, Any

from ..utils.config import Config
from ..storage.document_storage import DocumentStorage
from ..storage.vector_storage import VectorStorage
from ..analysis.citation_analyzer import CitationAnalyzer
from ..analysis.coauthorship_analyzer import CoAuthorshipAnalyzer


def create_app(config: Config = None) -> Flask:
    """
    Create Flask application
    
    Args:
        config: Configuration object
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Initialize configuration
    if config is None:
        config = Config()
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Enable CORS
    CORS(app)
    
    # Initialize storage and analysis components
    document_storage = DocumentStorage(config)
    vector_storage = VectorStorage(config)
    citation_analyzer = CitationAnalyzer(document_storage)
    coauthorship_analyzer = CoAuthorshipAnalyzer(document_storage)
    
    # Routes
    @app.route('/')
    def index():
        """Main page"""
        return render_template('index.html')
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'version': '0.1.0'})
    
    @app.route('/api/statistics')
    def get_statistics():
        """Get collection statistics"""
        try:
            stats = document_storage.get_statistics()
            vector_stats = vector_storage.get_collection_stats()
            
            return jsonify({
                'database': stats,
                'vector_store': vector_stats
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/search')
    def search_documents():
        """Search documents"""
        try:
            # Get query parameters
            query = request.args.get('q', '')
            author = request.args.get('author')
            year = request.args.get('year', type=int)
            keywords = request.args.getlist('keywords')
            limit = request.args.get('limit', 20, type=int)
            semantic = request.args.get('semantic', 'false').lower() == 'true'
            
            if semantic and query:
                # Semantic search
                results = vector_storage.semantic_search(query, n_results=limit)
                
                # Get full document details
                documents = []
                for result in results:
                    doc_id = result['metadata'].get('document_id')
                    if doc_id:
                        doc = document_storage.get_document(doc_id)
                        if doc:
                            doc_dict = doc.to_dict()
                            doc_dict['similarity_score'] = 1 - result.get('distance', 0)
                            documents.append(doc_dict)
                
                return jsonify({
                    'documents': documents,
                    'total': len(documents),
                    'search_type': 'semantic'
                })
            else:
                # Traditional search
                documents = document_storage.search_documents(
                    query=query,
                    author=author,
                    year=year,
                    keywords=keywords,
                    limit=limit
                )
                
                return jsonify({
                    'documents': [doc.to_dict() for doc in documents],
                    'total': len(documents),
                    'search_type': 'traditional'
                })
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/documents/<int:doc_id>')
    def get_document_details(doc_id: int):
        """Get detailed document information"""
        try:
            document = document_storage.get_document(doc_id)
            if not document:
                return jsonify({'error': 'Document not found'}), 404
            
            # Get citation network for this document
            citation_network = document_storage.get_citation_network(doc_id)
            
            # Get similar documents
            similar_docs = vector_storage.find_similar_documents(doc_id, n_results=5)
            
            return jsonify({
                'document': document.to_dict(),
                'citation_network': citation_network,
                'similar_documents': similar_docs
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/authors/<path:author_name>')
    def get_author_profile(author_name: str):
        """Get author profile and collaboration information"""
        try:
            profile = coauthorship_analyzer.get_author_profile(author_name)
            
            if 'error' in profile:
                return jsonify(profile), 404
            
            return jsonify(profile)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analysis/citations')
    def get_citation_analysis():
        """Get citation analysis"""
        try:
            analysis_type = request.args.get('type', 'overview')
            
            if analysis_type == 'overview':
                analysis = citation_analyzer.analyze_citation_patterns()
            elif analysis_type == 'most_cited':
                limit = request.args.get('limit', 10, type=int)
                analysis = citation_analyzer.get_most_cited_papers(limit)
            elif analysis_type == 'most_citing':
                limit = request.args.get('limit', 10, type=int)
                analysis = citation_analyzer.get_most_citing_papers(limit)
            elif analysis_type == 'timeline':
                analysis = citation_analyzer.get_citation_timeline()
            elif analysis_type == 'clusters':
                analysis = citation_analyzer.find_citation_clusters()
            else:
                return jsonify({'error': 'Invalid analysis type'}), 400
            
            return jsonify(analysis)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analysis/collaboration')
    def get_collaboration_analysis():
        """Get co-authorship analysis"""
        try:
            analysis_type = request.args.get('type', 'overview')
            
            if analysis_type == 'overview':
                analysis = coauthorship_analyzer.analyze_author_centrality()
            elif analysis_type == 'most_collaborative':
                limit = request.args.get('limit', 10, type=int)
                analysis = coauthorship_analyzer.get_most_collaborative_authors(limit)
            elif analysis_type == 'strongest_collaborations':
                limit = request.args.get('limit', 10, type=int)
                analysis = coauthorship_analyzer.get_strongest_collaborations(limit)
            elif analysis_type == 'communities':
                analysis = coauthorship_analyzer.find_research_communities()
            elif analysis_type == 'timeline':
                analysis = coauthorship_analyzer.get_collaboration_timeline()
            else:
                return jsonify({'error': 'Invalid analysis type'}), 400
            
            return jsonify(analysis)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/query', methods=['POST'])
    def natural_language_query():
        """Handle natural language queries"""
        try:
            data = request.get_json()
            query = data.get('query', '')
            
            if not query:
                return jsonify({'error': 'Query is required'}), 400
            
            # Analyze query to determine intent
            query_lower = query.lower()
            
            if 'cognitively guided instruction' in query_lower or 'cgi' in query_lower:
                # Search for CGI-related papers
                results = document_storage.search_documents(
                    query='cognitively guided instruction',
                    limit=20
                )
                
                return jsonify({
                    'query': query,
                    'interpretation': 'Searching for papers about Cognitively Guided Instruction',
                    'results': [doc.to_dict() for doc in results],
                    'total': len(results)
                })
            
            elif 'co-author' in query_lower or 'collaborated' in query_lower:
                # Extract author names and find collaborations
                # Simple extraction - could be improved with NLP
                import re
                names = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+', query)
                
                if names:
                    author_name = names[0]
                    profile = coauthorship_analyzer.get_author_profile(author_name)
                    
                    return jsonify({
                        'query': query,
                        'interpretation': f'Finding collaborations for {author_name}',
                        'results': profile
                    })
            
            elif 'cited by' in query_lower or 'citations' in query_lower:
                # Citation analysis query
                if 'most cited' in query_lower:
                    results = citation_analyzer.get_most_cited_papers(10)
                    
                    return jsonify({
                        'query': query,
                        'interpretation': 'Finding most cited papers',
                        'results': results
                    })
            
            # Default: semantic search
            results = vector_storage.semantic_search(query, n_results=10)
            
            # Get full document details
            documents = []
            for result in results:
                doc_id = result['metadata'].get('document_id')
                if doc_id:
                    doc = document_storage.get_document(doc_id)
                    if doc:
                        doc_dict = doc.to_dict()
                        doc_dict['similarity_score'] = 1 - result.get('distance', 0)
                        documents.append(doc_dict)
            
            return jsonify({
                'query': query,
                'interpretation': 'Semantic search across all documents',
                'results': documents,
                'total': len(documents)
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app