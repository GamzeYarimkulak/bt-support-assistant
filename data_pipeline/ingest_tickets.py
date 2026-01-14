"""
Ticket ingestion pipeline: CSV → Parquet (standardized schema).

Reads CSV files from data/raw/tickets/ and converts them to a single
standardized parquet file at data/processed/tickets.parquet.

Schema:
- id: str
- text: str (subject + body combined)
- resolution: str
- category: str
- priority: str
- language: str
- created_at: datetime or None
- source: str (filename)
"""

import os
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

logger = structlog.get_logger()

# Column mapping: different CSV column names → standard schema
COLUMN_MAPPING = {
    "text": [
        "subject", "title", "short_description", "summary",
        "body", "description", "content", "message"
    ],
    "resolution": [
        "resolution", "answer", "solution", "resolution_text",
        "resolved", "resolution_notes"
    ],
    "category": [
        "category", "type", "queue", "tag_1", "classification",
        "issue_type", "ticket_type"
    ],
    "priority": [
        "priority", "severity", "urgency", "priority_level"
    ],
    "language": [
        "language", "lang", "locale"
    ],
    "created_at": [
        "created_at", "date", "time", "created", "timestamp",
        "created_date", "created_time", "opened_at"
    ],
    "id": [
        "id", "ticket_id", "ticket", "number", "ticket_number",
        "incident_id", "request_id"
    ]
}


def find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
    """
    Find column in DataFrame by trying multiple possible names.
    
    Args:
        df: DataFrame to search
        possible_names: List of possible column names
        
    Returns:
        Column name if found, None otherwise
    """
    for name in possible_names:
        # Case-insensitive search
        for col in df.columns:
            if col.lower() == name.lower():
                return col
    return None


def map_columns(df: pd.DataFrame, source_file: str) -> Dict[str, Optional[str]]:
    """
    Map CSV columns to standard schema.
    
    Args:
        df: Input DataFrame
        source_file: Source filename (for logging)
        
    Returns:
        Dictionary mapping standard field names to actual column names
    """
    mapping = {}
    
    for standard_field, possible_names in COLUMN_MAPPING.items():
        col_name = find_column(df, possible_names)
        mapping[standard_field] = col_name
        
        if col_name:
            logger.debug("column_mapped",
                        source_file=source_file,
                        standard_field=standard_field,
                        actual_column=col_name)
        else:
            logger.debug("column_not_found",
                        source_file=source_file,
                        standard_field=standard_field)
    
    return mapping


def combine_text_fields(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.Series:
    """
    Combine text fields (subject + body) into single 'text' field.
    
    Args:
        df: Input DataFrame
        mapping: Column mapping dictionary
        
    Returns:
        Series with combined text
    """
    text_parts = []
    
    # Try to find subject/title field
    subject_col = mapping.get("text")
    if subject_col and subject_col in df.columns:
        text_parts.append(df[subject_col].fillna(""))
    
    # Try to find body/description field
    body_candidates = ["body", "description", "content", "message"]
    for col in body_candidates:
        if col in df.columns and col != subject_col:
            text_parts.append(df[col].fillna(""))
            break
    
    # Combine
    if text_parts:
        combined = text_parts[0]
        for part in text_parts[1:]:
            combined = combined + " " + part
        return combined.str.strip()
    else:
        # Fallback: use first text-like column
        return df.iloc[:, 0].fillna("").astype(str)


def parse_datetime(series: pd.Series) -> pd.Series:
    """
    Parse datetime column with multiple format attempts.
    
    Args:
        series: Series with datetime strings
        
    Returns:
        Series with datetime objects (NaT for unparseable)
    """
    if series.isna().all():
        return pd.Series([None] * len(series), dtype='datetime64[ns]')
    
    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]
    
    result = pd.Series([None] * len(series), dtype='datetime64[ns]')
    
    for fmt in formats:
        try:
            parsed = pd.to_datetime(series, format=fmt, errors='coerce')
            if parsed.notna().sum() > result.notna().sum():
                result = parsed
        except:
            continue
    
    # Final attempt: pandas auto-detect
    if result.isna().all():
        result = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    
    return result


def anonymize_if_enabled(text: str) -> str:
    """
    Anonymize text if anonymization is enabled.
    
    Args:
        text: Input text
        
    Returns:
        Anonymized text (or original if anonymization disabled)
    """
    if not settings.anonymization_enabled:
        return text
    
    try:
        from data_pipeline.anonymize import anonymize_text
        return anonymize_text(text)
    except ImportError:
        logger.warning("anonymize_module_not_found",
                     message="anonymize.py not found, skipping anonymization")
        return text
    except Exception as e:
        logger.warning("anonymization_failed", error=str(e))
        return text


def ingest_tickets(
    input_dir: Optional[str] = None,
    output_file: Optional[str] = None,
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Ingest tickets from CSV files and convert to parquet.
    
    Args:
        input_dir: Directory containing CSV files (default: data/raw/tickets/)
        output_file: Output parquet file path (default: data/processed/tickets.parquet)
        dry_run: If True, only analyze without writing
        limit: Limit number of rows to process per file (for testing)
        
    Returns:
        Dictionary with ingestion statistics
    """
    if input_dir is None:
        input_dir = os.path.join(settings.data_dir, "raw", "tickets")
    
    if output_file is None:
        output_file = os.path.join(settings.data_dir, "processed", "tickets.parquet")
    
    input_path = Path(input_dir)
    output_path = Path(output_file)
    
    print("=" * 70)
    print("TICKET INGESTION PIPELINE")
    print("=" * 70)
    print(f"Input directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Mode: {'DRY RUN' if dry_run else 'PROCESS'}")
    print(f"Anonymization: {'ENABLED' if settings.anonymization_enabled else 'DISABLED'}")
    print()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Find CSV files
    csv_files = list(input_path.glob("*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")
    
    print(f"Found {len(csv_files)} CSV file(s):")
    for f in csv_files:
        print(f"  - {f.name}")
    print()
    
    all_data = []
    column_mapping_report = {}
    
    for csv_file in csv_files:
        print(f"Processing: {csv_file.name}")
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
            
            if limit:
                df = df.head(limit)
            
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {list(df.columns)}")
            
            # Map columns
            mapping = map_columns(df, csv_file.name)
            column_mapping_report[csv_file.name] = mapping
            
            # Combine text fields
            text_series = combine_text_fields(df, mapping)
            
            # Build standardized dataframe
            standardized = pd.DataFrame()
            
            # ID
            id_col = mapping.get("id")
            if id_col and id_col in df.columns:
                standardized["id"] = df[id_col].astype(str)
            else:
                standardized["id"] = [f"{csv_file.stem}_{i}" for i in range(len(df))]
            
            # Text (with anonymization if enabled)
            if settings.anonymization_enabled:
                standardized["text"] = text_series.apply(anonymize_if_enabled)
            else:
                standardized["text"] = text_series
            
            # Resolution
            res_col = mapping.get("resolution")
            if res_col and res_col in df.columns:
                standardized["resolution"] = df[res_col].fillna("").astype(str)
            else:
                standardized["resolution"] = ""
            
            # Category
            cat_col = mapping.get("category")
            if cat_col and cat_col in df.columns:
                standardized["category"] = df[cat_col].fillna("").astype(str)
            else:
                standardized["category"] = ""
            
            # Priority
            pri_col = mapping.get("priority")
            if pri_col and pri_col in df.columns:
                standardized["priority"] = df[pri_col].fillna("").astype(str)
            else:
                standardized["priority"] = ""
            
            # Language
            lang_col = mapping.get("language")
            if lang_col and lang_col in df.columns:
                standardized["language"] = df[lang_col].fillna("tr").astype(str)
            else:
                standardized["language"] = "tr"
            
            # Created at
            date_col = mapping.get("created_at")
            if date_col and date_col in df.columns:
                standardized["created_at"] = parse_datetime(df[date_col])
            else:
                standardized["created_at"] = None
            
            # Source
            standardized["source"] = csv_file.name
            
            all_data.append(standardized)
            
            print(f"  ✓ Processed {len(standardized)} rows")
            
        except Exception as e:
            logger.error("csv_processing_failed",
                        file=csv_file.name,
                        error=str(e))
            print(f"  ✗ Error: {e}")
            continue
    
    if not all_data:
        raise ValueError("No data processed from any CSV files")
    
    # Combine all dataframes
    combined_df = pd.concat(all_data, ignore_index=True)
    
    print()
    print("=" * 70)
    print("COLUMN MAPPING REPORT")
    print("=" * 70)
    for filename, mapping in column_mapping_report.items():
        print(f"\n{filename}:")
        for std_field, actual_col in mapping.items():
            if actual_col:
                print(f"  {std_field} → {actual_col}")
            else:
                print(f"  {std_field} → (not found)")
    
    print()
    print("=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)
    print(f"Total rows: {len(combined_df)}")
    print(f"Total columns: {len(combined_df.columns)}")
    print(f"\nColumn null rates:")
    for col in combined_df.columns:
        null_count = combined_df[col].isna().sum()
        null_pct = (null_count / len(combined_df)) * 100
        print(f"  {col}: {null_count} ({null_pct:.1f}%)")
    
    if dry_run:
        print("\n[DRY RUN] Would write parquet file (not writing)")
        print(f"  Output: {output_path}")
        print(f"  Estimated size: ~{len(combined_df) * 500 / 1024 / 1024:.1f} MB")
    else:
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write parquet
        combined_df.to_parquet(output_path, index=False, engine='pyarrow')
        
        file_size = output_path.stat().st_size / 1024 / 1024
        print(f"\n✓ Parquet file written: {output_path}")
        print(f"  File size: {file_size:.2f} MB")
    
    return {
        "num_rows": len(combined_df),
        "num_columns": len(combined_df.columns),
        "output_file": str(output_path),
        "column_mapping": column_mapping_report,
        "null_rates": {
            col: float(combined_df[col].isna().sum() / len(combined_df))
            for col in combined_df.columns
        },
        "dry_run": dry_run
    }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest tickets from CSV files and convert to parquet"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Input directory (default: data/raw/tickets/)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output parquet file (default: data/processed/tickets.parquet)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze without writing output file"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of rows per CSV file (for testing)"
    )
    
    args = parser.parse_args()
    
    try:
        result = ingest_tickets(
            input_dir=args.input_dir,
            output_file=args.output,
            dry_run=args.dry_run,
            limit=args.limit
        )
        
        print("\n✓ Ingestion completed successfully")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()








