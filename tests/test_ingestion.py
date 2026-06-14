"""
Tests for data ingestion from CSV files.
"""

import pytest
from pathlib import Path
from datetime import datetime
from data_pipeline.ingestion import load_itsm_tickets_from_csv, ITSMTicket


DATA_PATH = Path("data") / "raw" / "tickets" / "sample_itsm_tickets.csv"


class TestCSVIngestion:
    """Tests for CSV ingestion functionality."""
    
    def test_load_itsm_tickets_from_csv_basic(self):
        """Test basic CSV loading functionality."""
        tickets = load_itsm_tickets_from_csv(str(DATA_PATH))
        
        # En az bir kayıt olsun
        assert len(tickets) >= 1
        
        first = tickets[0]
        assert isinstance(first, ITSMTicket)
        
        # created_at düzgün parse edilmiş olmalı
        assert isinstance(first.created_at, datetime)
        assert first.created_at.year == 2026
    
    def test_turkish_characters_preserved(self):
        """Test that Turkish characters are preserved correctly."""
        tickets = load_itsm_tickets_from_csv(str(DATA_PATH))
        
        # İlk ticket'ta Türkçe karakterler bozulmamış olmalı
        first = tickets[0]
        assert "paylaşımlı posta kutusu" in first.short_description.lower()
        assert "ş" in first.short_description.lower()
        assert "ı" in first.description.lower()
    
    def test_all_tickets_loaded(self):
        """Test that all tickets from CSV are loaded."""
        tickets = load_itsm_tickets_from_csv(str(DATA_PATH))
        
        # Ana raw ticket dosyasında genişletilmiş sentetik veri bulunur.
        assert len(tickets) >= 2000
        
        # İlk ticket ID'leri doğru mu?
        ticket_ids = [t.ticket_id for t in tickets]
        assert "TCK-00001" in ticket_ids
        assert "TCK-00002" in ticket_ids
        assert "TCK-00003" in ticket_ids
    
    def test_ticket_fields_populated(self):
        """Test that all ticket fields are populated correctly."""
        tickets = load_itsm_tickets_from_csv(str(DATA_PATH))
        
        first = tickets[0]
        
        # Tüm zorunlu alanlar dolu olmalı
        assert first.ticket_id == "TCK-00001"
        assert first.category == "E-posta"
        assert first.subcategory == "SMTP"
        assert first.short_description != ""
        assert first.description != ""
        assert first.resolution != ""
        assert first.channel == "email"
        assert first.priority == "medium"
        assert first.status == "open"
    
    def test_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        tickets = load_itsm_tickets_from_csv(str(DATA_PATH))
        
        # Hiçbir alanda başta/sonda boşluk olmamalı
        for ticket in tickets:
            assert not ticket.ticket_id.startswith(" ")
            assert not ticket.ticket_id.endswith(" ")
            assert not ticket.category.startswith(" ")
            assert not ticket.category.endswith(" ")
    
    def test_datetime_parsing(self):
        """Test that datetime fields are correctly parsed."""
        tickets = load_itsm_tickets_from_csv(str(DATA_PATH))
        
        # İlk ticket: 2026-01-01 07:43:46
        first = tickets[0]
        assert first.created_at.year == 2026
        assert first.created_at.month == 1
        assert first.created_at.day == 1
        assert first.created_at.hour == 7
        assert first.created_at.minute == 43
    
    def test_file_not_found_raises_error(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_itsm_tickets_from_csv("nonexistent.csv")
    
    def test_itsm_ticket_model_validation(self):
        """Test ITSMTicket Pydantic model validation."""
        # Valid ticket
        ticket = ITSMTicket(
            ticket_id="TEST-001",
            created_at="2025-01-15 10:30:00",
            category="Test",
            short_description="Test ticket"
        )
        
        assert ticket.ticket_id == "TEST-001"
        assert isinstance(ticket.created_at, datetime)
        
        # Required field missing should raise error
        with pytest.raises(Exception):  # Pydantic ValidationError
            ITSMTicket(
                # Missing ticket_id and created_at
                category="Test"
            )




