"""
Generate an independent anomaly validation stream with day-level labels.

The generated files are evaluation artifacts only. They do not modify
data/processed/tickets.parquet or the retrieval indexes.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "anomaly"
DEFAULT_TICKETS_OUTPUT = DEFAULT_OUTPUT_DIR / "anomaly_validation_tickets.parquet"
DEFAULT_TICKETS_CSV_OUTPUT = DEFAULT_OUTPUT_DIR / "anomaly_validation_tickets.csv"
DEFAULT_GT_OUTPUT = DEFAULT_OUTPUT_DIR / "anomaly_validation_ground_truth.csv"
DEFAULT_DAY_LABELS_OUTPUT = DEFAULT_OUTPUT_DIR / "anomaly_day_labels.csv"
DEFAULT_SUMMARY_OUTPUT = DEFAULT_OUTPUT_DIR / "anomaly_validation_summary.json"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

NORMAL_SCENARIOS = [
    {
        "category": "Ağ",
        "subcategory": "VPN",
        "short": "VPN bağlantı kontrolü",
        "description": "Kullanıcı VPN bağlantısında aralıklı yavaşlık bildirdi. Standart profil ve MFA doğrulaması kontrol edildi.",
        "resolution": "VPN profili yenilendi, bağlantı testi tamamlandı.",
    },
    {
        "category": "E-posta",
        "subcategory": "Outlook",
        "short": "Outlook senkronizasyon sorunu",
        "description": "Kullanıcı Outlook istemcisinde gönder-al gecikmesi yaşadığını belirtti.",
        "resolution": "Outlook profili ve önbellek ayarları kontrol edildi.",
    },
    {
        "category": "Kimlik & Erişim",
        "subcategory": "Parola",
        "short": "Parola sıfırlama talebi",
        "description": "Kullanıcı self servis parola yenileme adımlarında destek istedi.",
        "resolution": "Parola sıfırlama bağlantısı iletildi ve hesap durumu doğrulandı.",
    },
    {
        "category": "Donanım",
        "subcategory": "Laptop",
        "short": "Laptop performans sorunu",
        "description": "Kurumsal laptop açılışta yavaşlıyor ve disk kullanımı yüksek görünüyor.",
        "resolution": "Disk alanı, başlangıç uygulamaları ve güncelleme durumu kontrol edildi.",
    },
    {
        "category": "Yazıcı",
        "subcategory": "Network Printer",
        "short": "Yazıcı bağlantı sorunu",
        "description": "Departman yazıcısı bazı kullanıcılarda çevrimdışı görünüyor.",
        "resolution": "Yazıcı kuyruğu temizlendi ve ağ bağlantısı doğrulandı.",
    },
    {
        "category": "Teams",
        "subcategory": "Ses/Görüntü",
        "short": "Teams ses problemi",
        "description": "Toplantı sırasında mikrofon seçimi hatalı olduğu için ses gitmedi.",
        "resolution": "Teams cihaz ayarları güncellendi ve test görüşmesi yapıldı.",
    },
]

ANOMALY_SCENARIOS = {
    "volume_spike": [
        {
            "category": "Ağ",
            "subcategory": "VPN",
            "short": "VPN bağlantısı toplu olarak kesiliyor",
            "description": "FortiClient oturumları aynı saat aralığında düşüyor, uzaktan çalışan kullanıcılar şirket ağına erişemiyor.",
            "resolution": "VPN gateway kapasitesi, sertifika durumu ve eş zamanlı oturum limiti kontrol edildi.",
            "severity": "critical",
        },
        {
            "category": "E-posta",
            "subcategory": "Exchange",
            "short": "Exchange posta akışı kesintisi",
            "description": "Çok sayıda kullanıcı mail gönderememe, takvim gecikmesi ve ortak posta kutusu erişim sorunu bildiriyor.",
            "resolution": "Exchange transport queue, connector ve servis sağlık durumu incelendi.",
            "severity": "critical",
        },
    ],
    "category_shift": [
        {
            "category": "Kimlik & Erişim",
            "subcategory": "MFA",
            "short": "MFA doğrulama talepleri yoğunlaştı",
            "description": "Authenticator push bildirimi gelmiyor, token kodları kabul edilmiyor ve Conditional Access kararları başarısız oluyor.",
            "resolution": "MFA servis durumu, kullanıcı kayıtları ve riskli oturum logları incelendi.",
            "severity": "warning",
        },
        {
            "category": "Uygulama",
            "subcategory": "ERP",
            "short": "ERP ekranlarında toplu hata",
            "description": "ERP sipariş, stok ve fatura ekranlarında aynı anda hata oluşuyor; kullanıcılar iş akışını tamamlayamıyor.",
            "resolution": "ERP uygulama logları, entegrasyon kuyruğu ve yetki grupları kontrol edildi.",
            "severity": "warning",
        },
    ],
    "semantic_drift": [
        {
            "category": "Güvenlik",
            "subcategory": "Ransomware",
            "short": "Ransomware belirtisi şüphesi",
            "description": "Kullanıcılar şifrelenmiş dosya, fidye notu, uzantı değişimi ve paylaşımlı klasör erişim hatası bildiriyor.",
            "resolution": "EDR izolasyonu, IOC taraması, yedek kontrolü ve olay müdahale prosedürü başlatıldı.",
            "severity": "critical",
        },
        {
            "category": "Kimlik & Erişim",
            "subcategory": "MFA",
            "short": "MFA saldırısı belirtisi",
            "description": "Kullanıcılar kendilerinin başlatmadığı MFA push yağmuru, imkansız konum ve şüpheli oturum bildirimleri iletiyor.",
            "resolution": "Riskli oturumlar sonlandırıldı, MFA cihazları yenilendi ve parola sıfırlama uygulandı.",
            "severity": "critical",
        },
    ],
    "combined_anomaly": [
        {
            "category": "Kimlik & Erişim",
            "subcategory": "Parola",
            "short": "Toplu parola sıfırlama dalgası",
            "description": "Parola politikası değişikliği sonrası hesap kilidi, SSO giriş hatası ve VPN erişim sorunu aynı anda arttı.",
            "resolution": "AD hesap kilitleri, SSO metadata ve parola reset kuyruğu birlikte incelendi.",
            "severity": "critical",
        },
        {
            "category": "Güvenlik",
            "subcategory": "Ransomware",
            "short": "Güvenlik olayı ve hacim artışı",
            "description": "Ticket hacmi yükselirken açıklamalarda ransomware, EDR izolasyonu, fidye notu ve dosya kurtarma ifadeleri baskınlaştı.",
            "resolution": "SOC eskalasyonu yapıldı, etkilenen uç noktalar izole edildi ve yedeklerden geri dönüş planlandı.",
            "severity": "critical",
        },
    ],
}


def build_positive_schedule(start_date: datetime, event_count: int) -> dict[datetime, dict[str, Any]]:
    anomaly_types = list(ANOMALY_SCENARIOS)
    schedule: dict[datetime, dict[str, Any]] = {}
    current_date = start_date

    for index in range(event_count):
        anomaly_type = anomaly_types[index % len(anomaly_types)]
        scenario = ANOMALY_SCENARIOS[anomaly_type][
            (index // len(anomaly_types)) % len(ANOMALY_SCENARIOS[anomaly_type])
        ]
        schedule[current_date] = {
            "event_id": f"ANOM-{index + 1:03d}",
            "anomaly_type": anomaly_type,
            **scenario,
        }
        current_date += timedelta(days=3 + (index % 3))

    return schedule


def random_time_on_day(day: datetime, rng: random.Random, ticket_index: int) -> datetime:
    minute = (ticket_index * 17 + rng.randint(0, 120)) % (24 * 60)
    return day + timedelta(minutes=minute)


def make_ticket(
    ticket_id: str,
    created_at: datetime,
    category: str,
    subcategory: str,
    short_description: str,
    description: str,
    resolution: str,
    priority: str,
) -> dict[str, Any]:
    text = f"{short_description}. {description} Çözüm: {resolution}"
    return {
        "id": ticket_id,
        "text": text,
        "ticket_id": ticket_id,
        "created_at": created_at,
        "category": category,
        "subcategory": subcategory,
        "short_description": short_description,
        "description": description,
        "resolution": resolution,
        "priority": priority,
        "status": "resolved",
        "source": "anomaly_validation_synthetic",
        "is_synthetic": True,
        "language": "tr",
        "source_type": "anomaly_validation",
    }


def generate_tickets_and_labels(
    start_date: datetime,
    days: int,
    event_count: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = random.Random(seed)
    positive_schedule = build_positive_schedule(start_date + timedelta(days=35), event_count)
    rows: list[dict[str, Any]] = []
    gt_rows: list[dict[str, Any]] = []
    day_label_rows: list[dict[str, Any]] = []
    ticket_counter = 1

    for day_offset in range(days):
        day = start_date + timedelta(days=day_offset)
        scenario = positive_schedule.get(day)

        if scenario:
            anomaly_type = scenario["anomaly_type"]
            if anomaly_type == "volume_spike":
                ticket_count = rng.randint(48, 62)
                dominant_ratio = 0.60
            elif anomaly_type == "category_shift":
                ticket_count = rng.randint(24, 32)
                dominant_ratio = 0.82
            elif anomaly_type == "semantic_drift":
                ticket_count = rng.randint(16, 22)
                dominant_ratio = 0.55
            else:
                ticket_count = rng.randint(55, 72)
                dominant_ratio = 0.88

            expected_severity = scenario["severity"]
            gt_rows.append(
                {
                    "event_id": scenario["event_id"],
                    "window_start": f"{day.date().isoformat()} 00:00:00",
                    "window_end": f"{day.date().isoformat()} 23:59:59",
                    "anomaly_type": anomaly_type,
                    "expected_severity": expected_severity,
                    "description": scenario["description"],
                    "source": "independent_synthetic_validation",
                }
            )
            day_label_rows.append(
                {
                    "date": day.date().isoformat(),
                    "is_anomaly": True,
                    "event_id": scenario["event_id"],
                    "anomaly_type": anomaly_type,
                    "expected_severity": expected_severity,
                    "expected_category": scenario["category"],
                    "expected_subcategory": scenario["subcategory"],
                    "label_source": "independent_synthetic_validation",
                }
            )
        else:
            ticket_count = rng.randint(8, 14)
            dominant_ratio = 0.0
            day_label_rows.append(
                {
                    "date": day.date().isoformat(),
                    "is_anomaly": False,
                    "event_id": "",
                    "anomaly_type": "normal",
                    "expected_severity": "normal",
                    "expected_category": "",
                    "expected_subcategory": "",
                    "label_source": "independent_synthetic_validation",
                }
            )

        dominant_count = int(round(ticket_count * dominant_ratio)) if scenario else 0
        for index in range(ticket_count):
            if scenario and index < dominant_count:
                template = scenario
                priority = "critical" if scenario["severity"] == "critical" else "high"
            else:
                template = rng.choice(NORMAL_SCENARIOS)
                priority = rng.choice(["low", "medium", "medium", "high"])

            ticket_id = f"AVT-{ticket_counter:06d}"
            created_at = random_time_on_day(day, rng, index)
            rows.append(
                make_ticket(
                    ticket_id=ticket_id,
                    created_at=created_at,
                    category=template["category"],
                    subcategory=template["subcategory"],
                    short_description=template["short"],
                    description=template["description"],
                    resolution=template["resolution"],
                    priority=priority,
                )
            )
            ticket_counter += 1

    tickets = pd.DataFrame(rows)
    ground_truth = pd.DataFrame(gt_rows)
    day_labels = pd.DataFrame(day_label_rows)
    return tickets, ground_truth, day_labels


def attach_embeddings(frame: pd.DataFrame, model_name: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("sentence-transformers is required to generate validation embeddings") from exc

    model = SentenceTransformer(model_name, local_files_only=True)
    texts = frame["text"].astype(str).tolist()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    frame = frame.copy()
    frame["embedding"] = [np.asarray(vector, dtype=np.float32).tolist() for vector in embeddings]
    return frame, {
        "embedding_model": model_name,
        "embedding_dim": int(embeddings.shape[1]) if len(embeddings.shape) == 2 else None,
        "embedded_rows": int(len(frame)),
    }


def generate_validation_data(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    days: int = 190,
    event_count: int = 40,
    start_date: datetime = datetime(2026, 1, 1),
    seed: int = 20260610,
    embedding_model: str = EMBEDDING_MODEL,
) -> dict[str, Any]:
    tickets, ground_truth, day_labels = generate_tickets_and_labels(
        start_date=start_date,
        days=days,
        event_count=event_count,
        seed=seed,
    )
    tickets, embedding_summary = attach_embeddings(tickets, embedding_model)

    output_dir.mkdir(parents=True, exist_ok=True)
    tickets_path = output_dir / DEFAULT_TICKETS_OUTPUT.name
    tickets_csv_path = output_dir / DEFAULT_TICKETS_CSV_OUTPUT.name
    ground_truth_path = output_dir / DEFAULT_GT_OUTPUT.name
    day_labels_path = output_dir / DEFAULT_DAY_LABELS_OUTPUT.name
    summary_path = output_dir / DEFAULT_SUMMARY_OUTPUT.name

    tickets.to_parquet(tickets_path, index=False)
    tickets.drop(columns=["embedding"]).to_csv(tickets_csv_path, index=False, encoding="utf-8")
    ground_truth.to_csv(ground_truth_path, index=False, encoding="utf-8")
    day_labels.to_csv(day_labels_path, index=False, encoding="utf-8")

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tickets": str(tickets_path),
        "tickets_csv": str(tickets_csv_path),
        "ground_truth": str(ground_truth_path),
        "day_labels": str(day_labels_path),
        "days": int(days),
        "positive_event_days": int(len(ground_truth)),
        "negative_days": int((~day_labels["is_anomaly"].astype(bool)).sum()),
        "tickets_generated": int(len(tickets)),
        "anomaly_type_distribution": ground_truth["anomaly_type"].value_counts().to_dict(),
        "severity_distribution": ground_truth["expected_severity"].value_counts().to_dict(),
        **embedding_summary,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate independent anomaly validation data.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--days", type=int, default=190)
    parser.add_argument("--event-count", type=int, default=40)
    parser.add_argument("--start-date", type=str, default="2026-01-01")
    parser.add_argument("--seed", type=int, default=20260610)
    parser.add_argument("--embedding-model", type=str, default=EMBEDDING_MODEL)
    args = parser.parse_args()

    start_date = datetime.fromisoformat(args.start_date)
    summary = generate_validation_data(
        output_dir=args.output_dir,
        days=args.days,
        event_count=args.event_count,
        start_date=start_date,
        seed=args.seed,
        embedding_model=args.embedding_model,
    )
    print("Anomaly validation data generated.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
