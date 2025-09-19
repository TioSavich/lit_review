# Literature Review Platform

A comprehensive platform for processing, storing, and querying large collections of academic PDFs with a focus on mathematics education research. This platform can handle approximately 3000 articles, extract structured content using docling, and provide powerful search and analysis capabilities.

## Features

- **PDF Processing**: Uses docling for advanced PDF parsing with proper handling of equations and images
- **Semantic Search**: Vector-based search using sentence transformers for finding conceptually similar papers
- **Citation Analysis**: Track citation networks and identify highly cited works
- **Co-authorship Analysis**: Discover collaboration patterns among researchers
- **Natural Language Queries**: Ask questions like "which articles discuss cognitively guided instruction?"
- **Web Interface**: User-friendly interface for searching and browsing the collection
- **Batch Processing**: Efficiently process thousands of PDF files

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the Database**
   ```bash
   python -m lit_review.cli init
   ```

3. **Process PDF Files**
   ```bash
   # Process a single PDF
   python -m lit_review.cli process /path/to/paper.pdf
   
   # Process a directory of PDFs
   python -m lit_review.cli process /path/to/pdf/directory
   
   # Process with maximum file limit
   python -m lit_review.cli process /path/to/pdf/directory --max-files 100
   ```

4. **Start the Web Interface**
   ```bash
   python -m lit_review.cli web
   ```
   
   Access the interface at http://localhost:5000

## Installation

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

### Step-by-Step Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd lit_review
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Additional Models (Optional)**
   ```bash
   # For better NLP processing
   python -m spacy download en_core_web_sm
   ```

5. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

## Configuration

The platform uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed:

```bash
# Database configuration
DATABASE_URL=sqlite:///lit_review.db

# Document storage paths
DOCUMENT_STORAGE_PATH=./documents
PROCESSED_STORAGE_PATH=./processed
VECTOR_DB_PATH=./vector_db

# Web interface settings
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=True

# Processing settings
BATCH_SIZE=10
MAX_WORKERS=4

# Model configurations
EMBEDDING_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm
```

## Usage Examples

### Processing Mathematics Education Papers

```bash
# Process a collection of 3000 mathematics education PDFs
python -m lit_review.cli process /path/to/math_education_papers/

# Check processing progress
python -m lit_review.cli stats
```

### Search Queries

Access the web interface to perform searches:

- **Text Search**: "cognitively guided instruction"
- **Author Search**: Papers by specific researchers
- **Concept Search**: "mathematical reasoning" or "problem solving"
- **Citation Analysis**: Find most cited papers in the collection

### API Usage

The platform provides a REST API for programmatic access:

```bash
# Search for papers
curl "http://localhost:5000/api/search?q=cognitively+guided+instruction&semantic=true"

# Get author profile
curl "http://localhost:5000/api/authors/John%20Smith"

# Get citation analysis
curl "http://localhost:5000/api/analysis/citations?type=most_cited"
```

## Architecture

```
lit_review/
├── models/          # Database models (Document, Author, Citation, etc.)
├── processors/      # PDF processing (docling, fallback processors)
├── storage/         # Data storage (SQL database, vector database)
├── analysis/        # Citation and co-authorship analysis
├── web/            # Flask web interface
├── utils/          # Utility functions and configuration
└── cli.py          # Command-line interface
```

### Key Components

1. **PDF Processing Pipeline**
   - Primary: Docling for advanced PDF parsing
   - Fallback: PyMuPDF/PyPDF2 for basic text extraction
   - Metadata extraction and structuring

2. **Storage System**
   - SQLite/PostgreSQL for structured data
   - ChromaDB for vector embeddings
   - File system for original and processed documents

3. **Analysis Engine**
   - Citation network analysis using NetworkX
   - Co-authorship pattern detection
   - Research community identification

4. **Search Engine**
   - Traditional keyword search
   - Semantic search using sentence transformers
   - Natural language query processing

## API Reference

### Search Endpoints

- `GET /api/search` - Search documents
- `GET /api/documents/{id}` - Get document details
- `GET /api/authors/{name}` - Get author profile

### Analysis Endpoints

- `GET /api/analysis/citations` - Citation analysis
- `GET /api/analysis/collaboration` - Co-authorship analysis
- `POST /api/query` - Natural language queries

### Utility Endpoints

- `GET /api/health` - Health check
- `GET /api/statistics` - Collection statistics

## Performance Considerations

- **Batch Processing**: Process PDFs in batches for memory efficiency
- **Vector Storage**: Uses efficient similarity search with FAISS
- **Database Indexing**: Optimized queries for large document collections
- **Memory Management**: Streaming processing for large files

## Mathematics Education Features

The platform includes specialized features for mathematics education research:

- **Concept Recognition**: Identifies key mathematics education concepts
- **Methodology Detection**: Recognizes research methodologies
- **Topic Clustering**: Groups papers by research themes
- **Terminology Extraction**: Mathematics-specific keyword extraction

## Troubleshooting

### Common Issues

1. **Docling Installation Problems**
   ```bash
   # Use fallback processor if docling isn't available
   python -m lit_review.cli process /path/to/files --no-docling
   ```

2. **Memory Issues with Large Collections**
   ```bash
   # Process in smaller batches
   python -m lit_review.cli process /path/to/files --max-files 100
   ```

3. **Database Errors**
   ```bash
   # Reinitialize database
   python -m lit_review.cli init
   ```

### Performance Optimization

- Use SSD storage for vector database
- Increase batch size for faster processing
- Consider PostgreSQL for large collections (>10,000 papers)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation
- Submit issues on the repository

---

**Note**: This platform is designed to handle large-scale literature reviews efficiently while maintaining the quality of extracted information through advanced PDF processing techniques.
