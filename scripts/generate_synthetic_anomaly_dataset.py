"""
Generate synthetic anomaly evaluation data for BT support ticket monitoring.

The output is daily/category-level data, not individual tickets. Each row
represents an anomalous support window with:
date, category, ticket_count, anomaly_type, severity, explanation
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable


OUTPUT_PATH = Path("data/evaluation/anomaly/synthetic_bt_anomaly_dataset.csv")
RANDOM_SEED = 20260606
RECORDS_PER_TYPE = 120


ANOMALY_TYPES = (
    "Volume Spike",
    "Category Shift",
    "Semantic Drift",
    "Combined Anomaly",
)


@dataclass(frozen=True)
class Scenario:
    category: str
    low: int
    high: int
    severity_hint: str
    explanations: tuple[str, ...]


def severity_from_count(ticket_count: int, anomaly_type: str, hint: str) -> str:
    if anomaly_type == "Combined Anomaly":
        if ticket_count >= 420:
            return "critical"
        if ticket_count >= 240:
            return "warning"
        return hint

    if anomaly_type == "Volume Spike":
        if ticket_count >= 360:
            return "critical"
        if ticket_count >= 160:
            return "warning"
        return hint

    if anomaly_type == "Semantic Drift":
        if any(word in hint for word in ("critical", "warning")):
            return hint
        if ticket_count >= 90:
            return "warning"
        return "info"

    if anomaly_type == "Category Shift":
        if ticket_count >= 180:
            return "warning"
        return hint

    return hint


def make_record(
    record_date: date,
    anomaly_type: str,
    scenario: Scenario,
    explanation_suffix: str,
) -> dict[str, str | int]:
    ticket_count = random.randint(scenario.low, scenario.high)
    severity = severity_from_count(ticket_count, anomaly_type, scenario.severity_hint)
    explanation = random.choice(scenario.explanations)
    return {
        "date": record_date.isoformat(),
        "category": scenario.category,
        "ticket_count": ticket_count,
        "anomaly_type": anomaly_type,
        "severity": severity,
        "explanation": f"{explanation} {explanation_suffix}",
    }


def rotate_date(start: date, index: int) -> date:
    return start + timedelta(days=index)


def build_volume_spike_scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            "VPN",
            160,
            520,
            "warning",
            (
                "FortiClient ve SSL VPN bağlantılarında aynı saat diliminde yoğun kopma bildirimi oluştu.",
                "Uzaktan çalışan kullanıcılar VPN tünelinin kurulamadığını ve oturumun sürekli düştüğünü bildirdi.",
                "VPN gateway üzerinde lisans ve eş zamanlı oturum limitine yaklaşılması destek kayıtlarını artırdı.",
            ),
        ),
        Scenario(
            "Exchange",
            120,
            430,
            "warning",
            (
                "Exchange posta kutularında gönder-al gecikmesi ve Outlook çevrimdışı kalma bildirimleri hızla arttı.",
                "Transport queue birikmesi nedeniyle mail gönderememe kayıtlarında olağan dışı yükseliş görüldü.",
                "Kullanıcılar takvim davetlerinin iletilmediğini ve ortak posta kutularına erişemediğini bildirdi.",
            ),
        ),
        Scenario(
            "Identity & Access",
            180,
            650,
            "warning",
            (
                "Toplu parola süresi dolumu nedeniyle self-service reset ve hesap kilidi kayıtları kısa sürede yükseldi.",
                "Active Directory hesap kilitlenmeleri ve başarısız oturum açma kayıtları normal hacmin üstüne çıktı.",
                "Parola politikası değişikliği sonrası kullanıcılar VPN, mail ve ERP sistemlerine giriş yapamadı.",
            ),
        ),
        Scenario(
            "Security",
            90,
            360,
            "warning",
            (
                "EDR uyarıları ve şüpheli dosya çalıştırma bildirimleri destek kuyruğunda ani yoğunluk oluşturdu.",
                "Güvenlik operasyon merkezi aynı anda çok sayıda endpoint izolasyon talebi açtı.",
                "Kullanıcılar güvenlik uyarısı, tarayıcı yönlendirmesi ve bilinmeyen uygulama pop-up kayıtları oluşturdu.",
            ),
        ),
        Scenario(
            "MFA",
            140,
            540,
            "warning",
            (
                "MFA doğrulama ekranı gelmeme ve push bildirimi onaylanmama kayıtları olağan dışı arttı.",
                "Authenticator uygulaması eşleşme hataları ve QR kod yenileme talepleri yoğunlaştı.",
                "Çok faktörlü doğrulama servisindeki gecikme nedeniyle kullanıcılar kritik uygulamalara erişemedi.",
            ),
        ),
        Scenario(
            "Endpoint",
            100,
            300,
            "warning",
            (
                "Windows güncellemesi sonrası mavi ekran, yavaş açılış ve disk şifreleme hataları aynı gün yoğunlaştı.",
                "Kurumsal antivirüs ajanı güncellemesi sonrasında cihaz performans şikayetleri arttı.",
                "Endpoint yönetim ajanı servisinin durması nedeniyle yazılım dağıtım kayıtlarında ani yükseliş oluştu.",
            ),
        ),
    )


def build_category_shift_scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            "MFA",
            45,
            210,
            "info",
            (
                "Normalde parola sıfırlama ağırlıklı olan kimlik kuyruğu MFA push reddi ve yeniden kayıt taleplerine kaydı.",
                "Kullanıcı erişim kayıtlarında kategori dağılımı hesap kilidi yerine MFA cihaz eşleştirme sorunlarına döndü.",
                "Yeni koşullu erişim kuralı sonrası destek talebi kompozisyonu MFA doğrulama hatalarına yoğunlaştı.",
            ),
        ),
        Scenario(
            "Ransomware Suspected",
            20,
            130,
            "warning",
            (
                "Genel dosya erişim talepleri kısa sürede şifrelenmiş dosya, uzantı değişimi ve kurtarma isteği kategorisine kaydı.",
                "Paylaşımlı klasör erişim kayıtlarında ransomware belirtisi taşıyan dosya adı değişiklikleri öne çıktı.",
                "Kullanıcı açıklamaları normal depolama sorunlarından fidye notu ve dosya açılamama bildirimlerine döndü.",
            ),
        ),
        Scenario(
            "Exchange",
            60,
            240,
            "info",
            (
                "Genel Office talepleri Exchange posta akışı ve Outlook bağlantı sorunlarına belirgin şekilde kaydı.",
                "Mail kategorisi içinde takvim, ortak posta kutusu ve transport queue sorunları normal dağılımı bozdu.",
                "Servis masası kayıtlarında yazıcı ve donanım payı düşerken Exchange kesintisi kaynaklı kayıtlar yükseldi.",
            ),
        ),
        Scenario(
            "VPN",
            70,
            260,
            "info",
            (
                "Ağ kategorisi içinde Wi-Fi talepleri azalırken VPN sertifika ve tünel hataları baskın kategori haline geldi.",
                "Uzaktan erişim kategorisi günlük kayıtların çoğunu oluşturarak olağan hizmet dağılımından saptı.",
                "Firewall değişikliği sonrası destek kayıtları genel bağlantıdan VPN policy ve split tunnel başlıklarına kaydı.",
            ),
        ),
        Scenario(
            "Security",
            35,
            180,
            "info",
            (
                "Kullanıcı destek kayıtlarında normal uygulama hataları azalırken phishing, zararlı ek ve EDR uyarıları arttı.",
                "Güvenlik kategorisi ilk kez günlük kuyruğun baskın sınıfı oldu ve servis masası dağılımını değiştirdi.",
                "SOC kaynaklı inceleme talepleri, standart BT destek kayıtlarını kategori ağırlığı açısından geride bıraktı.",
            ),
        ),
        Scenario(
            "Password Reset",
            80,
            300,
            "info",
            (
                "Kimlik taleplerinin dağılımı yetki onayından toplu parola reset ve hesap kilidi kaldırma işlemlerine kaydı.",
                "Kampüs genelinde parola süresi dolumu sonrası kayıt kompozisyonu reset ve ilk giriş sorunlarına döndü.",
                "SSO policy değişikliği kategori dağılımını oturum açma ve parola yenileme kayıtları yönüne çevirdi.",
            ),
        ),
    )


def build_semantic_drift_scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            "Security",
            25,
            120,
            "warning",
            (
                "Açıklamalarda 'dosyalar .locked oldu', 'fidye notu çıktı' ve 'paylaşım klasörü açılamıyor' ifadeleri belirmeye başladı.",
                "Kullanıcı metinlerinde normal antivirüs uyarılarından farklı olarak şifreleme, gölge kopya silinmesi ve kurtarma kelimeleri arttı.",
                "Ticket içerikleri olağan zararlı yazılım temizliğinden ransomware belirtisi taşıyan semantik kümeye kaydı.",
            ),
        ),
        Scenario(
            "MFA",
            30,
            140,
            "warning",
            (
                "Kayıt metinlerinde 'arka arkaya onay bildirimi geliyor' ve 'ben giriş yapmadım' ifadeleri yoğunlaşmaya başladı.",
                "MFA açıklamaları cihaz değişimi yerine MFA fatigue, push bombing ve imkansız yolculuk uyarılarına kaydı.",
                "Kullanıcı beyanları normal doğrulama hatasından şüpheli MFA onay isteği semantiğine dönüştü.",
            ),
        ),
        Scenario(
            "Exchange",
            20,
            110,
            "info",
            (
                "Mail kayıtlarında 'NDR', 'transport queue', 'hybrid connector' ve 'delayed delivery' ifadeleri ilk kez baskınlaştı.",
                "Outlook kullanım sorunları yerine posta akışı, relay ve Exchange Online kesintisi anlam alanı öne çıktı.",
                "Kayıt açıklamaları istemci profilinden tenant seviyesinde mail akışı bozulmasına doğru semantik kayma gösterdi.",
            ),
        ),
        Scenario(
            "VPN",
            25,
            150,
            "info",
            (
                "Ağ kayıtlarında genel internet kesintisi yerine 'SSL handshake', 'certificate expired' ve 'IKE negotiation failed' ifadeleri arttı.",
                "VPN ticket metinleri kullanıcı parolası sorunundan sertifika zinciri ve gateway policy bozulmasına doğru kaydı.",
                "Açıklamalarda yeni VPN client sürümü, split tunnel ve DNS leak ifadeleri olağan dışı yoğunluk kazandı.",
            ),
        ),
        Scenario(
            "Backup",
            15,
            95,
            "warning",
            (
                "Yedekleme kayıtlarında normal job failure yerine immutable backup, restore test failure ve snapshot silinmesi ifadeleri belirdi.",
                "Ticket semantiği kapasite uyarısından kritik kurtarma ve ransomware sonrası geri dönüş senaryolarına kaydı.",
                "Kayıtlarda 'son sağlam yedek', 'restore edilemiyor' ve 'retention bozuldu' ifadeleri yoğunlaştı.",
            ),
        ),
        Scenario(
            "Endpoint",
            20,
            115,
            "info",
            (
                "Cihaz kayıtlarında olağan yavaşlık yerine kernel crash, EDR isolation ve BitLocker recovery anahtarı ifadeleri arttı.",
                "Endpoint açıklamaları standart performans sorunundan güvenlik ajanı izolasyonu ve disk şifreleme olaylarına kaydı.",
                "Yeni ajan sürümü sonrası kayıt metinlerinde servis çakışması, quarantine ve rollback talepleri öne çıktı.",
            ),
        ),
    )


def build_combined_scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            "Security",
            220,
            900,
            "critical",
            (
                "Çok sayıda kullanıcı aynı anda şifrelenmiş dosya, fidye notu, EDR izolasyonu ve paylaşımlı klasör erişim sorunu bildirdi.",
                "Ticket hacmi yükselirken kategori güvenliğe kaydı ve açıklamalarda ransomware belirtisi taşıyan ifadeler baskınlaştı.",
                "SOC uyarıları, endpoint izolasyonları ve dosya kurtarma talepleri aynı pencerede birleşerek kritik alarm oluşturdu.",
            ),
        ),
        Scenario(
            "MFA",
            180,
            760,
            "critical",
            (
                "MFA push bombing şikayetleri, başarısız oturum açma artışı ve hesap kilidi kayıtları aynı gün anormal yükseldi.",
                "Kategori kimlik güvenliğine kayarken ticket metinleri onay yağmuru, şüpheli giriş ve imkansız konum ifadeleri içerdi.",
                "Kullanıcılar MFA bildirimlerinin kendilerinden kaynaklanmadığını belirtirken kayıt hacmi normalin çok üstüne çıktı.",
            ),
        ),
        Scenario(
            "Password Reset",
            250,
            820,
            "warning",
            (
                "Toplu parola reset talepleri, AD hesap kilidi ve SSO giriş başarısızlığı aynı pencerede yoğunlaştı.",
                "Parola politikası değişikliği sonrası hacim artışı, kategori kayması ve kimlik doğrulama semantik drift birlikte görüldü.",
                "Kurum genelinde kullanıcılar VPN, mail ve ERP erişimi için aynı anda parola yenileme kaydı açtı.",
            ),
        ),
        Scenario(
            "VPN",
            200,
            680,
            "critical",
            (
                "VPN gateway kesintisi sırasında uzaktan erişim kayıtları patladı, kategori VPN'e kaydı ve sertifika/gateway ifadeleri yoğunlaştı.",
                "Firewall policy değişikliği sonrası bağlantı kurulamama, SSL hatası ve kullanıcı grubu yetki sorunları birlikte arttı.",
                "Bölgesel VPN kesintisi aynı anda hacim artışı, ağ kategori kayması ve teknik hata semantiği üretti.",
            ),
        ),
        Scenario(
            "Exchange",
            180,
            620,
            "critical",
            (
                "Exchange kesintisi sırasında mail gönderememe, takvim gecikmesi ve ortak posta kutusu erişim kayıtları topluca yükseldi.",
                "Mail akışı bozulurken kategori Exchange'e kaydı ve açıklamalarda NDR, transport queue ve connector ifadeleri yoğunlaştı.",
                "Tenant seviyesindeki posta akışı sorunu hem kayıt hacmini artırdı hem de içerik semantiğini operasyonel kesintiye çevirdi.",
            ),
        ),
        Scenario(
            "Network",
            170,
            540,
            "warning",
            (
                "Merkez ofis ağ kesintisi VPN, DNS, DHCP ve kablosuz bağlantı kayıtlarını aynı anda artırdı.",
                "Ağ kategorisi baskın hale gelirken açıklamalarda paket kaybı, DNS çözümleme ve gateway timeout ifadeleri birleşti.",
                "Omurga anahtarındaki arıza hem hacim artışı hem kategori kayması hem de bağlantı semantiği değişimi yarattı.",
            ),
        ),
    )


def generate_for_type(
    anomaly_type: str,
    start: date,
    scenarios_factory: Callable[[], tuple[Scenario, ...]],
) -> list[dict[str, str | int]]:
    scenarios = scenarios_factory()
    records: list[dict[str, str | int]] = []
    suffixes = (
        "Bu pencere geçmiş 14 günlük baz çizgiye göre değerlendirme verisi olarak işaretlendi.",
        "Olay kurum içi destek yoğunluğu ve servis sürekliliği açısından izlenmelidir.",
        "Kayıt, anomali motorunun geri çağırma ve hassasiyet ölçümü için etiketlenmiştir.",
        "Senaryo kurumsal BT destek kuyruğunda erken uyarı üretimini test etmek için oluşturuldu.",
    )

    for i in range(RECORDS_PER_TYPE):
        scenario = scenarios[i % len(scenarios)]
        record_date = rotate_date(start, i)
        suffix = suffixes[(i + len(anomaly_type)) % len(suffixes)]
        records.append(make_record(record_date, anomaly_type, scenario, suffix))

    return records


def generate_dataset() -> list[dict[str, str | int]]:
    random.seed(RANDOM_SEED)

    generators: tuple[tuple[str, date, Callable[[], tuple[Scenario, ...]]], ...] = (
        ("Volume Spike", date(2026, 1, 1), build_volume_spike_scenarios),
        ("Category Shift", date(2026, 5, 1), build_category_shift_scenarios),
        ("Semantic Drift", date(2026, 9, 1), build_semantic_drift_scenarios),
        ("Combined Anomaly", date(2027, 1, 1), build_combined_scenarios),
    )

    records: list[dict[str, str | int]] = []
    for anomaly_type, start, factory in generators:
        records.extend(generate_for_type(anomaly_type, start, factory))

    return records


def write_csv(records: list[dict[str, str | int]], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "date",
        "category",
        "ticket_count",
        "anomaly_type",
        "severity",
        "explanation",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    records = generate_dataset()
    write_csv(records)

    counts: dict[str, int] = {anomaly_type: 0 for anomaly_type in ANOMALY_TYPES}
    for record in records:
        counts[str(record["anomaly_type"])] += 1

    print(f"Wrote {len(records)} records to {OUTPUT_PATH}")
    for anomaly_type in ANOMALY_TYPES:
        print(f"{anomaly_type}: {counts[anomaly_type]}")


if __name__ == "__main__":
    main()
