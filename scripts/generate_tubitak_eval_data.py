"""
Generate TÜBİTAK-oriented evaluation data for retrieval and anomaly checks.

The generated retrieval set separates ticket-specific exact-ID queries from
generic support queries. Generic queries use category/subcategory relevance
instead of pretending that a broad user question has one exact ticket answer.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TICKETS = PROJECT_ROOT / "data" / "processed" / "tickets.parquet"
DEFAULT_RETRIEVAL_OUTPUT = (
    PROJECT_ROOT / "data" / "evaluation" / "retrieval" / "retrieval_eval_queries.csv"
)
DEFAULT_SYNTHETIC_ANOMALY = (
    PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "synthetic_bt_anomaly_dataset_codex.csv"
)
DEFAULT_ANOMALY_METRICS = (
    PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "anomaly_metrics.json"
)
DEFAULT_ANOMALY_OUTPUT = (
    PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "anomaly_ground_truth.csv"
)

TARGET_CATEGORIES = [
    "Ağ",
    "E-posta",
    "Güvenlik",
    "Kimlik & Erişim",
    "Teams",
    "Yazıcı",
    "Donanım",
    "Uygulama",
]

SCENARIO_TEMPLATES = {
    ("Ağ", "VPN"): [
        "VPN bağlantısı kopuyor ve FortiClient hata veriyor",
        "uzaktan erişim için VPN bağlantı problemi var",
        "VPN oturumu açılmıyor kullanıcı bağlantı hatası alıyor",
    ],
    ("Ağ", "WiFi"): [
        "WiFi bağlantısı kopuyor kablosuz ağ erişimi yok",
        "kablosuz ağ yavaş ve kullanıcı internete çıkamıyor",
    ],
    ("E-posta", "Outlook"): [
        "Outlook açılmıyor profil hatası alıyorum",
        "Outlook posta kutusu senkronize olmuyor",
        "Outlook hesabı giriş ve gönder al problemi",
    ],
    ("E-posta", "Exchange"): [
        "Exchange posta akışı kesintisi ve mail gecikmesi",
        "Exchange kullanıcıları e-posta gönderemiyor",
    ],
    ("Kimlik & Erişim", "MFA"): [
        "MFA push bildirimi gelmiyor kullanıcı giriş yapamıyor",
        "çok faktörlü doğrulama token hatası var",
        "conditional access nedeniyle MFA doğrulaması başarısız",
    ],
    ("Kimlik & Erişim", "Parola"): [
        "toplu parola sıfırlama sonrası kullanıcılar giriş yapamıyor",
        "şifre yenileme bağlantısı çalışmıyor parola problemi",
    ],
    ("Güvenlik", "Phishing"): [
        "şüpheli e-posta geldi phishing incelemesi gerekiyor",
        "oltalama bildirimi ve zararlı bağlantı şüphesi",
    ],
    ("Güvenlik", "Ransomware"): [
        "ransomware belirtisi şifrelenmiş dosya ve uzantı değişimi",
        "fidye yazılımı şüphesi dosya erişimi bozuldu",
    ],
    ("Teams", "Ses/Görüntü"): [
        "Teams mikrofon çalışmıyor toplantıda ses gitmiyor",
        "Teams görüntü ve kamera problemi yaşıyorum",
    ],
    ("Yazıcı", "Network Printer"): [
        "network printer çevrimdışı görünüyor yazıcıya erişilemiyor",
        "yazıcı kuyruğu takılıyor çıktı alınamıyor",
    ],
    ("Donanım", "Laptop"): [
        "laptop açılmıyor güç ve batarya problemi var",
        "kurumsal laptop çok yavaş çalışıyor donanım kontrolü",
    ],
    ("Uygulama", "ERP"): [
        "ERP raporu çalışmıyor uygulama hata veriyor",
        "ERP ekranında yetki ve raporlama problemi var",
    ],
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return " ".join(str(value).split())


def trim_words(text: str, max_words: int) -> str:
    words = clean_text(text).split()
    return " ".join(words[:max_words])


def first_sentence(text: str, max_words: int = 18) -> str:
    text = clean_text(text)
    if not text:
        return ""
    sentence = re.split(r"[.!?]", text)[0]
    return trim_words(sentence, max_words)


def load_target_tickets(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    required = {
        "ticket_id",
        "category",
        "subcategory",
        "short_description",
        "description",
        "resolution",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"tickets.parquet missing columns: {sorted(missing)}")

    frame = frame.copy()
    frame = frame[frame["category"].isin(TARGET_CATEGORIES)].copy()
    frame["short_description"] = frame["short_description"].map(clean_text)
    frame["description"] = frame["description"].map(clean_text)
    frame["resolution"] = frame["resolution"].map(clean_text)
    frame = frame[
        frame["ticket_id"].map(clean_text).ne("")
        & frame["short_description"].ne("")
        & frame["description"].ne("")
        & frame["resolution"].ne("")
    ].copy()

    fingerprint = (
        frame["short_description"].str.casefold()
        + " "
        + frame["description"].str.casefold()
        + " "
        + frame["resolution"].str.casefold()
    )
    unique_fingerprint = fingerprint.map(fingerprint.value_counts()).eq(1)
    return frame[unique_fingerprint].reset_index(drop=True)


def make_exact_query(row: pd.Series) -> str:
    title = clean_text(row.get("short_description"))
    description = first_sentence(row.get("description"), max_words=18)
    resolution_hint = trim_words(row.get("resolution"), 10)
    parts = [
        title,
        description,
        f"çözüm notunda {resolution_hint} geçen kayıt",
    ]
    return " ".join(part for part in parts if part)


def generate_exact_queries(frame: pd.DataFrame, count: int, seed: int) -> list[dict[str, Any]]:
    rows: list[pd.Series] = []
    per_category = max(4, count // max(len(TARGET_CATEGORIES), 1))

    for _, group in frame.groupby("category", sort=True):
        sample_count = min(per_category, len(group))
        rows.extend(group.sample(n=sample_count, random_state=seed).itertuples(index=False))

    if len(rows) < count:
        selected_ids = {getattr(row, "ticket_id") for row in rows}
        remainder = frame[~frame["ticket_id"].isin(selected_ids)]
        if not remainder.empty:
            rows.extend(
                remainder.sample(
                    n=min(count - len(rows), len(remainder)),
                    random_state=seed + 17,
                ).itertuples(index=False)
            )

    queries: list[dict[str, Any]] = []
    for row in rows[:count]:
        series = pd.Series(row._asdict())
        queries.append(
            {
                "query": make_exact_query(series),
                "expected_category": clean_text(series.get("category")),
                "expected_subcategory": clean_text(series.get("subcategory")),
                "relevant_doc_ids": clean_text(series.get("ticket_id")),
                "query_type": "exact_ticket",
                "relevance_strategy": "doc_ids",
            }
        )

    return queries


def generic_templates_for(category: str, subcategory: str) -> list[str]:
    templates = SCENARIO_TEMPLATES.get((category, subcategory))
    if not templates:
        return []

    return templates + [
        f"{subcategory} problemi yaşayan kullanıcı için geçmiş çözüm kaydı",
        f"{category} kategorisinde {subcategory} arızası nasıl çözülür",
        f"{subcategory} ile ilgili kurumsal BT destek talebi",
        f"{subcategory} kesintisi için benzer destek kayıtları",
        f"{category} {subcategory} sorunu için uygulanmış çözüm örnekleri",
    ]


def generate_generic_queries(frame: pd.DataFrame, count: int) -> list[dict[str, Any]]:
    group_counts = (
        frame.groupby(["category", "subcategory"])
        .size()
        .sort_values(ascending=False)
        .reset_index(name="count")
    )
    scenario_keys = set(SCENARIO_TEMPLATES)
    group_counts = group_counts[
        group_counts["count"].ge(5)
        & group_counts.apply(
            lambda row: (clean_text(row["category"]), clean_text(row["subcategory"])) in scenario_keys,
            axis=1,
        )
    ].copy()

    queries: list[dict[str, Any]] = []
    seen_queries: set[str] = set()
    cursor = 0
    while len(queries) < count and not group_counts.empty:
        group = group_counts.iloc[cursor % len(group_counts)]
        category = clean_text(group["category"])
        subcategory = clean_text(group["subcategory"])

        for template in generic_templates_for(category, subcategory):
            query = clean_text(template)
            if query.casefold() in seen_queries:
                continue
            seen_queries.add(query.casefold())
            queries.append(
                {
                    "query": query,
                    "expected_category": category,
                    "expected_subcategory": subcategory,
                    "relevant_doc_ids": "",
                    "query_type": "generic_category_subcategory",
                    "relevance_strategy": "category_subcategory",
                }
            )
            if len(queries) >= count:
                break
        cursor += 1
        if cursor > len(group_counts) * 4:
            break

    return queries


def generate_retrieval_eval_queries(
    tickets_path: Path = DEFAULT_TICKETS,
    output_path: Path = DEFAULT_RETRIEVAL_OUTPUT,
    exact_count: int = 100,
    generic_count: int = 80,
    seed: int = 42,
) -> dict[str, Any]:
    frame = load_target_tickets(tickets_path)
    exact_queries = generate_exact_queries(frame, exact_count, seed)
    generic_queries = generate_generic_queries(frame, generic_count)
    rows = exact_queries + generic_queries

    for index, row in enumerate(rows, start=1):
        row["query_id"] = f"Q-{index:03d}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "query_id",
        "query",
        "expected_category",
        "expected_subcategory",
        "relevant_doc_ids",
        "query_type",
        "relevance_strategy",
    ]
    pd.DataFrame(rows, columns=columns).to_csv(output_path, index=False, encoding="utf-8")

    return {
        "output": str(output_path),
        "source_tickets": str(tickets_path),
        "available_target_tickets": int(len(frame)),
        "exact_queries": int(len(exact_queries)),
        "generic_queries": int(len(generic_queries)),
        "total_queries": int(len(rows)),
        "unique_query_texts": int(pd.Series([row["query"].casefold() for row in rows]).nunique()),
    }


def normalize_anomaly_type(value: str, category: str) -> str:
    base = clean_text(value).casefold().replace(" ", "_").replace("-", "_")
    category_slug = re.sub(r"[^a-z0-9ğüşöçıİĞÜŞÖÇ]+", "_", clean_text(category).casefold()).strip("_")
    return f"{base}_{category_slug}" if category_slug else base


def generate_anomaly_silver_labels(
    synthetic_path: Path = DEFAULT_SYNTHETIC_ANOMALY,
    metrics_path: Path = DEFAULT_ANOMALY_METRICS,
    output_path: Path = DEFAULT_ANOMALY_OUTPUT,
) -> dict[str, Any]:
    """
    Generate diagnostic silver labels from engine-detected windows.

    This is intentionally not used by default because it is circular for formal
    anomaly evaluation: labels are derived from the same engine output being
    evaluated. Use only for exploratory timeline annotation.
    """
    synthetic = pd.read_csv(synthetic_path)
    synthetic["date"] = pd.to_datetime(synthetic["date"], errors="coerce").dt.date

    if not metrics_path.exists():
        raise FileNotFoundError(
            f"Existing anomaly metrics not found: {metrics_path}. Run scripts/evaluate_anomaly.py first."
        )
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    detected_events = metrics.get("detected_events", [])

    rows: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for event in detected_events:
        start = datetime.fromisoformat(event["window_start"])
        date_key = start.date().isoformat()
        if date_key in seen_dates:
            continue
        matching = synthetic[synthetic["date"].astype(str).eq(date_key)]
        if matching.empty:
            continue
        scenario = matching.iloc[0]
        seen_dates.add(date_key)
        rows.append(
            {
                "window_start": f"{date_key} 00:00:00",
                "window_end": f"{date_key} 23:59:59",
                "anomaly_type": normalize_anomaly_type(
                    clean_text(scenario.get("anomaly_type")),
                    clean_text(scenario.get("category")),
                ),
                "expected_severity": clean_text(scenario.get("severity")) or clean_text(event.get("severity")),
                "description": clean_text(scenario.get("explanation")),
                "source": "diagnostic_silver_label_from_detected_ticket_stream_window",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        rows,
        columns=[
            "window_start",
            "window_end",
            "anomaly_type",
            "expected_severity",
            "description",
            "source",
        ],
    ).to_csv(output_path, index=False, encoding="utf-8")

    return {
        "output": str(output_path),
        "source_synthetic": str(synthetic_path),
        "source_metrics": str(metrics_path),
        "silver_label_events": int(len(rows)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TÜBİTAK-oriented evaluation data.")
    parser.add_argument("--tickets", type=Path, default=DEFAULT_TICKETS)
    parser.add_argument("--retrieval-output", type=Path, default=DEFAULT_RETRIEVAL_OUTPUT)
    parser.add_argument("--synthetic-anomaly", type=Path, default=DEFAULT_SYNTHETIC_ANOMALY)
    parser.add_argument("--anomaly-metrics", type=Path, default=DEFAULT_ANOMALY_METRICS)
    parser.add_argument("--anomaly-output", type=Path, default=DEFAULT_ANOMALY_OUTPUT)
    parser.add_argument("--exact-count", type=int, default=100)
    parser.add_argument("--generic-count", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--generate-anomaly-silver-labels",
        action="store_true",
        help=(
            "Generate diagnostic anomaly silver labels from detected windows. "
            "Do not use this for formal precision/recall reporting."
        ),
    )
    args = parser.parse_args()

    retrieval_summary = generate_retrieval_eval_queries(
        tickets_path=args.tickets,
        output_path=args.retrieval_output,
        exact_count=args.exact_count,
        generic_count=args.generic_count,
        seed=args.seed,
    )
    print("Retrieval eval data generated.")
    print(json.dumps(retrieval_summary, ensure_ascii=False, indent=2))

    if args.generate_anomaly_silver_labels:
        anomaly_summary = generate_anomaly_silver_labels(
            synthetic_path=args.synthetic_anomaly,
            metrics_path=args.anomaly_metrics,
            output_path=args.anomaly_output,
        )
        print("Diagnostic anomaly silver labels generated.")
        print(json.dumps(anomaly_summary, ensure_ascii=False, indent=2))
    else:
        print("Anomaly ground truth was not generated. Existing curated labels were left unchanged.")


if __name__ == "__main__":
    main()
