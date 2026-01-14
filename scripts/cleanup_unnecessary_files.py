"""
Cleanup unnecessary duplicate files.

Removes:
1. Duplicate CSV/PDF files in data/ root (already in data/raw/)
2. Old/obsolete scripts
3. Old documentation files
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def cleanup_duplicate_data_files(dry_run: bool = False):
    """Remove duplicate files from data/ root (already in raw/)."""
    print("=" * 70)
    print("CLEANUP: Duplicate Data Files")
    print("=" * 70)
    
    base_dir = Path(settings.data_dir)
    
    # Files to remove (already in raw/)
    files_to_remove = [
        base_dir / "aa_dataset-tickets-multi-lang-5-2-50-version.csv",
        base_dir / "sample_itsm_tickets.csv",
        base_dir / "ticket_helpdesk_labeled_multi_languages_english_spain_french_german.csv",
        base_dir / "WA_Fn-UseC_-IT-Help-Desk.csv",
        base_dir / "IncidentManagementProcessDocument_v02.pdf",
        base_dir / "it-incident-management-ebook.pdf",
        base_dir / "IT-Service-Desk-A-Complete-Guide-Whitepaper.pdf",
        base_dir / "ITSM-Incident-Process-Guide.pdf",
    ]
    
    removed = []
    not_found = []
    
    for file_path in files_to_remove:
        if file_path.exists():
            if dry_run:
                print(f"[DRY RUN] Would remove: {file_path.name}")
            else:
                try:
                    file_path.unlink()
                    print(f"✓ Removed: {file_path.name}")
                    removed.append(str(file_path))
                except Exception as e:
                    print(f"✗ Error removing {file_path.name}: {e}")
        else:
            not_found.append(str(file_path))
            print(f"- Not found: {file_path.name} (already removed or doesn't exist)")
    
    print(f"\nSummary: {len(removed)} files removed, {len(not_found)} not found")
    return removed


def cleanup_old_scripts(dry_run: bool = False):
    """Remove old/obsolete scripts."""
    print("\n" + "=" * 70)
    print("CLEANUP: Old Scripts")
    print("=" * 70)
    
    scripts_dir = Path("scripts")
    
    # Old scripts to remove (replaced by new ones)
    old_scripts = [
        scripts_dir / "build_sample_index.py",  # Replaced by build_indexes.py
        scripts_dir / "build_index_with_pdf.py",  # Replaced by build_indexes.py
        # build_and_test_index.py - keep it, might still be useful
    ]
    
    removed = []
    not_found = []
    
    for script_path in old_scripts:
        if script_path.exists():
            if dry_run:
                print(f"[DRY RUN] Would remove: {script_path.name}")
            else:
                try:
                    script_path.unlink()
                    print(f"✓ Removed: {script_path.name}")
                    removed.append(str(script_path))
                except Exception as e:
                    print(f"✗ Error removing {script_path.name}: {e}")
        else:
            not_found.append(str(script_path))
            print(f"- Not found: {script_path.name}")
    
    print(f"\nSummary: {len(removed)} scripts removed, {len(not_found)} not found")
    return removed


def cleanup_old_docs(dry_run: bool = False):
    """Remove old documentation files."""
    print("\n" + "=" * 70)
    print("CLEANUP: Old Documentation")
    print("=" * 70)
    
    # Old docs to remove
    old_docs = [
        Path("TEMIZLENEN_DOSYALAR.md"),  # Old cleanup list
    ]
    
    removed = []
    not_found = []
    
    for doc_path in old_docs:
        if doc_path.exists():
            if dry_run:
                print(f"[DRY RUN] Would remove: {doc_path.name}")
            else:
                try:
                    doc_path.unlink()
                    print(f"✓ Removed: {doc_path.name}")
                    removed.append(str(doc_path))
                except Exception as e:
                    print(f"✗ Error removing {doc_path.name}: {e}")
        else:
            not_found.append(str(doc_path))
            print(f"- Not found: {doc_path.name}")
    
    print(f"\nSummary: {len(removed)} docs removed, {len(not_found)} not found")
    return removed


def main():
    """Main cleanup function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cleanup unnecessary duplicate files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without actually removing"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("CLEANUP UNNECESSARY FILES")
    print("=" * 70)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'REMOVE'}")
    print()
    
    all_removed = []
    
    # Cleanup duplicate data files
    removed_data = cleanup_duplicate_data_files(dry_run=args.dry_run)
    all_removed.extend(removed_data)
    
    # Cleanup old scripts
    removed_scripts = cleanup_old_scripts(dry_run=args.dry_run)
    all_removed.extend(removed_scripts)
    
    # Cleanup old docs
    removed_docs = cleanup_old_docs(dry_run=args.dry_run)
    all_removed.extend(removed_docs)
    
    # Summary
    print("\n" + "=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"Total files removed: {len(all_removed)}")
    
    if all_removed:
        print("\nRemoved files:")
        for f in all_removed:
            print(f"  - {f}")
    
    if args.dry_run:
        print("\n[DRY RUN] No files were actually removed.")
        print("Run without --dry-run to actually remove files.")
    else:
        print("\n✓ Cleanup completed!")


if __name__ == "__main__":
    main()








