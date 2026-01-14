"""
KB (Knowledge Base) ingestion pipeline: PDF → Chunked JSONL.

Reads PDF files from data/raw/kb/ and converts them to chunked JSONL format
at data/processed/kb_chunks.jsonl.

Each chunk is approximately 400 tokens and contains:
- id: str (unique chunk ID)
- text: str (chunk text)
- source_pdf: str (source filename)
- page: int (page number)
- chunk_index: int (chunk index within page)
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

logger = structlog.get_logger()

# Try to import PDF libraries
try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pypdf_not_installed",
                  message="pypdf not installed. Install with: pip install pypdf")


def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text from PDF file, page by page.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of dictionaries with 'page' and 'text' keys
    """
    if not PDF_AVAILABLE:
        raise ImportError("pypdf not installed. Install with: pip install pypdf")
    
    pages = []
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                pages.append({
                    "page": page_num,
                    "text": text
                })
    
    except Exception as e:
        logger.error("pdf_extraction_failed",
                    file=str(pdf_path),
                    error=str(e))
        raise
    
    return pages


def is_turkish_troubleshooting_doc(pdf_name: str) -> bool:
    """
    Check if PDF is a Turkish troubleshooting document.
    
    Args:
        pdf_name: PDF filename
        
    Returns:
        True if it's a Turkish troubleshooting document
    """
    pdf_lower = pdf_name.lower()
    turkish_troubleshooting_keywords = [
        "sorun_giderme",
        "sorun giderme",
        "troubleshooting",
        "çözüm",
        "kilavuz",
        "kılavuz"
    ]
    return any(keyword in pdf_lower for keyword in turkish_troubleshooting_keywords)


def is_itsm_document(pdf_name: str) -> bool:
    """
    Check if PDF is an ITSM document.
    
    Args:
        pdf_name: PDF filename
        
    Returns:
        True if it's an ITSM document
    """
    pdf_lower = pdf_name.lower()
    itsm_keywords = [
        "itsm",
        "incident",
        "service desk",
        "service management",
        "itil",
        "process document"
    ]
    return any(keyword in pdf_lower for keyword in itsm_keywords)


def is_itsm_conceptual_content(text: str) -> bool:
    """
    Check if text contains ITSM conceptual content (definitions, classifications, prioritization, decision support).
    
    Args:
        text: Text chunk to check
        
    Returns:
        True if content is conceptual ITSM content
    """
    text_lower = text.lower()
    
    # Keywords indicating conceptual content
    conceptual_keywords = [
        # Definitions
        "tanım", "definition", "nedir", "what is", "kavram", "concept",
        # Classification
        "sınıflandırma", "classification", "kategori", "category", "tip", "type",
        # Prioritization
        "öncelik", "priority", "önceliklendirme", "prioritization", "öncelik seviyesi",
        # Decision support
        "karar", "decision", "destek", "support", "değerlendirme", "evaluation",
        "kriter", "criteria", "ölçüt", "metric"
    ]
    
    # Check if text contains conceptual keywords
    conceptual_count = sum(1 for keyword in conceptual_keywords if keyword in text_lower)
    
    # If multiple conceptual keywords found, it's likely conceptual content
    return conceptual_count >= 2


def should_exclude_content(text: str) -> bool:
    """
    Check if content should be excluded based on filtering rules.
    
    Excludes:
    - Internal role definitions
    - Product names and specific product details
    - Detailed process flows
    - Training/educational content
    - Hardware theory
    - Academic content
    
    Args:
        text: Text chunk to check
        
    Returns:
        True if content should be excluded
    """
    text_lower = text.lower()
    
    # Exclusion patterns
    exclusion_patterns = [
        # Internal roles
        r"\b(rol|role|sorumluluk|responsibility|görev|duty)\s+(tanım|definition|açıklama)",
        r"\b(manager|yönetici|analyst|analist|technician|teknisyen)\s+(rol|role)",
        
        # Product names and specific products
        r"\b(product|ürün)\s+(isim|name|adı)",
        r"\b(service|servis)\s+(now|desk|management)",
        r"\b(version|versiyon)\s+\d+",
        
        # Detailed process flows
        r"(süreç\s+akışı|process\s+flow|workflow)",
        r"(adım\s+adım\s+süreç|step\s+by\s+step\s+process)",
        r"(akış\s+şeması|flow\s+chart|diagram)",
        
        # Training/educational content
        r"\b(eğitim|training|education|öğretim)\s+(kitabı|book|materyal|material)",
        r"(eğitim\s+programı|training\s+program)",
        r"(kurs|course)\s+(içeriği|content)",
        
        # Hardware theory
        r"(donanım|hardware)\s+(teorisi|theory|teorik)",
        r"(fiziksel|physical)\s+(bileşen|component|yapı|structure)",
        
        # Academic content
        r"\b(akademik|academic|teorik|theoretical)\s+(çalışma|study|araştırma|research)",
        r"(literatür|literature)\s+(taraması|review)",
        r"(referans|reference)\s+(listesi|list)"
    ]
    
    # Check for exclusion patterns
    for pattern in exclusion_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Additional exclusion keywords (if they appear frequently)
    exclusion_keywords = [
        "firma içi", "internal", "proprietary", "özel", "confidential",
        "workflow diagram", "process diagram", "flowchart"
    ]
    
    exclusion_keyword_count = sum(1 for keyword in exclusion_keywords if keyword in text_lower)
    if exclusion_keyword_count >= 2:
        return True
    
    return False


def is_actionable_content(text: str) -> bool:
    """
    Check if content contains actionable steps for end users.
    
    Args:
        text: Text chunk to check
        
    Returns:
        True if content contains actionable steps
    """
    text_lower = text.lower()
    
    # Actionable content indicators
    actionable_patterns = [
        r"(adım\s+\d+|step\s+\d+)",
        r"(yapılacaklar|to\s+do|actions)",
        r"(çözüm|solution|fix|düzeltme)",
        r"(nasıl|how\s+to)",
        r"(kontrol\s+et|check|verify)",
        r"(ayarla|configure|set)",
        r"(yeniden\s+başlat|restart|reboot)",
        r"(test\s+et|test)",
        r"(kurulum|install|setup)",
        r"(güncelle|update|upgrade)"
    ]
    
    # Check for actionable patterns
    for pattern in actionable_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Check for numbered lists or bullet points (often indicate steps)
    if re.search(r"^\s*[\d•\-\*]\s+", text_lower, re.MULTILINE):
        return True
    
    return False


def should_include_chunk(text: str, pdf_name: str) -> Tuple[bool, str]:
    """
    Determine if a chunk should be included in KB based on filtering rules.
    
    Rules:
    1. Turkish troubleshooting docs: Include all actionable content, prioritize heavily
    2. ITSM docs: Only include conceptual content (definitions, classifications, prioritization, decision support)
    3. Exclude: Internal roles, product names, detailed process flows, training content, hardware theory, academic content
    
    Args:
        text: Text chunk content
        pdf_name: Source PDF filename
        
    Returns:
        Tuple of (should_include: bool, reason: str)
    """
    # Always exclude if content matches exclusion patterns
    if should_exclude_content(text):
        return False, "excluded_by_rules"
    
    # Turkish troubleshooting documents: Include all actionable content (priority source)
    if is_turkish_troubleshooting_doc(pdf_name):
        if is_actionable_content(text):
            return True, "turkish_troubleshooting_actionable"
        # Also include other useful troubleshooting content
        if len(text.strip()) > 50:  # Non-empty meaningful content
            return True, "turkish_troubleshooting_content"
        return False, "turkish_troubleshooting_empty"
    
    # ITSM documents: Only include conceptual content (definitions, classifications, prioritization, decision support)
    if is_itsm_document(pdf_name):
        if is_itsm_conceptual_content(text):
            return True, "itsm_conceptual"
        # Exclude non-conceptual ITSM content
        return False, "itsm_non_conceptual"
    
    # For other documents, be more selective
    # Include if it's actionable or conceptual
    if is_actionable_content(text):
        return True, "actionable_content"
    
    if is_itsm_conceptual_content(text):
        return True, "conceptual_content"
    
    # Default: exclude if doesn't match criteria
    return False, "no_match"


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """
    Split text into chunks of approximately chunk_size tokens.
    
    Uses simple word-based chunking (approximates tokens as words).
    
    Args:
        text: Input text
        chunk_size: Target chunk size in tokens (approximate)
        overlap: Overlap between chunks in tokens
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    # Simple word-based splitting (approximates tokens)
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        
        # Move start forward with overlap
        start = end - overlap
        if start >= len(words):
            break
    
    return chunks


def process_pdf(
    pdf_path: Path,
    chunk_size: int = 400,
    max_pages: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Process a single PDF file into chunks.
    
    Args:
        pdf_path: Path to PDF file
        chunk_size: Target chunk size in tokens
        max_pages: Maximum number of pages to process (None = all)
        
    Returns:
        List of chunk dictionaries
    """
    print(f"  Processing: {pdf_path.name}")
    
    # Extract text
    pages = extract_text_from_pdf(pdf_path)
    
    if max_pages:
        pages = pages[:max_pages]
        print(f"    Limited to {max_pages} pages")
    
    print(f"    Extracted {len(pages)} pages")
    
    # Chunk each page
    all_chunks = []
    chunk_counter = 0
    excluded_counter = 0
    inclusion_reasons = {}
    
    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]
        
        if not text or not text.strip():
            continue
        
        chunks = chunk_text(text, chunk_size=chunk_size)
        
        if not chunks:
            # If no chunks created (empty text), skip this page
            continue
        
        for chunk_idx, chunk_text_content in enumerate(chunks):
            # Apply filtering rules
            should_include, reason = should_include_chunk(chunk_text_content, pdf_path.name)
            
            if not should_include:
                excluded_counter += 1
                continue
            
            # Track inclusion reasons for statistics
            inclusion_reasons[reason] = inclusion_reasons.get(reason, 0) + 1
            
            chunk_id = f"{pdf_path.stem}_p{page_num}_c{chunk_idx}"
            
            chunk = {
                "id": chunk_id,
                "text": chunk_text_content,
                "source_pdf": pdf_path.name,
                "page": page_num,
                "chunk_index": chunk_idx,
                "inclusion_reason": reason  # Track why chunk was included
            }
            
            all_chunks.append(chunk)
            chunk_counter += 1
    
    print(f"    Created {chunk_counter} chunks (excluded {excluded_counter} chunks)")
    if inclusion_reasons:
        print(f"    Inclusion reasons: {inclusion_reasons}")
    
    return all_chunks


def ingest_kb(
    input_dir: Optional[str] = None,
    output_file: Optional[str] = None,
    dry_run: bool = False,
    max_pages: Optional[int] = None,
    chunk_size: int = 400
) -> Dict[str, Any]:
    """
    Ingest KB PDF files and convert to chunked JSONL.
    
    Args:
        input_dir: Directory containing PDF files (default: data/raw/kb/)
        output_file: Output JSONL file path (default: data/processed/kb_chunks.jsonl)
        dry_run: If True, only analyze without writing
        max_pages: Maximum pages per PDF (for testing)
        chunk_size: Target chunk size in tokens
        
    Returns:
        Dictionary with ingestion statistics
    """
    if not PDF_AVAILABLE:
        raise ImportError("pypdf not installed. Install with: pip install pypdf")
    
    if input_dir is None:
        input_dir = os.path.join(settings.data_dir, "raw", "kb")
    
    if output_file is None:
        output_file = os.path.join(settings.data_dir, "processed", "kb_chunks.jsonl")
    
    input_path = Path(input_dir)
    output_path = Path(output_file)
    
    print("=" * 70)
    print("KB INGESTION PIPELINE")
    print("=" * 70)
    print(f"Input directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Mode: {'DRY RUN' if dry_run else 'PROCESS'}")
    print(f"Chunk size: {chunk_size} tokens (approximate)")
    if max_pages:
        print(f"Max pages per PDF: {max_pages}")
    print()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Find PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {input_dir}")
    
    print(f"Found {len(pdf_files)} PDF file(s):")
    for f in pdf_files:
        print(f"  - {f.name}")
    print()
    
    all_chunks = []
    
    for pdf_file in pdf_files:
        try:
            chunks = process_pdf(pdf_file, chunk_size=chunk_size, max_pages=max_pages)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error("pdf_processing_failed",
                        file=pdf_file.name,
                        error=str(e))
            print(f"  ✗ Error processing {pdf_file.name}: {e}")
            continue
    
    if not all_chunks:
        raise ValueError("No chunks created from any PDF files")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Total PDFs processed: {len(pdf_files)}")
    
    # Calculate average chunk size
    if all_chunks:
        avg_chunk_size = sum(len(c["text"].split()) for c in all_chunks) / len(all_chunks)
        print(f"Average chunk size: {avg_chunk_size:.1f} words (approximate tokens)")
        
        # Show inclusion reason statistics
        inclusion_stats = {}
        for chunk in all_chunks:
            reason = chunk.get("inclusion_reason", "unknown")
            inclusion_stats[reason] = inclusion_stats.get(reason, 0) + 1
        
        if inclusion_stats:
            print("\nInclusion statistics:")
            for reason, count in sorted(inclusion_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count} chunks")
    
    if dry_run:
        print("\n[DRY RUN] Would write JSONL file (not writing)")
        print(f"  Output: {output_path}")
        print(f"  Estimated size: ~{len(all_chunks) * 200 / 1024:.1f} KB")
    else:
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        file_size = output_path.stat().st_size / 1024
        print(f"\n✓ JSONL file written: {output_path}")
        print(f"  File size: {file_size:.2f} KB")
    
    return {
        "num_chunks": len(all_chunks),
        "num_pdfs": len(pdf_files),
        "output_file": str(output_path),
        "avg_chunk_size": avg_chunk_size,
        "dry_run": dry_run
    }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest KB PDF files and convert to chunked JSONL"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Input directory (default: data/raw/kb/)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSONL file (default: data/processed/kb_chunks.jsonl)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze without writing output file"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum pages per PDF (for testing)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=400,
        help="Target chunk size in tokens (default: 400)"
    )
    
    args = parser.parse_args()
    
    try:
        result = ingest_kb(
            input_dir=args.input_dir,
            output_file=args.output,
            dry_run=args.dry_run,
            max_pages=args.max_pages,
            chunk_size=args.chunk_size
        )
        
        print("\n✓ KB ingestion completed successfully")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

