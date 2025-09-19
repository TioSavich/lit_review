#!/usr/bin/env python3
"""
Test script to verify the literature review platform setup
"""

import sys
import os
from pathlib import Path

def test_project_structure():
    """Test that all required directories and files exist"""
    print("Testing project structure...")
    
    required_dirs = [
        'lit_review',
        'lit_review/models',
        'lit_review/processors', 
        'lit_review/storage',
        'lit_review/web',
        'lit_review/analysis',
        'lit_review/utils',
        'lit_review/web/templates'
    ]
    
    required_files = [
        'requirements.txt',
        'setup.py',
        'README.md',
        'lit_review/__init__.py',
        'lit_review/cli.py',
        'lit_review/web/app.py',
        'lit_review/web/templates/index.html'
    ]
    
    all_good = True
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✓ Directory exists: {directory}")
        else:
            print(f"✗ Missing directory: {directory}")
            all_good = False
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ File exists: {file_path}")
        else:
            print(f"✗ Missing file: {file_path}")
            all_good = False
    
    return all_good

def test_configuration():
    """Test configuration files"""
    print("\nTesting configuration...")
    
    # Check if .env.example exists
    if os.path.exists('.env.example'):
        print("✓ Configuration template exists")
        with open('.env.example', 'r') as f:
            content = f.read()
            required_configs = [
                'DATABASE_URL',
                'DOCUMENT_STORAGE_PATH',
                'VECTOR_DB_PATH',
                'FLASK_HOST',
                'FLASK_PORT'
            ]
            
            for config in required_configs:
                if config in content:
                    print(f"  ✓ {config} configured")
                else:
                    print(f"  ✗ {config} missing")
    else:
        print("✗ .env.example not found")

def test_requirements():
    """Test requirements.txt"""
    print("\nTesting requirements...")
    
    if os.path.exists('requirements.txt'):
        print("✓ requirements.txt exists")
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            key_packages = [
                'docling',
                'flask',
                'sqlalchemy',
                'sentence-transformers',
                'chromadb',
                'pandas',
                'networkx'
            ]
            
            for package in key_packages:
                if package in requirements.lower():
                    print(f"  ✓ {package} listed")
                else:
                    print(f"  ✗ {package} missing")
    else:
        print("✗ requirements.txt not found")

def show_next_steps():
    """Show next steps for setup"""
    print("\n" + "="*50)
    print("SETUP INSTRUCTIONS")
    print("="*50)
    print()
    print("1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    print("2. Copy configuration:")
    print("   cp .env.example .env")
    print()
    print("3. Initialize database:")
    print("   python -m lit_review.cli init")
    print()
    print("4. Process PDF files:")
    print("   python -m lit_review.cli process /path/to/pdfs/")
    print()
    print("5. Start web interface:")
    print("   python -m lit_review.cli web")
    print()
    print("6. For batch processing:")
    print("   python batch_process.py")
    print()
    print("="*50)
    print("EXAMPLE USAGE")
    print("="*50)
    print()
    print("To process 3000 mathematics education PDFs:")
    print("1. Place PDFs in a directory (e.g., ./math_education_papers/)")
    print("2. Run: python -m lit_review.cli process ./math_education_papers/")
    print("3. Access web interface at http://localhost:5000")
    print("4. Search for 'cognitively guided instruction' or other topics")
    print()
    print("The platform supports:")
    print("- Semantic search across all documents")
    print("- Citation network analysis")
    print("- Co-authorship pattern detection")
    print("- Natural language queries")
    print("- Mathematics education specific keyword extraction")

def main():
    """Run all tests"""
    print("Literature Review Platform - Setup Test")
    print("="*50)
    
    structure_ok = test_project_structure()
    test_configuration()
    test_requirements()
    
    if structure_ok:
        print("\n✓ Project structure looks good!")
        show_next_steps()
    else:
        print("\n✗ Some files are missing. Please check the project setup.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())