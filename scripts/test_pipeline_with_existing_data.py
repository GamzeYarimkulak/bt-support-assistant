"""
Test pipeline with existing data files.

This script:
1. Creates directory structure
2. Moves existing CSV/PDF files to raw/ directories (copies, doesn't move)
3. Runs ingestion pipelines
4. Builds indexes
5. Runs evaluation

Run this after activating conda environment:
conda activate bt-support
"""

import os
import sys
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.config import settings
except ImportError as e:
    print(f"ERROR: Cannot import settings. Make sure conda environment is activated:")
    print(f"  conda activate bt-support")
    print(f"Error: {e}")
    sys.exit(1)


def setup_directories():
    """Create directory structure."""
    print("=" * 70)
    print("STEP 1: Creating directory structure")
    print("=" * 70)
    
    base_dir = Path(settings.data_dir)
    
    dirs_to_create = [
        base_dir / "raw" / "tickets",
        base_dir / "raw" / "kb",
        base_dir / "processed",
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ {dir_path}")
    
    print()
    return True


def copy_existing_files():
    """Copy existing CSV/PDF files to raw directories."""
    print("=" * 70)
    print("STEP 2: Copying existing files to raw directories")
    print("=" * 70)
    
    base_dir = Path(settings.data_dir)
    raw_tickets = base_dir / "raw" / "tickets"
    raw_kb = base_dir / "raw" / "kb"
    
    # Find CSV files in data/ root
    csv_files = list(base_dir.glob("*.csv"))
    pdf_files = list(base_dir.glob("*.pdf"))
    
    print(f"Found {len(csv_files)} CSV file(s) in data/ root:")
    for csv_file in csv_files:
        if csv_file.parent == base_dir:  # Only files directly in data/
            dest = raw_tickets / csv_file.name
            if not dest.exists():
                shutil.copy2(csv_file, dest)
                print(f"  ✓ Copied: {csv_file.name} → raw/tickets/")
            else:
                print(f"  - Already exists: {csv_file.name}")
    
    print(f"\nFound {len(pdf_files)} PDF file(s) in data/ root:")
    for pdf_file in pdf_files:
        if pdf_file.parent == base_dir:  # Only files directly in data/
            dest = raw_kb / pdf_file.name
            if not dest.exists():
                shutil.copy2(pdf_file, dest)
                print(f"  ✓ Copied: {pdf_file.name} → raw/kb/")
            else:
                print(f"  - Already exists: {pdf_file.name}")
    
    print()
    return True


def run_ingestion():
    """Run ticket and KB ingestion."""
    print("=" * 70)
    print("STEP 3: Running ingestion pipelines")
    print("=" * 70)
    
    # Import here to avoid issues if modules not available
    try:
        from data_pipeline.ingest_tickets import ingest_tickets
        from data_pipeline.ingest_kb import ingest_kb
        
        print("\n3.1 Ticket Ingestion:")
        print("-" * 70)
        ticket_result = ingest_tickets(dry_run=False)
        print(f"✓ Processed {ticket_result['num_rows']} tickets")
        
        print("\n3.2 KB Ingestion:")
        print("-" * 70)
        kb_result = ingest_kb(dry_run=False, max_pages=None)  # Process all pages
        print(f"✓ Created {kb_result['num_chunks']} KB chunks")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_indexes():
    """Build indexes from processed data."""
    print("\n" + "=" * 70)
    print("STEP 4: Building indexes")
    print("=" * 70)
    
    try:
        from scripts.build_indexes import build_indexes
        
        result = build_indexes(dry_run=False, rebuild=True)
        print(f"✓ Indexed {result['num_documents']} documents")
        print(f"  - Tickets: {result['num_tickets']}")
        print(f"  - KB chunks: {result['num_kb_chunks']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during index build: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_evaluation():
    """Run retrieval evaluation."""
    print("\n" + "=" * 70)
    print("STEP 5: Running evaluation")
    print("=" * 70)
    
    try:
        from scripts.evaluate_retrieval import evaluate_retrieval
        
        result = evaluate_retrieval(n_queries=50, seed=42)  # Start with 50 queries
        
        print(f"\n✓ Evaluation Results:")
        print(f"  - Recall@5: {result['recall_at_5']:.4f}")
        print(f"  - nDCG@10: {result['ndcg_at_10']:.4f}")
        print(f"  - Avg Latency: {result['avg_latency_seconds']:.4f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test pipeline."""
    print("\n" + "=" * 70)
    print("TESTING PIPELINE WITH EXISTING DATA")
    print("=" * 70)
    print(f"Data directory: {settings.data_dir}")
    print()
    
    steps = [
        ("Directory Setup", setup_directories),
        ("File Copying", copy_existing_files),
        ("Ingestion", run_ingestion),
        ("Index Build", build_indexes),
        ("Evaluation", run_evaluation),
    ]
    
    results = {}
    
    for step_name, step_func in steps:
        try:
            success = step_func()
            results[step_name] = success
            if not success:
                print(f"\n⚠️  {step_name} failed. Stopping pipeline.")
                break
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Pipeline interrupted by user at: {step_name}")
            break
        except Exception as e:
            print(f"\n✗ Unexpected error in {step_name}: {e}")
            results[step_name] = False
            break
    
    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    
    for step_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{step_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All steps completed successfully!")
    else:
        print("\n⚠️  Some steps failed. Check errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

