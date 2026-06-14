"""
Organize project data files and create Turkish-friendly processed datasets.

This script is intentionally deterministic and conservative:
- It only moves known files inside the repository data directory.
- It converts the two known TXT exports into CSV.
- It creates a Turkish-normalized processed ticket dataset from tickets_clean.csv.
- It writes a merged CSV and parquet file for downstream indexing/evaluation.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


DIRECTORIES = [
    DATA / "raw" / "tickets" / "original",
    DATA / "raw" / "tickets" / "synthetic",
    DATA / "raw" / "tickets" / "external" / "english",
    DATA / "raw" / "tickets" / "external" / "german",
    DATA / "raw" / "tickets" / "external" / "multilingual",
    DATA / "raw" / "tickets" / "converted" / "source_texts",
    DATA / "raw" / "kb" / "converted" / "source_texts",
    DATA / "processed" / "tickets",
    DATA / "evaluation" / "anomaly",
    DATA / "evaluation" / "retrieval",
    DATA / "logs" / "synthetic",
]


MOVE_MAP = {
    DATA / "aa_dataset-tickets-multi-lang-5-2-50-version.csv": DATA
    / "raw"
    / "tickets"
    / "external"
    / "multilingual"
    / "aa_dataset-tickets-multi-lang-5-2-50-version.csv",
    DATA / "dataset-tickets-multi-lang3-4k.csv": DATA
    / "raw"
    / "tickets"
    / "external"
    / "multilingual"
    / "dataset-tickets-multi-lang3-4k.csv",
    DATA / "dataset-tickets-multi-lang-4-20k.csv": DATA
    / "raw"
    / "tickets"
    / "external"
    / "multilingual"
    / "dataset-tickets-multi-lang-4-20k.csv",
    DATA / "dataset-tickets-german_normalized.csv": DATA
    / "raw"
    / "tickets"
    / "external"
    / "german"
    / "dataset-tickets-german_normalized.csv",
    DATA / "dataset-tickets-german_normalized_50_5_2.csv": DATA
    / "raw"
    / "tickets"
    / "external"
    / "german"
    / "dataset-tickets-german_normalized_50_5_2.csv",
    DATA / "tickets_clean.csv": DATA
    / "raw"
    / "tickets"
    / "external"
    / "english"
    / "tickets_clean.csv",
    DATA / "sample_itsm_tickets.csv": DATA
    / "raw"
    / "tickets"
    / "original"
    / "sample_itsm_tickets_80.csv",
    DATA / "raw" / "tickets" / "synthetic_itsm_tickets_2200.csv": DATA
    / "raw"
    / "tickets"
    / "synthetic"
    / "synthetic_itsm_tickets_2200.csv",
    DATA / "eval" / "anomaly_ground_truth.csv": DATA
    / "evaluation"
    / "anomaly"
    / "anomaly_ground_truth.csv",
    DATA / "eval" / "retrieval_eval_queries.csv": DATA
    / "evaluation"
    / "retrieval"
    / "retrieval_eval_queries.csv",
    DATA / "evaluationcodex" / "synthetic_bt_anomaly_dataset_codex.csv": DATA
    / "evaluation"
    / "anomaly"
    / "synthetic_bt_anomaly_dataset_codex.csv",
    DATA / "logs" / "chat_logs_synthetic_500.jsonl": DATA
    / "logs"
    / "synthetic"
    / "chat_logs_synthetic_500.jsonl",
    DATA / "logs" / "chat_tickets_synthetic_500.csv": DATA
    / "logs"
    / "synthetic"
    / "chat_tickets_synthetic_500.csv",
    DATA / "deepseek_tsv_20260607_7faf13.txt": DATA
    / "raw"
    / "tickets"
    / "converted"
    / "source_texts"
    / "deepseek_tsv_20260607_7faf13.txt",
    DATA / "gemini-code-1780821831396.txt": DATA
    / "raw"
    / "kb"
    / "converted"
    / "source_texts"
    / "gemini-code-1780821831396.txt",
    DATA / "generate_dataset.py": ROOT / "scripts" / "generate_dataset.py",
}


CATEGORY_MAP = {
    "Hardware": "Donanım",
    "Software": "Yazılım",
    "Access/Permissions": "Kimlik & Erişim",
    "Network": "Ağ",
    "Email/Communication": "E-posta",
    "Database": "Veritabanı",
    "Cloud/Infrastructure": "Bulut & Altyapı",
    "Security": "Güvenlik",
}


SUBCATEGORY_MAP = {
    "Peripheral": "Çevre Birimi",
    "Compatibility": "Uyumluluk",
    "Desktop": "Masaüstü",
    "Printer": "Yazıcı",
    "Update": "Güncelleme",
    "Monitor": "Monitör",
    "Installation": "Kurulum",
    "Laptop": "Laptop",
    "License": "Lisans",
    "Slow Connection": "Yavaş Bağlantı",
    "New Account": "Yeni Hesap",
    "DNS": "DNS",
    "Permission Request": "Yetki Talebi",
    "Account Lockout": "Hesap Kilidi",
    "Firewall": "Güvenlik Duvarı",
    "Distribution List": "Dağıtım Listesi",
    "Crash": "Çökme",
    "Password Reset": "Parola Sıfırlama",
    "WiFi": "Wi-Fi",
    "Calendar": "Takvim",
    "MFA": "MFA",
    "Teams": "Teams",
    "Outlook": "Outlook",
    "VPN": "VPN",
    "Performance": "Performans",
    "Backup": "Yedekleme",
    "Data Integrity": "Veri Bütünlüğü",
    "Access": "Erişim",
    "Service Outage": "Servis Kesintisi",
    "Malware": "Zararlı Yazılım",
    "Phishing": "Oltalama",
    "Scaling": "Ölçekleme",
    "Storage": "Depolama",
    "Deployment": "Dağıtım",
    "Suspicious Activity": "Şüpheli Aktivite",
    "Policy": "Politika",
    "Vulnerability": "Zafiyet",
    "VM": "Sanal Makine",
}


PHRASE_MAP = {
    "account locked": "hesap kilitlendi",
    "password change": "parola değişikliği",
    "password reset": "parola sıfırlama",
    "security alert": "güvenlik uyarısı",
    "usb drive": "USB bellek",
    "malware": "zararlı yazılım",
    "phishing": "oltalama",
    "network": "ağ",
    "vpn": "VPN",
    "printer": "yazıcı",
    "email": "e-posta",
    "outlook": "Outlook",
    "calendar": "takvim",
    "teams": "Teams",
    "firewall": "güvenlik duvarı",
    "permission": "yetki",
    "license": "lisans",
    "installation": "kurulum",
    "update": "güncelleme",
    "crash": "çökme",
    "backup": "yedekleme",
    "database": "veritabanı",
    "storage": "depolama",
    "service outage": "servis kesintisi",
    "slow connection": "yavaş bağlantı",
    "monitor": "monitör",
    "laptop": "laptop",
    "desktop": "masaüstü",
}


def ensure_inside_workspace(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Path is outside workspace: {resolved}")
    return resolved


def ensure_directories() -> None:
    for directory in DIRECTORIES:
        ensure_inside_workspace(directory)
        directory.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst: Path) -> bool:
    ensure_inside_workspace(src)
    ensure_inside_workspace(dst)

    if not src.exists():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        print(f"skip move, destination exists: {dst.relative_to(ROOT)}")
        return False

    shutil.move(str(src), str(dst))
    print(f"moved: {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    return True


def convert_deepseek_txt(source_txt: Path, output_csv: Path) -> int:
    if not source_txt.exists():
        return 0

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    base_date = datetime(2026, 6, 7, 8, 0, 0)

    with source_txt.open("r", encoding="utf-8") as txt_file:
        for index, line in enumerate(txt_file):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue

            source_id, short_description, category, priority_score = parts[:4]
            try:
                score = int(priority_score)
            except ValueError:
                score = 3

            priority = "critical" if score >= 5 else "high" if score == 4 else "medium" if score == 3 else "low"
            created_at = base_date + timedelta(minutes=17 * index)

            rows.append(
                {
                    "ticket_id": f"DS-{int(source_id):05d}" if source_id.isdigit() else f"DS-{index + 1:05d}",
                    "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "category": category.strip(),
                    "subcategory": "",
                    "short_description": short_description.strip(),
                    "description": f"{short_description.strip()} konusu için LLM kaynaklı sentetik destek kaydı.",
                    "resolution": "",
                    "channel": "synthetic_txt",
                    "priority": priority,
                    "status": "open",
                    "is_anomaly": "No",
                    "anomaly_type": "",
                    "source_file": source_txt.name,
                    "source_row_id": source_id,
                    "priority_score": str(score),
                }
            )

    fieldnames = [
        "ticket_id",
        "created_at",
        "category",
        "subcategory",
        "short_description",
        "description",
        "resolution",
        "channel",
        "priority",
        "status",
        "is_anomaly",
        "anomaly_type",
        "source_file",
        "source_row_id",
        "priority_score",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"converted txt to csv: {output_csv.relative_to(ROOT)} ({len(rows)} rows)")
    return len(rows)


def convert_gemini_txt(source_txt: Path, output_csv: Path) -> int:
    if not source_txt.exists():
        return 0

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with source_txt.open("r", encoding="utf-8", newline="") as txt_file:
        reader = csv.DictReader(txt_file)
        rows = list(reader)

    fieldnames = reader.fieldnames or ["document_id", "title", "content", "category"]
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"converted txt to csv: {output_csv.relative_to(ROOT)} ({len(rows)} rows)")
    return len(rows)


def tr_phrase(text: str) -> str:
    normalized = (text or "").strip()
    lowered = normalized.lower()
    for english, turkish in PHRASE_MAP.items():
        lowered = lowered.replace(english, turkish)
    return lowered[:1].upper() + lowered[1:] if lowered else ""


def normalize_priority(priority: str) -> str:
    value = (priority or "").strip().lower()
    if value in {"critical", "high", "medium", "low"}:
        return value
    return "medium"


def normalize_status(status: str) -> str:
    value = (status or "").strip().lower()
    if value in {"resolved", "closed"}:
        return "resolved"
    if value in {"open", "new", "pending"}:
        return "open"
    return value or "resolved"


def normalize_tickets_clean_english(source_csv: Path, output_csv: Path) -> int:
    if not source_csv.exists():
        return 0

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    with source_csv.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            category_tr = CATEGORY_MAP.get(row.get("category", ""), row.get("category", "Genel") or "Genel")
            subcategory_tr = SUBCATEGORY_MAP.get(
                row.get("sub_category", ""),
                tr_phrase(row.get("sub_category", "")) or "Genel",
            )
            product = (row.get("product_service") or "kurumsal sistem").strip()
            department = (row.get("department") or "Bilinmeyen").strip()
            priority = normalize_priority(row.get("priority", ""))
            original_subject_hint = tr_phrase(row.get("subject", ""))

            short_description = f"{product} - {subcategory_tr} sorunu"
            if original_subject_hint:
                short_description = f"{short_description}: {original_subject_hint[:90]}"

            description = (
                f"Kullanıcı {product} hizmetinde {subcategory_tr.lower()} ile ilgili BT destek talebi açtı. "
                f"Kategori: {category_tr}. Departman: {department}. Öncelik: {priority}. "
                f"Özgün İngilizce kayıt Türkçe proje veri seti için yapılandırılmış özet formatına dönüştürüldü."
            )

            resolution_hint = tr_phrase(row.get("resolution", ""))
            resolution = (
                f"Destek ekibi {product} üzerinde {subcategory_tr.lower()} için kontrol ve düzeltme adımlarını uyguladı."
            )
            if resolution_hint:
                resolution = f"{resolution} Özgün çözüm notu özeti: {resolution_hint[:240]}"

            rows.append(
                {
                    "ticket_id": row.get("ticket_id", "").strip(),
                    "created_at": row.get("created_date", "").strip(),
                    "category": category_tr,
                    "subcategory": subcategory_tr,
                    "short_description": short_description,
                    "description": description,
                    "resolution": resolution,
                    "channel": "external_english_tr",
                    "priority": priority,
                    "status": normalize_status(row.get("status", "")),
                    "source_language": "en",
                    "source_dataset": source_csv.name,
                }
            )

    fieldnames = [
        "ticket_id",
        "created_at",
        "category",
        "subcategory",
        "short_description",
        "description",
        "resolution",
        "channel",
        "priority",
        "status",
        "source_language",
        "source_dataset",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"created Turkish-normalized dataset: {output_csv.relative_to(ROOT)} ({len(rows)} rows)")
    return len(rows)


def iter_standard_ticket_rows(csv_path: Path, source_name: str) -> Iterable[dict[str, str]]:
    if not csv_path.exists():
        return []

    rows: list[dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            ticket_id = row.get("ticket_id") or row.get("id")
            short_description = row.get("short_description") or row.get("subject") or row.get("title") or ""
            description = row.get("description") or row.get("body") or row.get("text") or ""
            resolution = row.get("resolution") or row.get("answer") or ""
            if not ticket_id or not short_description:
                continue
            rows.append(
                {
                    "ticket_id": ticket_id.strip(),
                    "created_at": (row.get("created_at") or row.get("created_date") or "").strip(),
                    "category": (row.get("category") or row.get("queue") or "Genel").strip(),
                    "subcategory": (row.get("subcategory") or row.get("sub_category") or "").strip(),
                    "short_description": short_description.strip(),
                    "description": description.strip(),
                    "resolution": resolution.strip(),
                    "channel": (row.get("channel") or source_name).strip(),
                    "priority": normalize_priority(row.get("priority", "")),
                    "status": normalize_status(row.get("status", "")),
                    "source_dataset": source_name,
                }
            )

    return rows


def create_merged_outputs() -> tuple[int, int]:
    sources = [
        (DATA / "raw" / "tickets" / "sample_itsm_tickets.csv", "sample_itsm_tickets"),
        (
            DATA / "raw" / "tickets" / "synthetic" / "synthetic_itsm_tickets_2200.csv",
            "synthetic_itsm_tickets_2200",
        ),
        (DATA / "raw" / "tickets" / "converted" / "deepseek_tickets_20260607.csv", "deepseek_tickets_20260607"),
        (DATA / "processed" / "tickets" / "tickets_clean_tr.csv", "tickets_clean_tr"),
    ]

    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for csv_path, source_name in sources:
        for row in iter_standard_ticket_rows(csv_path, source_name):
            key = (row["ticket_id"], source_name)
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)

    merged_csv = DATA / "processed" / "tickets" / "merged_turkish_tickets.csv"
    merged_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticket_id",
        "created_at",
        "category",
        "subcategory",
        "short_description",
        "description",
        "resolution",
        "channel",
        "priority",
        "status",
        "source_dataset",
    ]
    with merged_csv.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)

    parquet_rows = []
    for row in merged:
        text = " ".join(
            part
            for part in [row["short_description"], row["description"], row["resolution"]]
            if part
        )
        parquet_rows.append(
            {
                "id": row["ticket_id"],
                "text": text,
                "resolution": row["resolution"],
                "category": row["category"],
                "priority": row["priority"],
                "language": "tr",
                "created_at": row["created_at"] or None,
                "source": row["source_dataset"],
            }
        )

    parquet_path = DATA / "processed" / "tickets.parquet"
    try:
        import pandas as pd

        frame = pd.DataFrame(parquet_rows)
        frame.to_parquet(parquet_path, index=False, engine="pyarrow")
        parquet_count = len(frame)
    except Exception as exc:
        parquet_count = 0
        print(f"warning: could not write parquet ({exc})")

    print(f"created merged ticket csv: {merged_csv.relative_to(ROOT)} ({len(merged)} rows)")
    if parquet_count:
        print(f"created processed parquet: {parquet_path.relative_to(ROOT)} ({parquet_count} rows)")

    return len(merged), parquet_count


def organize_known_files() -> None:
    for src, dst in MOVE_MAP.items():
        safe_move(src, dst)


def main() -> None:
    ensure_directories()

    deepseek_txt = DATA / "deepseek_tsv_20260607_7faf13.txt"
    gemini_txt = DATA / "gemini-code-1780821831396.txt"
    convert_deepseek_txt(deepseek_txt, DATA / "raw" / "tickets" / "converted" / "deepseek_tickets_20260607.csv")
    convert_gemini_txt(gemini_txt, DATA / "raw" / "kb" / "converted" / "gemini_kb_documents_20260607.csv")

    english_source_before_move = DATA / "tickets_clean.csv"
    english_source_after_move = DATA / "raw" / "tickets" / "external" / "english" / "tickets_clean.csv"
    english_source = english_source_before_move if english_source_before_move.exists() else english_source_after_move
    normalize_tickets_clean_english(english_source, DATA / "processed" / "tickets" / "tickets_clean_tr.csv")

    organize_known_files()
    create_merged_outputs()


if __name__ == "__main__":
    main()
