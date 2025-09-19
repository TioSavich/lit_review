"""
Co-authorship network analysis tools
"""

import logging
from typing import Dict, List, Any, Tuple
import networkx as nx
from collections import defaultdict, Counter

from ..storage.document_storage import DocumentStorage


class CoAuthorshipAnalyzer:
    """
    Analyzes co-authorship networks and collaboration patterns
    """
    
    def __init__(self, document_storage: DocumentStorage):
        """
        Initialize co-authorship analyzer
        
        Args:
            document_storage: Document storage instance
        """
        self.storage = document_storage
        self.logger = logging.getLogger(__name__)
    
    def build_coauthorship_network(self) -> nx.Graph:
        """
        Build an undirected graph of co-authorship relationships
        
        Returns:
            NetworkX Graph with co-authorship relationships
        """
        session = self.storage.get_session()
        
        try:
            # Create undirected graph
            G = nx.Graph()
            
            # Get all documents with authors
            from ..models import Document, Author
            
            documents = session.query(Document).all()
            
            # Build co-authorship edges
            for doc in documents:
                authors = [a.name for a in doc.authors]
                
                # Add author nodes with attributes
                for author in authors:
                    if not G.has_node(author):
                        G.add_node(author, papers=[], total_papers=0)
                    
                    # Add this paper to author's list
                    G.nodes[author]['papers'].append({
                        'id': doc.id,
                        'title': doc.title,
                        'year': doc.publication_year
                    })
                    G.nodes[author]['total_papers'] += 1
                
                # Add co-authorship edges
                for i, author1 in enumerate(authors):
                    for author2 in authors[i+1:]:
                        if G.has_edge(author1, author2):
                            # Increment collaboration count
                            G[author1][author2]['weight'] += 1
                            G[author1][author2]['papers'].append({
                                'id': doc.id,
                                'title': doc.title,
                                'year': doc.publication_year
                            })
                        else:
                            # Create new collaboration edge
                            G.add_edge(author1, author2, 
                                     weight=1, 
                                     papers=[{
                                         'id': doc.id,
                                         'title': doc.title,
                                         'year': doc.publication_year
                                     }])
            
            self.logger.info(f"Built co-authorship network with {G.number_of_nodes()} authors and {G.number_of_edges()} collaborations")
            return G
            
        finally:
            session.close()
    
    def get_most_collaborative_authors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get authors with the most collaborations
        
        Args:
            limit: Number of authors to return
            
        Returns:
            List of authors sorted by collaboration count
        """
        G = self.build_coauthorship_network()
        
        # Calculate collaboration metrics for each author
        authors_data = []
        
        for author in G.nodes():
            degree = G.degree(author)  # Number of unique collaborators
            total_papers = G.nodes[author]['total_papers']
            
            # Calculate weighted degree (total collaboration strength)
            weighted_degree = sum(G[author][neighbor]['weight'] for neighbor in G.neighbors(author))
            
            # Get list of collaborators with collaboration counts
            collaborators = []
            for neighbor in G.neighbors(author):
                collaborators.append({
                    'name': neighbor,
                    'collaboration_count': G[author][neighbor]['weight'],
                    'shared_papers': G[author][neighbor]['papers']
                })
            
            authors_data.append({
                'name': author,
                'total_papers': total_papers,
                'unique_collaborators': degree,
                'total_collaborations': weighted_degree,
                'collaboration_rate': degree / total_papers if total_papers > 0 else 0,
                'collaborators': sorted(collaborators, key=lambda x: x['collaboration_count'], reverse=True)
            })
        
        # Sort by number of unique collaborators
        return sorted(authors_data, key=lambda x: x['unique_collaborators'], reverse=True)[:limit]
    
    def get_strongest_collaborations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the strongest collaboration pairs (most papers together)
        
        Args:
            limit: Number of collaboration pairs to return
            
        Returns:
            List of collaboration pairs sorted by strength
        """
        G = self.build_coauthorship_network()
        
        # Get all edges with their weights
        collaborations = []
        for author1, author2, data in G.edges(data=True):
            collaborations.append({
                'authors': [author1, author2],
                'collaboration_count': data['weight'],
                'shared_papers': data['papers']
            })
        
        # Sort by collaboration strength
        return sorted(collaborations, key=lambda x: x['collaboration_count'], reverse=True)[:limit]
    
    def find_research_communities(self) -> List[Dict[str, Any]]:
        """
        Find research communities based on co-authorship patterns
        
        Returns:
            List of research communities
        """
        G = self.build_coauthorship_network()
        
        try:
            # Find communities using modularity-based clustering
            communities = nx.community.greedy_modularity_communities(G)
            
            research_communities = []
            for i, community in enumerate(communities):
                if len(community) >= 3:  # Only include communities with 3+ authors
                    
                    # Get community statistics
                    subgraph = G.subgraph(community)
                    total_papers = sum(G.nodes[author]['total_papers'] for author in community)
                    internal_edges = subgraph.number_of_edges()
                    
                    # Get most active authors in community
                    authors_in_community = []
                    for author in community:
                        authors_in_community.append({
                            'name': author,
                            'papers_count': G.nodes[author]['total_papers'],
                            'collaborations_in_community': subgraph.degree(author)
                        })
                    
                    # Sort authors by activity
                    authors_in_community.sort(key=lambda x: x['papers_count'], reverse=True)
                    
                    research_communities.append({
                        'community_id': i,
                        'size': len(community),
                        'total_papers': total_papers,
                        'internal_collaborations': internal_edges,
                        'density': nx.density(subgraph),
                        'authors': authors_in_community,
                        'key_authors': authors_in_community[:5]  # Top 5 most active
                    })
            
            return sorted(research_communities, key=lambda x: x['size'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding research communities: {str(e)}")
            return []
    
    def analyze_author_centrality(self) -> Dict[str, Any]:
        """
        Analyze author centrality in the co-authorship network
        
        Returns:
            Dictionary with centrality analysis results
        """
        G = self.build_coauthorship_network()
        
        if G.number_of_nodes() == 0:
            return {}
        
        try:
            # Calculate different centrality measures
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            closeness_centrality = nx.closeness_centrality(G)
            eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=1000)
            
            # Get top authors by each measure
            analysis = {
                'total_authors': G.number_of_nodes(),
                'total_collaborations': G.number_of_edges(),
                'average_collaborators_per_author': 2 * G.number_of_edges() / G.number_of_nodes(),
                
                'top_by_degree_centrality': sorted(degree_centrality.items(), 
                                                  key=lambda x: x[1], reverse=True)[:10],
                'top_by_betweenness_centrality': sorted(betweenness_centrality.items(), 
                                                       key=lambda x: x[1], reverse=True)[:10],
                'top_by_closeness_centrality': sorted(closeness_centrality.items(), 
                                                     key=lambda x: x[1], reverse=True)[:10],
                'top_by_eigenvector_centrality': sorted(eigenvector_centrality.items(), 
                                                       key=lambda x: x[1], reverse=True)[:10],
            }
            
            # Network structure analysis
            if nx.is_connected(G):
                analysis['is_connected'] = True
                analysis['diameter'] = nx.diameter(G)
                analysis['average_path_length'] = nx.average_shortest_path_length(G)
            else:
                analysis['is_connected'] = False
                analysis['connected_components'] = nx.number_connected_components(G)
                
                # Analyze largest component
                largest_cc = max(nx.connected_components(G), key=len)
                largest_subgraph = G.subgraph(largest_cc)
                analysis['largest_component_size'] = len(largest_cc)
                analysis['largest_component_diameter'] = nx.diameter(largest_subgraph)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in centrality analysis: {str(e)}")
            return {}
    
    def get_collaboration_timeline(self) -> Dict[str, Any]:
        """
        Analyze collaboration patterns over time
        
        Returns:
            Timeline analysis of collaborations
        """
        session = self.storage.get_session()
        
        try:
            from ..models import Document
            
            # Get documents with year and author information
            documents = session.query(Document).filter(
                Document.publication_year.isnot(None)
            ).all()
            
            timeline = defaultdict(lambda: {
                'total_papers': 0,
                'collaborative_papers': 0,
                'solo_papers': 0,
                'unique_authors': set(),
                'unique_collaborations': set()
            })
            
            for doc in documents:
                year = doc.publication_year
                authors = [a.name for a in doc.authors]
                
                timeline[year]['total_papers'] += 1
                timeline[year]['unique_authors'].update(authors)
                
                if len(authors) > 1:
                    timeline[year]['collaborative_papers'] += 1
                    # Add all collaboration pairs
                    for i, author1 in enumerate(authors):
                        for author2 in authors[i+1:]:
                            timeline[year]['unique_collaborations'].add(
                                tuple(sorted([author1, author2]))
                            )
                else:
                    timeline[year]['solo_papers'] += 1
            
            # Convert sets to counts and prepare final timeline
            final_timeline = {}
            for year, data in timeline.items():
                final_timeline[year] = {
                    'total_papers': data['total_papers'],
                    'collaborative_papers': data['collaborative_papers'],
                    'solo_papers': data['solo_papers'],
                    'unique_authors': len(data['unique_authors']),
                    'unique_collaborations': len(data['unique_collaborations']),
                    'collaboration_rate': data['collaborative_papers'] / data['total_papers'] if data['total_papers'] > 0 else 0
                }
            
            return {
                'timeline': final_timeline,
                'total_years': len(final_timeline),
                'year_range': (min(final_timeline.keys()), max(final_timeline.keys())) if final_timeline else (None, None)
            }
            
        finally:
            session.close()
    
    def get_author_profile(self, author_name: str) -> Dict[str, Any]:
        """
        Get detailed profile for a specific author
        
        Args:
            author_name: Name of the author
            
        Returns:
            Author profile with collaboration details
        """
        G = self.build_coauthorship_network()
        
        # Find author (case-insensitive partial match)
        matching_authors = [name for name in G.nodes() if author_name.lower() in name.lower()]
        
        if not matching_authors:
            return {'error': f'Author "{author_name}" not found'}
        
        # Use exact match if available, otherwise use first match
        if author_name in matching_authors:
            author = author_name
        else:
            author = matching_authors[0]
        
        if author not in G.nodes():
            return {'error': f'Author "{author}" not found in network'}
        
        # Get author's papers
        papers = G.nodes[author]['papers']
        
        # Get collaborators
        collaborators = []
        for neighbor in G.neighbors(author):
            collaboration_data = G[author][neighbor]
            collaborators.append({
                'name': neighbor,
                'collaboration_count': collaboration_data['weight'],
                'shared_papers': collaboration_data['papers']
            })
        
        collaborators.sort(key=lambda x: x['collaboration_count'], reverse=True)
        
        # Calculate metrics
        total_papers = len(papers)
        collaborative_papers = sum(1 for paper in papers if any(
            collab['shared_papers'] for collab in collaborators 
            if any(p['id'] == paper['id'] for p in collab['shared_papers'])
        ))
        
        return {
            'name': author,
            'total_papers': total_papers,
            'collaborative_papers': collaborative_papers,
            'solo_papers': total_papers - collaborative_papers,
            'unique_collaborators': len(collaborators),
            'collaboration_rate': collaborative_papers / total_papers if total_papers > 0 else 0,
            'papers': sorted(papers, key=lambda x: x.get('year', 0), reverse=True),
            'collaborators': collaborators,
            'top_collaborators': collaborators[:10],
            'years_active': sorted(list(set(p.get('year') for p in papers if p.get('year')))),
        }