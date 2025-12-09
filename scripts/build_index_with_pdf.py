"""
Build unified index from both ITSM tickets AND PDF documents (PHASE 7).

This script creates a single searchable index containing:
- ITSM ticket resolutions (from CSV)
- PDF documentation (from PDF files)

Both are treated equally by the RAG pipeline.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_pipeline.ingestion import load_itsm_tickets_from_csv
from data_pipeline.anonymize import anonymize_tickets
from data_pipeline.build_indexes import IndexBuilder, convert_ticket_to_document
from data_pipeline.pdf_processor import process_pdf_to_documents
import structlog

logger = structlog.get_logger()


def main():
    """Build unified index from tickets and PDF documents."""
    
    print("="*70)
    print("PHASE 7: Building Unified Index (Tickets + PDF Documents)")
    print("="*70)
    
    # Configuration
    csv_path = "data/sample_itsm_tickets.csv"
    pdf_path = "Donanım Sorunlarını Giderme.pdf"
    index_dir = "indexes/"
    
    print(f"\nConfiguration:")
    print(f"  CSV file: {csv_path}")
    print(f"  PDF file: {pdf_path}")
    print(f"  Index directory: {index_dir}")
    print(f"  Anonymization: Enabled")
    
    try:
        # ============================================
        # Step 1: Load ITSM Tickets
        # ============================================
        print("\n" + "="*70)
        print("Step 1: Loading ITSM tickets from CSV...")
        print("="*70)
        
        tickets = load_itsm_tickets_from_csv(csv_path)
        print(f"Loaded {len(tickets)} tickets")
        
        # ============================================
        # Step 2: Anonymize Tickets
        # ============================================
        print("\n" + "="*70)
        print("Step 2: Anonymizing tickets...")
        print("="*70)
        
        tickets = anonymize_tickets(tickets)
        print(f"Anonymized {len(tickets)} tickets")
        
        # ============================================
        # Step 3: Convert Tickets to Documents
        # ============================================
        print("\n" + "="*70)
        print("Step 3: Converting tickets to documents...")
        print("="*70)
        
        ticket_docs = [convert_ticket_to_document(t) for t in tickets]
        print(f"Converted {len(ticket_docs)} ticket documents")
        
        # ============================================
        # Step 4: Load PDF Documents
        # ============================================
        print("\n" + "="*70)
        print("Step 4: Processing PDF document...")
        print("="*70)
        
        try:
            pdf_docs = process_pdf_to_documents(pdf_path)
            print(f"Extracted {len(pdf_docs)} pages from PDF")
        except FileNotFoundError:
            print(f"WARNING: PDF not found at {pdf_path}")
            print("Continuing with tickets only...")
            pdf_docs = []
        except ImportError as e:
            print(f"ERROR: {e}")
            print("Install pdfplumber: pip install pdfplumber")
            print("Continuing with tickets only...")
            pdf_docs = []
        
        # ============================================
        # Step 5: Combine All Documents
        # ============================================
        print("\n" + "="*70)
        print("Step 5: Combining all documents...")
        print("="*70)
        
        all_docs = ticket_docs + pdf_docs
        print(f"Total documents: {len(all_docs)}")
        print(f"  - Tickets: {len(ticket_docs)}")
        print(f"  - PDF pages: {len(pdf_docs)}")
        
        # ============================================
        # Step 6: Build Unified Index
        # ============================================
        print("\n" + "="*70)
        print("Step 6: Building unified search index...")
        print("="*70)
        
        index_builder = IndexBuilder(index_dir=index_dir)
        index_builder.build_hybrid_indexes(all_docs)
        
        print(f"\nIndex built successfully!")
        print(f"  Location: {index_dir}")
        print(f"  BM25 documents: {len(all_docs)}")
        print(f"  Embedding documents: {len(all_docs)}")
        
        # ============================================
        # Step 7: Quick Test
        # ============================================
        print("\n" + "="*70)
        print("Step 7: Testing retrieval...")
        print("="*70)
        
        # Test query
        test_query = "Donanım sorunu nasıl giderilir?"
        print(f"\nTest query: '{test_query}'")
        
        # Load and test
        bm25_retriever = index_builder.load_bm25_index()
        if bm25_retriever:
            results = bm25_retriever.search(test_query, top_k=3)
            print(f"\nTop 3 results:")
            for i, doc in enumerate(results, 1):
                doc_type = doc.get('doc_type', 'ticket')
                title = doc.get('title') or doc.get('short_description', '')
                score = doc.get('score', 0)
                print(f"  {i}. [{doc_type}] {title[:60]}... (score: {score:.3f})")
        
        print("\n" + "="*70)
        print("SUCCESS! Unified index ready for use!")
        print("="*70)
        print("\nNow the RAG system will answer from:")
        print("  - ITSM ticket resolutions")
        print("  - PDF documentation")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

