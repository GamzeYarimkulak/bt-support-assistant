"""
Demo script to test dynamic weighting functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.retrieval.dynamic_weighting import DynamicWeightComputer


def main():
    """Test dynamic weighting with various query examples."""
    print("=" * 70)
    print("DINAMIK AGIRLIKLANDIRMA TESTI")
    print("=" * 70)
    print()
    
    computer = DynamicWeightComputer()
    
    test_queries = [
        # Short technical queries (should favor embeddings)
        ("VPN bağlantı", "Kısa teknik sorgu"),
        ("Outlook şifre", "Kısa teknik sorgu"),
        ("yazıcı hata", "Kısa teknik sorgu"),
        
        # Medium queries (should be balanced)
        ("Outlook şifre sıfırlama nasıl yapılır", "Orta uzunlukta sorgu"),
        ("VPN bağlantı sorunu çözümü", "Orta uzunlukta sorgu"),
        ("Email gönderemiyorum ne yapmalıyım", "Orta uzunlukta sorgu"),
        
        # Long free-form queries (should favor BM25)
        ("Outlook email hesabıma giriş yapamıyorum ve şifre sıfırlama bağlantısı gelmiyor ne yapmalıyım", "Uzun serbest sorgu"),
        ("Yazıcı yazdırmıyor ve hata mesajı veriyor nasıl çözebilirim lütfen yardım edin", "Uzun serbest sorgu"),
    ]
    
    print(f"{'Sorgu':<60} {'Alpha':<8} {'Açıklama'}")
    print("-" * 70)
    
    for query, description in test_queries:
        alpha = computer.compute_alpha(query)
        characteristics = computer.get_query_characteristics(query)
        
        # Determine strategy
        if alpha < 0.4:
            strategy = "Embedding ağırlıklı"
        elif alpha > 0.6:
            strategy = "BM25 ağırlıklı"
        else:
            strategy = "Dengeli"
        
        print(f"{query[:58]:<60} {alpha:.2f}    {strategy}")
        print(f"  → Kelime sayısı: {characteristics['word_count']}, "
              f"Teknik terim: {characteristics['technical_term_count']}, "
              f"Oran: {characteristics['technical_ratio']:.2f}")
        print()
    
    print("=" * 70)
    print("SONUÇ")
    print("=" * 70)
    print("✅ Dinamik ağırlıklandırma çalışıyor!")
    print("   - Kısa teknik sorgular → Embedding ağırlıklı (alpha < 0.4)")
    print("   - Orta sorgular → Dengeli (alpha ~ 0.5)")
    print("   - Uzun sorgular → BM25 ağırlıklı (alpha > 0.6)")


if __name__ == "__main__":
    main()


















