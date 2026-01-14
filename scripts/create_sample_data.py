"""
Create sample ITSM tickets CSV file for testing.
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path


def create_sample_csv(output_path: str = "data/sample_itsm_tickets.csv"):
    """
    Create a sample ITSM tickets CSV file with realistic Turkish IT support tickets.
    
    Args:
        output_path: Path where CSV file will be created
    """
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Sample tickets with realistic Turkish IT support scenarios
    tickets = [
        {
            "ticket_id": "TCK-0001",
            "created_at": "2024-12-01 09:15:00",
            "category": "Uygulama",
            "subcategory": "Outlook",
            "short_description": "Outlook şifremi unuttum",
            "description": "Outlook email hesabıma giriş yapamıyorum. Şifremi hatırlamıyorum ve şifre sıfırlama bağlantısı gelmiyor.",
            "resolution": "Kullanıcıya şifre sıfırlama bağlantısı gönderildi. Outlook web üzerinden şifre sıfırlama işlemi tamamlandı. Yeni şifre ile giriş yapıldı.",
            "channel": "portal",
            "priority": "Medium",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0002",
            "created_at": "2024-12-01 10:30:00",
            "category": "Ağ",
            "subcategory": "VPN",
            "short_description": "VPN bağlantısı kopuyor",
            "description": "VPN bağlantısı her 5-10 dakikada bir kopuyor. İnternet bağlantım normal çalışıyor ama VPN sürekli kesiliyor.",
            "resolution": "VPN istemci yazılımı güncellendi. Bağlantı ayarları kontrol edildi ve yeniden yapılandırıldı. Sorun çözüldü.",
            "channel": "email",
            "priority": "High",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0003",
            "created_at": "2024-12-01 11:45:00",
            "category": "Donanım",
            "subcategory": "Yazıcı",
            "short_description": "Yazıcı yazdırmıyor",
            "description": "Ağ yazıcısına yazdırma komutu gönderiyorum ama yazdırma yapılmıyor. Yazıcı çevrimiçi görünüyor ama iş kuyruğunda bekliyor.",
            "resolution": "Yazıcı sürücüsü güncellendi. Yazıcı kuyruğu temizlendi. Test sayfası başarıyla yazdırıldı. Sorun çözüldü.",
            "channel": "phone",
            "priority": "Medium",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0004",
            "created_at": "2024-12-02 08:20:00",
            "category": "Donanım",
            "subcategory": "Laptop",
            "short_description": "Laptop çok yavaş çalışıyor",
            "description": "Laptop açılırken ve çalışırken çok yavaş. Programlar geç açılıyor ve donuyor. Disk kullanımı %100 görünüyor.",
            "resolution": "Disk temizliği yapıldı. Gereksiz dosyalar silindi. Disk birleştirme yapıldı. RAM kontrol edildi. Performans iyileşti.",
            "channel": "web",
            "priority": "High",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0005",
            "created_at": "2024-12-02 14:10:00",
            "category": "Uygulama",
            "subcategory": "Email",
            "short_description": "Email gönderemiyorum",
            "description": "Outlook'tan email göndermeye çalışıyorum ama 'gönderilemedi' hatası alıyorum. Alıcı adresi doğru görünüyor.",
            "resolution": "SMTP sunucu ayarları kontrol edildi. Güvenlik duvarı kuralı eklendi. Test emaili başarıyla gönderildi.",
            "channel": "portal",
            "priority": "Medium",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0006",
            "created_at": "2024-12-03 09:00:00",
            "category": "Donanım",
            "subcategory": "Disk",
            "short_description": "Disk alanı doldu hatası",
            "description": "C sürücüsünde disk alanı doldu hatası alıyorum. Dosya kaydedemiyorum ve programlar çalışmıyor.",
            "resolution": "Geçici dosyalar temizlendi. Kullanılmayan programlar kaldırıldı. Disk alanı %15'e düştü. Sorun çözüldü.",
            "channel": "email",
            "priority": "High",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0007",
            "created_at": "2024-12-03 13:30:00",
            "category": "Ağ",
            "subcategory": "WiFi",
            "short_description": "WiFi bağlantısı yok",
            "description": "Laptop WiFi ağına bağlanamıyor. Ağ listesinde görünmüyor. Ethernet kablosu ile bağlanabiliyorum.",
            "resolution": "WiFi sürücüsü güncellendi. Ağ ayarları sıfırlandı. WiFi adaptörü yeniden etkinleştirildi. Bağlantı sağlandı.",
            "channel": "phone",
            "priority": "High",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0008",
            "created_at": "2024-12-04 10:15:00",
            "category": "Uygulama",
            "subcategory": "Teams",
            "short_description": "Teams'te ses gelmiyor",
            "description": "Microsoft Teams'te görüşme yaparken karşı taraftan ses gelmiyor. Mikrofonum çalışıyor ama hoparlörden ses çıkmıyor.",
            "resolution": "Ses ayarları kontrol edildi. Ses sürücüsü güncellendi. Teams ses ayarları yeniden yapılandırıldı. Sorun çözüldü.",
            "channel": "portal",
            "priority": "Medium",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0009",
            "created_at": "2024-12-04 15:45:00",
            "category": "Güvenlik",
            "subcategory": "Kimlik Doğrulama",
            "short_description": "Çok faktörlü kimlik doğrulama hatası",
            "description": "MFA kodunu giriyorum ama 'kimlik doğrulama başarısız' hatası alıyorum. Telefonumda kod geliyor ama sistem kabul etmiyor.",
            "resolution": "MFA ayarları kontrol edildi. Zaman senkronizasyonu yapıldı. MFA uygulaması yeniden yapılandırıldı. Giriş başarılı.",
            "channel": "email",
            "priority": "High",
            "status": "Closed"
        },
        {
            "ticket_id": "TCK-0010",
            "created_at": "2024-12-05 11:20:00",
            "category": "Uygulama",
            "subcategory": "Office",
            "short_description": "Word dosyası açılmıyor",
            "description": "Word dosyasını açmaya çalışıyorum ama 'dosya bozuk' hatası alıyorum. Dosya daha önce açılabiliyordu.",
            "resolution": "Dosya yedeği bulundu ve geri yüklendi. Word onarım aracı çalıştırıldı. Dosya başarıyla açıldı.",
            "channel": "web",
            "priority": "Low",
            "status": "Closed"
        }
    ]
    
    # Write to CSV
    fieldnames = [
        "ticket_id", "created_at", "category", "subcategory",
        "short_description", "description", "resolution",
        "channel", "priority", "status"
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tickets)
    
    print(f"✅ Örnek CSV dosyası oluşturuldu: {output_path}")
    print(f"   Toplam {len(tickets)} ticket eklendi")
    return output_path


if __name__ == "__main__":
    import sys
    output_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_itsm_tickets.csv"
    create_sample_csv(output_path)


















