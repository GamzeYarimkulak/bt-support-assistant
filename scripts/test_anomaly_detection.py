"""
Anomali Tespiti Test Scripti

Bu script anomali tespiti sistemini test eder:
1. Mevcut CSV verilerini kullanarak test
2. Chat loglarından (chat_tickets.csv) anomali tespiti
3. Manuel test senaryoları

Kullanım:
    # Mevcut CSV verileri ile test
    python scripts/test_anomaly_detection.py --csv data/raw/tickets/sample_itsm_tickets.csv
    
    # Chat logları ile test
    python scripts/test_anomaly_detection.py --chat-logs
    
    # Manuel test (aynı konuyla ilgili art arda sorunlar)
    python scripts/test_anomaly_detection.py --manual-test
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from core.anomaly.engine import AnomalyTicket, analyze_ticket_stream
from data_pipeline.ingestion import load_itsm_tickets_from_csv, ITSMTicket
from data_pipeline.anonymize import DataAnonymizer
from data_pipeline.build_indexes import IndexBuilder

logger = structlog.get_logger()


def load_tickets_for_anomaly(csv_path: str, anonymize: bool = True) -> List[AnomalyTicket]:
    """
    Load tickets from CSV and convert to AnomalyTicket format.
    
    Args:
        csv_path: Path to CSV file
        anonymize: Whether to anonymize PII
        
    Returns:
        List of AnomalyTicket objects
    """
    print(f"📂 Loading tickets from: {csv_path}")
    
    # Load raw tickets
    raw_tickets = load_itsm_tickets_from_csv(csv_path)
    
    if not raw_tickets:
        raise ValueError(f"No tickets found in {csv_path}")
    
    print(f"   ✓ Loaded {len(raw_tickets)} tickets")
    
    # Anonymize if requested
    if anonymize:
        print("   🔒 Anonymizing PII data...")
        anonymizer = DataAnonymizer(anonymization_enabled=True)
        raw_tickets = anonymizer.anonymize_tickets(raw_tickets)
        print("   ✓ Anonymization complete")
    
    # Load embedding model for semantic analysis
    print("   🔍 Loading embedding model...")
    embedding_retriever = None
    try:
        index_builder = IndexBuilder(index_dir="indexes/")
        embedding_retriever = index_builder.load_embedding_index()
        
        if embedding_retriever:
            print("   ✓ Embedding model loaded")
        else:
            print("   ⚠️  Embedding model not found, semantic drift will be skipped")
    except Exception as e:
        print(f"   ⚠️  Failed to load embedding model: {e}")
        print("   ⚠️  Semantic drift will be skipped")
    
    # Convert to AnomalyTicket format
    print("   🔄 Converting to AnomalyTicket format...")
    anomaly_tickets = []
    
    for ticket in raw_tickets:
        # Get embedding for this ticket's content
        embedding = None
        if embedding_retriever:
            try:
                text = f"{ticket.short_description or ''} {ticket.description or ''} {ticket.resolution or ''}"
                text = text.strip()
                
                if text:
                    embedding_result = embedding_retriever.model.encode([text])[0]
                    embedding = embedding_result
            except Exception as e:
                logger.debug("failed_to_embed_ticket", ticket_id=ticket.ticket_id, error=str(e))
        
        anomaly_ticket = AnomalyTicket(
            ticket_id=ticket.ticket_id or 'unknown',
            created_at=ticket.created_at or datetime.now(),
            category=ticket.category,
            subcategory=ticket.subcategory,
            priority=ticket.priority,
            embedding=embedding,
        )
        
        anomaly_tickets.append(anomaly_ticket)
    
    print(f"   ✓ Converted {len(anomaly_tickets)} tickets")
    
    return anomaly_tickets


def load_chat_logs_for_anomaly(chat_logs_path: Optional[str] = None) -> List[AnomalyTicket]:
    """
    Load chat logs (chat_tickets.csv) and convert to AnomalyTicket format.
    
    Args:
        chat_logs_path: Path to chat_tickets.csv (default: data/processed/chat_logs/chat_tickets.csv)
        
    Returns:
        List of AnomalyTicket objects
    """
    if chat_logs_path is None:
        chat_logs_path = os.path.join(settings.chat_logs_dir, "chat_tickets.csv")
    
    chat_path = Path(chat_logs_path)
    
    if not chat_path.exists():
        print(f"⚠️  Chat logs not found: {chat_logs_path}")
        print("   💡 Start using the chat interface to generate logs")
        return []
    
    print(f"📂 Loading chat logs from: {chat_logs_path}")
    
    # Load chat tickets CSV
    df = pd.read_csv(chat_path)
    
    if len(df) == 0:
        print("   ⚠️  No chat tickets found")
        return []
    
    print(f"   ✓ Loaded {len(df)} chat tickets")
    
    # Load embedding model
    print("   🔍 Loading embedding model...")
    embedding_retriever = None
    try:
        index_builder = IndexBuilder(index_dir="indexes/")
        embedding_retriever = index_builder.load_embedding_index()
        
        if embedding_retriever:
            print("   ✓ Embedding model loaded")
    except Exception as e:
        print(f"   ⚠️  Failed to load embedding model: {e}")
    
    # Convert to AnomalyTicket format
    print("   🔄 Converting to AnomalyTicket format...")
    anomaly_tickets = []
    
    for _, row in df.iterrows():
        # Get embedding
        embedding = None
        if embedding_retriever:
            try:
                text = f"{row.get('short_description', '')} {row.get('description', '')}"
                text = text.strip()
                
                if text:
                    embedding_result = embedding_retriever.model.encode([text])[0]
                    embedding = embedding_result
            except Exception as e:
                logger.debug("failed_to_embed_chat_ticket", ticket_id=row.get('ticket_id'), error=str(e))
        
        # Parse created_at
        created_at = datetime.now()
        try:
            if pd.notna(row.get('created_at')):
                created_at = pd.to_datetime(row['created_at']).to_pydatetime()
        except:
            pass
        
        anomaly_ticket = AnomalyTicket(
            ticket_id=row.get('ticket_id', 'unknown'),
            created_at=created_at,
            category=row.get('category', 'General'),
            subcategory=row.get('subcategory', ''),
            priority=row.get('priority', 'Medium'),
            embedding=embedding,
        )
        
        anomaly_tickets.append(anomaly_ticket)
    
    print(f"   ✓ Converted {len(anomaly_tickets)} chat tickets")
    
    return anomaly_tickets


def create_manual_test_scenario() -> List[AnomalyTicket]:
    """
    Create a manual test scenario with repeated similar issues.
    Simulates a spike in VPN-related problems.
    
    Returns:
        List of AnomalyTicket objects
    """
    print("🧪 Creating manual test scenario (VPN spike)...")
    
    # Load embedding model
    embedding_retriever = None
    try:
        index_builder = IndexBuilder(index_dir="indexes/")
        embedding_retriever = index_builder.load_embedding_index()
    except:
        pass
    
    # Create baseline tickets (normal distribution)
    base_time = datetime.now() - timedelta(days=7)
    anomaly_tickets = []
    
    # Baseline: Mixed categories
    categories = ["Outlook", "Printer", "Network", "Hardware", "System"]
    for i in range(20):
        ticket_time = base_time + timedelta(hours=i * 6)
        category = categories[i % len(categories)]
        
        text = f"{category} issue {i}"
        embedding = None
        if embedding_retriever:
            try:
                embedding = embedding_retriever.model.encode([text])[0]
            except:
                pass
        
        anomaly_tickets.append(AnomalyTicket(
            ticket_id=f"BASELINE-{i}",
            created_at=ticket_time,
            category=category,
            subcategory="",
            priority="Medium",
            embedding=embedding,
        ))
    
    # Anomaly: VPN spike (last 24 hours)
    spike_start = datetime.now() - timedelta(hours=24)
    for i in range(15):  # 15 VPN tickets in 24 hours (anomaly!)
        ticket_time = spike_start + timedelta(minutes=i * 30)
        
        text = f"VPN bağlantı sorunu {i} - bağlanamıyorum"
        embedding = None
        if embedding_retriever:
            try:
                embedding = embedding_retriever.model.encode([text])[0]
            except:
                pass
        
        anomaly_tickets.append(AnomalyTicket(
            ticket_id=f"VPN-SPIKE-{i}",
            created_at=ticket_time,
            category="VPN",
            subcategory="Connection",
            priority="High",
            embedding=embedding,
        ))
    
    print(f"   ✓ Created {len(anomaly_tickets)} test tickets")
    print(f"      - Baseline: 20 tickets (mixed categories)")
    print(f"      - Anomaly: 15 VPN tickets (last 24 hours)")
    
    return anomaly_tickets


def run_anomaly_test(
    tickets: List[AnomalyTicket],
    window_size_hours: int = 24,
    min_baseline_windows: int = 3
) -> Dict[str, Any]:
    """
    Run anomaly detection test.
    
    Args:
        tickets: List of AnomalyTicket objects
        window_size_hours: Window size in hours (default: 24)
        min_baseline_windows: Minimum baseline windows
        
    Returns:
        Dictionary with test results
    """
    print("\n" + "=" * 70)
    print("ANOMALY DETECTION TEST")
    print("=" * 70)
    print(f"Total tickets: {len(tickets)}")
    print(f"Window size: {window_size_hours} hours")
    print(f"Min baseline windows: {min_baseline_windows}")
    print()
    
    if len(tickets) < 10:
        print("⚠️  WARNING: Less than 10 tickets. Anomaly detection may not work well.")
        print("   Minimum recommended: 20-30 tickets")
        return {
            "success": False,
            "error": "Insufficient tickets",
            "ticket_count": len(tickets)
        }
    
    # Run analysis
    print("🔍 Running anomaly analysis...")
    window_size = timedelta(hours=window_size_hours)
    
    try:
        stats, events = analyze_ticket_stream(
            tickets=tickets,
            window_size=window_size,
            min_baseline_windows=min_baseline_windows,
        )
        
        print(f"   ✓ Analysis complete")
        print(f"      - Total windows: {len(stats)}")
        print(f"      - Anomaly events: {len(events)}")
        print()
        
        # Display results
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        # Window statistics
        print("\n📊 Window Statistics:")
        for i, stat in enumerate(stats[-10:], 1):  # Last 10 windows
            severity_icon = {
                "normal": "✅",
                "info": "ℹ️ ",
                "warning": "⚠️ ",
                "critical": "🔴"
            }.get(stat.severity, "❓")
            
            print(f"  {severity_icon} Window {i}: {stat.window_start.strftime('%Y-%m-%d %H:%M')}")
            print(f"     Tickets: {stat.total_tickets}")
            print(f"     Volume Z-score: {stat.volume_z:.2f}" if stat.volume_z else "     Volume Z-score: N/A")
            print(f"     Category Divergence: {stat.category_divergence:.3f}" if stat.category_divergence else "     Category Divergence: N/A")
            print(f"     Semantic Drift: {stat.semantic_drift:.3f}" if stat.semantic_drift else "     Semantic Drift: N/A")
            print(f"     Combined Score: {stat.combined_score:.3f}")
            print(f"     Severity: {stat.severity.upper()}")
            if stat.reasons:
                print(f"     Reasons: {', '.join(stat.reasons)}")
            print()
        
        # Anomaly events
        if events:
            print("🚨 Anomaly Events Detected:")
            for event in events:
                severity_icon = {
                    "info": "ℹ️ ",
                    "warning": "⚠️ ",
                    "critical": "🔴"
                }.get(event.severity, "❓")
                
                print(f"  {severity_icon} {event.window_start.strftime('%Y-%m-%d %H:%M')} - {event.severity.upper()}")
                print(f"     Score: {event.score:.3f}")
                print(f"     Reasons: {', '.join(event.reasons)}")
                print()
        else:
            print("✅ No anomaly events detected (all windows normal)")
            print()
        
        # Summary statistics
        severity_counts = {}
        for stat in stats:
            severity_counts[stat.severity] = severity_counts.get(stat.severity, 0) + 1
        
        print("📈 Summary:")
        print(f"   Total windows: {len(stats)}")
        print(f"   Anomaly events: {len(events)}")
        print(f"   Severity distribution:")
        for severity, count in sorted(severity_counts.items()):
            print(f"      - {severity}: {count}")
        
        # Calculate metrics
        total_tickets = sum(stat.total_tickets for stat in stats)
        anomalous_windows = len(events)
        anomaly_rate = (anomalous_windows / len(stats)) * 100 if stats else 0
        
        print(f"\n📊 Metrics:")
        print(f"   Total tickets analyzed: {total_tickets}")
        print(f"   Anomaly rate: {anomaly_rate:.1f}%")
        print(f"   Average tickets per window: {total_tickets / len(stats):.1f}" if stats else "   Average tickets per window: N/A")
        
        return {
            "success": True,
            "total_windows": len(stats),
            "anomaly_events": len(events),
            "total_tickets": total_tickets,
            "anomaly_rate": anomaly_rate,
            "severity_distribution": severity_counts,
            "events": [
                {
                    "window_start": e.window_start.isoformat(),
                    "window_end": e.window_end.isoformat(),
                    "severity": e.severity,
                    "score": e.score,
                    "reasons": e.reasons
                }
                for e in events
            ],
            "stats": [
                {
                    "window_start": s.window_start.isoformat(),
                    "window_end": s.window_end.isoformat(),
                    "total_tickets": s.total_tickets,
                    "volume_z": s.volume_z,
                    "category_divergence": s.category_divergence,
                    "semantic_drift": s.semantic_drift,
                    "combined_score": s.combined_score,
                    "severity": s.severity,
                    "reasons": s.reasons
                }
                for s in stats
            ]
        }
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test anomaly detection system"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to CSV file with tickets"
    )
    parser.add_argument(
        "--chat-logs",
        action="store_true",
        help="Use chat logs (chat_tickets.csv) for testing"
    )
    parser.add_argument(
        "--manual-test",
        action="store_true",
        help="Create manual test scenario (VPN spike)"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=24,
        help="Window size in hours (default: 24)"
    )
    parser.add_argument(
        "--min-baseline",
        type=int,
        default=3,
        help="Minimum baseline windows (default: 3)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for results"
    )
    
    args = parser.parse_args()
    
    # Determine data source
    tickets = []
    
    if args.manual_test:
        tickets = create_manual_test_scenario()
    elif args.chat_logs:
        tickets = load_chat_logs_for_anomaly()
        if not tickets:
            print("\n❌ No chat logs found. Start using the chat interface first.")
            return
    elif args.csv:
        tickets = load_tickets_for_anomaly(args.csv)
    else:
        # Default: Try sample_itsm_tickets.csv
        default_csv = os.path.join(settings.data_dir, "raw", "tickets", "sample_itsm_tickets.csv")
        if Path(default_csv).exists():
            print(f"📂 Using default CSV: {default_csv}")
            tickets = load_tickets_for_anomaly(default_csv)
        else:
            print("❌ No data source specified. Use --csv, --chat-logs, or --manual-test")
            parser.print_help()
            return
    
    # Run test
    results = run_anomaly_test(
        tickets=tickets,
        window_size_hours=args.window_size,
        min_baseline_windows=args.min_baseline
    )
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Results saved to: {args.output}")
    
    print("\n" + "=" * 70)
    if results.get("success"):
        print("✅ TEST COMPLETED SUCCESSFULLY")
    else:
        print("❌ TEST FAILED")
    print("=" * 70)


if __name__ == "__main__":
    main()



