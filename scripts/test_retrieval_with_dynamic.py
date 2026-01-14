"""
Test retrieval with dynamic weighting - Gerçek sorgularla test
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.build_indexes import IndexBuilder
from core.retrieval.hybrid_retriever import HybridRetriever
from core.retrieval.dynamic_weighting import DynamicWeightComputer


def test_retrieval():
    """Test retrieval with various queries."""
    print("=" * 70)
    print("DINAMIK AGIRLIKLANDIRMA ILE ARAMA TESTI")
    print("=" * 70)
    print()
    
    # Load indexes
    print("[1/3] İndeksler yükleniyor...")
    index_builder = IndexBuilder(index_dir="indexes/")
    bm25 = index_builder.load_bm25_index()
    embedding = index_builder.load_embedding_index()
    
    if not bm25 or not embedding:
        print("❌ İndeksler bulunamadı! Önce indeks oluşturun:")
        print("   python scripts/build_sample_index.py")
        return
    
    print(f"✅ BM25: {bm25.get_index_stats()['num_documents']} doküman")
    print(f"✅ Embedding: {embedding.get_index_stats()['num_documents']} doküman")
    print()
    
    # Create hybrid retriever with dynamic weighting
    print("[2/3] Hibrit retriever oluşturuluyor (dinamik ağırlıklandırma aktif)...")
    hybrid_retriever = HybridRetriever(
        bm25_retriever=bm25,
        embedding_retriever=embedding,
        use_dynamic_weighting=True  # ✅ Dinamik ağırlıklandırma aktif
    )
    print("✅ Hibrit retriever hazır!")
    print()
    
    # Test queries
    test_queries = [
        ("VPN bağlantı", "Kısa teknik sorgu"),
        ("Outlook şifre sıfırlama nasıl yapılır", "Orta sorgu"),
        ("Yazıcı yazdırmıyor ve hata mesajı veriyor nasıl çözebilirim", "Uzun sorgu"),
        ("Laptop çok yavaş", "Kısa teknik sorgu"),
        ("Email gönderemiyorum çünkü sunucu bağlantı hatası veriyor", "Uzun teknik sorgu"),
    ]
    
    print("[3/3] Test sorguları çalıştırılıyor...")
    print("=" * 70)
    print()
    
    for query, description in test_queries:
        print(f"📝 Sorgu: '{query}'")
        print(f"   Tip: {description}")
        print()
        
        # Get dynamic alpha
        weight_computer = DynamicWeightComputer()
        alpha = weight_computer.compute_alpha(query)
        print(f"   Dinamik Alpha: {alpha:.2f} ({'Embedding ağırlıklı' if alpha < 0.4 else 'BM25 ağırlıklı' if alpha > 0.6 else 'Dengeli'})")
        print()
        
        # Search
        results = hybrid_retriever.search(query, top_k=3)
        
        if results:
            print(f"   ✅ {len(results)} sonuç bulundu:")
            for i, result in enumerate(results, 1):
                ticket_id = result.get('ticket_id', 'N/A')
                short_desc = result.get('short_description', '')[:50]
                score = result.get('score', 0.0)
                alpha_used = result.get('alpha_used', 0.5)
                
                print(f"      {i}. [{ticket_id}] {short_desc}...")
                print(f"         Skor: {score:.3f} (Alpha: {alpha_used:.2f})")
        else:
            print("   ⚠️  Sonuç bulunamadı")
        
        print()
        print("-" * 70)
        print()
    
    print("=" * 70)
    print("✅ Test tamamlandı!")
    print("=" * 70)


if __name__ == "__main__":
    test_retrieval()


















