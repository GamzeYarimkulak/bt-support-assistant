"""
Initialize data directory structure (raw/processed standard).

This script creates the standard data directory structure:
- data/raw/tickets/
- data/raw/kb/
- data/processed/

It does NOT move existing files - user should move them manually.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def init_data_dirs(dry_run: bool = False) -> dict:
    """
    Initialize data directory structure.
    
    Args:
        dry_run: If True, only report what would be created without creating
        
    Returns:
        Dictionary with created directories and status
    """
    base_dir = Path(settings.data_dir)
    
    dirs_to_create = {
        "raw_tickets": base_dir / "raw" / "tickets",
        "raw_kb": base_dir / "raw" / "kb",
        "processed": base_dir / "processed",
    }
    
    created = []
    existing = []
    errors = []
    
    print("=" * 70)
    print("DATA DIRECTORY INITIALIZATION")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Mode: {'DRY RUN' if dry_run else 'CREATE'}")
    print()
    
    for name, dir_path in dirs_to_create.items():
        if dir_path.exists():
            print(f"✓ {name}: {dir_path} (already exists)")
            existing.append(str(dir_path))
        else:
            if dry_run:
                print(f"[DRY RUN] Would create: {dir_path}")
            else:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"✓ Created: {dir_path}")
                    created.append(str(dir_path))
                except Exception as e:
                    print(f"✗ Error creating {dir_path}: {e}")
                    errors.append(str(dir_path))
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Created: {len(created)}")
    print(f"Already existed: {len(existing)}")
    print(f"Errors: {len(errors)}")
    
    if created:
        print("\nCreated directories:")
        for d in created:
            print(f"  - {d}")
    
    if existing:
        print("\nExisting directories (not modified):")
        for d in existing:
            print(f"  - {d}")
    
    if errors:
        print("\nErrors:")
        for d in errors:
            print(f"  - {d}")
    
    return {
        "created": created,
        "existing": existing,
        "errors": errors,
        "dry_run": dry_run
    }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Initialize data directory structure (raw/processed standard)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating"
    )
    
    args = parser.parse_args()
    
    result = init_data_dirs(dry_run=args.dry_run)
    
    if result["errors"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()








