"""
Data ingestion from ITSM systems and document repositories.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import structlog

logger = structlog.get_logger()


class ITSMTicket(BaseModel):
    """
    Pydantic model for an ITSM ticket.
    Represents a standardized ticket structure from CSV ingestion.
    """
    ticket_id: str = Field(..., description="Unique ticket identifier")
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    category: str = Field(default="", description="Primary category/classification")
    subcategory: str = Field(default="", description="Secondary category")
    short_description: str = Field(default="", description="Brief summary of the issue")
    description: str = Field(default="", description="Detailed description of the issue")
    resolution: str = Field(default="", description="Resolution notes or solution")
    channel: str = Field(default="", description="Reporting channel (email, phone, web, etc.)")
    priority: str = Field(default="", description="Priority level (low, medium, high, critical)")
    status: str = Field(default="", description="Current ticket status")
    
    @field_validator('created_at', mode='before')
    @classmethod
    def parse_created_at(cls, v):
        """Parse created_at from string to datetime if needed."""
        if isinstance(v, str):
            # Try common datetime formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(v.strip(), fmt)
                except ValueError:
                    continue
            # If all formats fail, try ISO format
            try:
                return datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Cannot parse datetime from: {v}")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def load_itsm_tickets_from_csv(path: str) -> List[ITSMTicket]:
    """
    Load ITSM tickets from a CSV file.
    
    This function reads a CSV file containing ITSM ticket data and returns
    a list of validated ITSMTicket objects. It handles:
    - Datetime parsing for the created_at field
    - Whitespace stripping from all text fields
    - Preservation of Turkish and other Unicode characters
    - Graceful error handling with detailed logging
    
    Args:
        path: Path to the CSV file. Expected columns:
              ticket_id, created_at, category, subcategory, short_description,
              description, resolution, channel, priority, status
              
    Returns:
        List of ITSMTicket objects parsed from the CSV
        
    Raises:
        FileNotFoundError: If the CSV file does not exist
        ValueError: If the CSV has missing required columns or invalid data
        
    Example:
        >>> tickets = load_itsm_tickets_from_csv("data/sample_itsm_tickets.csv")
        >>> print(f"Loaded {len(tickets)} tickets")
    """
    csv_path = Path(path)
    
    if not csv_path.exists():
        logger.error("csv_file_not_found", path=path)
        raise FileNotFoundError(f"CSV file not found: {path}")
    
    tickets = []
    errors = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Validate required columns
            required_cols = {'ticket_id', 'created_at'}
            if reader.fieldnames and not required_cols.issubset(set(reader.fieldnames)):
                missing = required_cols - set(reader.fieldnames)
                raise ValueError(f"Missing required columns: {missing}")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Strip whitespace from all string fields
                    cleaned_row = {
                        key: value.strip() if isinstance(value, str) else value
                        for key, value in row.items()
                    }
                    
                    # Create ITSMTicket object (Pydantic will validate)
                    ticket = ITSMTicket(**cleaned_row)
                    tickets.append(ticket)
                    
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning("ticket_parsing_failed", 
                                 row=row_num, 
                                 ticket_id=row.get('ticket_id', 'unknown'),
                                 error=str(e))
        
        logger.info("csv_tickets_loaded",
                   path=path,
                   total_tickets=len(tickets),
                   failed_rows=len(errors))
        
        if errors and len(errors) > 10:
            logger.warning("many_parsing_errors", 
                         error_count=len(errors),
                         sample_errors=errors[:5])
        
        return tickets
        
    except Exception as e:
        logger.error("csv_loading_failed", path=path, error=str(e))
        raise


class DataIngestion:
    """
    Handles ingestion of ITSM tickets and internal documentation.
    Can connect to various data sources (databases, APIs, file systems).
    """
    
    def __init__(self, data_dir: str = "./data"):
        """
        Initialize data ingestion.
        
        Args:
            data_dir: Directory for storing ingested data
        """
        self.data_dir = data_dir
        logger.info("data_ingestion_initialized", data_dir=data_dir)
    
    def ingest_tickets_from_json(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Ingest tickets from JSON file.
        
        Args:
            filepath: Path to JSON file containing tickets
            
        Returns:
            List of ticket dictionaries
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            tickets = data if isinstance(data, list) else data.get("tickets", [])
            
            logger.info("tickets_ingested_from_json",
                       filepath=filepath,
                       num_tickets=len(tickets))
            
            return tickets
            
        except Exception as e:
            logger.error("json_ingestion_failed", filepath=filepath, error=str(e))
            return []
    
    def ingest_tickets_from_database(
        self,
        query: str,
        connection_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Ingest tickets from database.
        
        Args:
            query: SQL query to fetch tickets
            connection_params: Database connection parameters
            
        Returns:
            List of ticket dictionaries
        """
        # TODO: Implement database connection
        # This would use libraries like psycopg2, pymongo, etc.
        logger.warning("database_ingestion_not_implemented")
        return []
    
    def ingest_tickets_from_api(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ingest tickets from REST API.
        
        Args:
            api_url: API endpoint URL
            api_key: Optional API key for authentication
            params: Optional query parameters
            
        Returns:
            List of ticket dictionaries
        """
        # TODO: Implement API ingestion
        # This would use requests or httpx
        logger.warning("api_ingestion_not_implemented")
        return []
    
    def ingest_documents_from_directory(
        self,
        directory: str,
        file_extensions: List[str] = [".txt", ".md", ".pdf"]
    ) -> List[Dict[str, Any]]:
        """
        Ingest documents from directory.
        
        Args:
            directory: Directory path
            file_extensions: List of file extensions to include
            
        Returns:
            List of document dictionaries
        """
        # TODO: Implement directory scanning and document parsing
        logger.warning("directory_ingestion_not_implemented")
        return []
    
    def validate_ticket(self, ticket: Dict[str, Any]) -> bool:
        """
        Validate ticket structure and required fields.
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["id", "title", "description"]
        
        for field in required_fields:
            if field not in ticket:
                logger.warning("ticket_validation_failed",
                             ticket_id=ticket.get("id", "unknown"),
                             missing_field=field)
                return False
        
        return True
    
    def filter_tickets_by_date(
        self,
        tickets: List[Dict[str, Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_field: str = "created_at"
    ) -> List[Dict[str, Any]]:
        """
        Filter tickets by date range.
        
        Args:
            tickets: List of tickets
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            date_field: Field name containing the date
            
        Returns:
            Filtered list of tickets
        """
        if not start_date and not end_date:
            return tickets
        
        filtered = []
        for ticket in tickets:
            if date_field not in ticket:
                continue
            
            # Parse date (assuming ISO format)
            try:
                ticket_date = datetime.fromisoformat(ticket[date_field].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning("date_parsing_failed",
                             ticket_id=ticket.get("id"),
                             date_field=date_field)
                continue
            
            if start_date and ticket_date < start_date:
                continue
            if end_date and ticket_date > end_date:
                continue
            
            filtered.append(ticket)
        
        logger.info("tickets_filtered_by_date",
                   original_count=len(tickets),
                   filtered_count=len(filtered))
        
        return filtered
    
    def normalize_ticket_schema(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ticket to standard schema.
        
        Args:
            ticket: Raw ticket dictionary
            
        Returns:
            Normalized ticket
        """
        # Map common field variations to standard fields
        normalized = {
            "id": ticket.get("id") or ticket.get("ticket_id") or ticket.get("number"),
            "title": ticket.get("title") or ticket.get("subject") or ticket.get("summary"),
            "description": ticket.get("description") or ticket.get("body") or ticket.get("details"),
            "status": ticket.get("status") or ticket.get("state"),
            "priority": ticket.get("priority") or ticket.get("urgency"),
            "category": ticket.get("category") or ticket.get("type"),
            "created_at": ticket.get("created_at") or ticket.get("created") or ticket.get("timestamp"),
            "updated_at": ticket.get("updated_at") or ticket.get("modified"),
            "resolved_at": ticket.get("resolved_at") or ticket.get("closed_at"),
        }
        
        # Include any additional fields
        for key, value in ticket.items():
            if key not in normalized:
                normalized[key] = value
        
        return normalized
    
    def save_tickets(self, tickets: List[Dict[str, Any]], filename: str = "tickets.json"):
        """
        Save tickets to JSON file.
        
        Args:
            tickets: List of tickets
            filename: Output filename
        """
        import os
        os.makedirs(self.data_dir, exist_ok=True)
        
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
        
        logger.info("tickets_saved", filepath=filepath, num_tickets=len(tickets))

