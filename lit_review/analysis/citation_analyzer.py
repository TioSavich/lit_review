"""
Citation network analysis tools
"""

import logging
from typing import Dict, List, Any, Tuple
import networkx as nx
from collections import defaultdict, Counter

from ..storage.document_storage import DocumentStorage


class CitationAnalyzer:
    """
    Analyzes citation networks and patterns
    """
    
    def __init__(self, document_storage: DocumentStorage):
        """
        Initialize citation analyzer
        
        Args:
            document_storage: Document storage instance
        """
        self.storage = document_storage
        self.logger = logging.getLogger(__name__)
    
    def build_citation_network(self) -> nx.DiGraph:
        """
        Build a directed graph of citation relationships
        
        Returns:
            NetworkX DiGraph with citation relationships
        """
        session = self.storage.get_session()
        
        try:
            # Create directed graph
            G = nx.DiGraph()
            
            # Get all documents and citations
            from ..models import Document, Citation, Author
            
            documents = session.query(Document).all()
            citations = session.query(Citation).all()
            
            # Add document nodes
            for doc in documents:
                G.add_node(doc.id, 
                          title=doc.title,
                          authors=[a.name for a in doc.authors],
                          year=doc.publication_year,
                          journal=doc.journal)
            
            # Add citation edges
            for citation in citations:
                if citation.cited_document_id:  # Internal citation
                    G.add_edge(citation.citing_document_id, 
                              citation.cited_document_id,
                              citation_text=citation.citation_text)
            
            self.logger.info(f"Built citation network with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            return G
            
        finally:
            session.close()
    
    def get_most_cited_papers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most cited papers in the collection
        
        Args:
            limit: Number of papers to return
            
        Returns:
            List of papers sorted by citation count
        """
        session = self.storage.get_session()
        
        try:
            from ..models import Document, Citation
            
            # Count citations for each document
            citation_counts = (session.query(Citation.cited_document_id, 
                                           session.query(Citation)
                                           .filter(Citation.cited_document_id == Citation.cited_document_id)
                                           .count().label('count'))
                             .filter(Citation.cited_document_id.isnot(None))
                             .group_by(Citation.cited_document_id)
                             .order_by(session.query(Citation)
                                      .filter(Citation.cited_document_id == Citation.cited_document_id)
                                      .count().desc())
                             .limit(limit)
                             .all())
            
            # Get document details
            results = []
            for doc_id, count in citation_counts:
                doc = session.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    results.append({
                        'document': doc.to_dict(),
                        'citation_count': count
                    })
            
            return results
            
        finally:
            session.close()
    
    def get_most_citing_papers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get papers that cite the most other papers
        
        Args:
            limit: Number of papers to return
            
        Returns:
            List of papers sorted by number of citations made
        """
        session = self.storage.get_session()
        
        try:
            from ..models import Document, Citation
            
            # Count citations made by each document
            citing_counts = (session.query(Citation.citing_document_id,
                                         session.query(Citation)
                                         .filter(Citation.citing_document_id == Citation.citing_document_id)
                                         .count().label('count'))
                           .group_by(Citation.citing_document_id)
                           .order_by(session.query(Citation)
                                    .filter(Citation.citing_document_id == Citation.citing_document_id)
                                    .count().desc())
                           .limit(limit)
                           .all())
            
            # Get document details
            results = []
            for doc_id, count in citing_counts:
                doc = session.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    results.append({
                        'document': doc.to_dict(),
                        'citations_made': count
                    })
            
            return results
            
        finally:
            session.close()
    
    def analyze_citation_patterns(self) -> Dict[str, Any]:
        """
        Analyze citation patterns in the collection
        
        Returns:
            Dictionary with citation analysis results
        """
        G = self.build_citation_network()
        
        analysis = {
            'total_papers': G.number_of_nodes(),
            'total_citations': G.number_of_edges(),
            'average_citations_per_paper': G.number_of_edges() / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        }
        
        if G.number_of_nodes() > 0:
            # Calculate centrality measures
            try:
                in_degree_centrality = nx.in_degree_centrality(G)
                out_degree_centrality = nx.out_degree_centrality(G)
                pagerank = nx.pagerank(G)
                
                # Get top papers by different measures
                analysis.update({
                    'most_cited_by_in_degree': sorted(in_degree_centrality.items(), 
                                                     key=lambda x: x[1], reverse=True)[:5],
                    'most_citing_by_out_degree': sorted(out_degree_centrality.items(), 
                                                       key=lambda x: x[1], reverse=True)[:5],
                    'highest_pagerank': sorted(pagerank.items(), 
                                             key=lambda x: x[1], reverse=True)[:5],
                })
                
                # Network structure analysis
                if nx.is_weakly_connected(G):
                    analysis['is_connected'] = True
                    analysis['diameter'] = nx.diameter(G.to_undirected())
                else:
                    analysis['is_connected'] = False
                    analysis['connected_components'] = nx.number_weakly_connected_components(G)
                
            except Exception as e:
                self.logger.error(f"Error in network analysis: {str(e)}")
        
        return analysis
    
    def get_citation_timeline(self) -> Dict[str, Any]:
        """
        Analyze citation patterns over time
        
        Returns:
            Timeline analysis of citations
        """
        session = self.storage.get_session()
        
        try:
            from ..models import Document, Citation
            
            # Get citations with year information
            results = (session.query(Document.publication_year, 
                                    session.query(Citation)
                                    .filter(Citation.citing_document_id == Document.id)
                                    .count().label('citations_made'),
                                    session.query(Citation)
                                    .filter(Citation.cited_document_id == Document.id)
                                    .count().label('citations_received'))
                     .filter(Document.publication_year.isnot(None))
                     .group_by(Document.publication_year)
                     .order_by(Document.publication_year)
                     .all())
            
            timeline = {}
            for year, made, received in results:
                timeline[year] = {
                    'citations_made': made,
                    'citations_received': received,
                    'net_citations': received - made
                }
            
            return {
                'timeline': timeline,
                'total_years': len(timeline),
                'year_range': (min(timeline.keys()), max(timeline.keys())) if timeline else (None, None)
            }
            
        finally:
            session.close()
    
    def find_citation_clusters(self) -> List[Dict[str, Any]]:
        """
        Find clusters of highly interconnected papers
        
        Returns:
            List of citation clusters
        """
        G = self.build_citation_network()
        
        try:
            # Convert to undirected for community detection
            G_undirected = G.to_undirected()
            
            # Find communities using modularity-based clustering
            communities = nx.community.greedy_modularity_communities(G_undirected)
            
            clusters = []
            for i, community in enumerate(communities):
                if len(community) >= 3:  # Only include clusters with 3+ papers
                    cluster_docs = []
                    for node_id in community:
                        node_data = G.nodes[node_id]
                        cluster_docs.append({
                            'id': node_id,
                            'title': node_data.get('title', ''),
                            'authors': node_data.get('authors', []),
                            'year': node_data.get('year')
                        })
                    
                    clusters.append({
                        'cluster_id': i,
                        'size': len(community),
                        'documents': cluster_docs
                    })
            
            return sorted(clusters, key=lambda x: x['size'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding citation clusters: {str(e)}")
            return []