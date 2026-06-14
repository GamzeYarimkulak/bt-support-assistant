"""
İndeks oluştur ve test et - Tek komutla
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.build_indexes import build_indexes_from_csv
from data_pipeline.build_indexes import IndexBuilder
from core.retrieval.hybrid_retriever import HybridRetriever
from core.retrieval.dynamic_weighting import DynamicWeightComputer


def main():
    print("=" * 70)
    print("İNDEKS OLUŞTURMA VE TEST")
    print("=" * 70)
    print()
    
    # Step 1: Build indexes
    print("[1/3] İndeksler oluşturuluyor...")
    print("   Bu işlem birkaç dakika sürebilir (embedding model indirme)")
    print()
    
    try:
        num_docs, stats = build_indexes_from_csv(
            csv_path="data/raw/tickets/sample_itsm_tickets.csv",
            index_dir="indexes/",
            language="tr",
            anonymize=True
        )
        
        print(f"✅ {num_docs} doküman indekslendi!")
        print(f"   BM25: {stats['bm25_stats']['num_documents']} doküman")
        print(f"   Embedding: {stats['embedding_stats']['num_documents']} doküman")
        print()
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 2: Load indexes
    print("[2/3] İndeksler yükleniyor...")
    index_builder = IndexBuilder(index_dir="indexes/")
    bm25 = index_builder.load_bm25_index()
    embedding = index_builder.load_embedding_index()
    
    if not bm25 or not embedding:
        print("❌ İndeksler yüklenemedi!")
        return 1
    
    print("✅ İndeksler yüklendi!")
    print()
    
    # Step 3: Test with dynamic weighting
    print("[3/3] Dinamik ağırlıklandırma ile test ediliyor...")
    print()
    
    hybrid_retriever = HybridRetriever(
        bm25_retriever=bm25,
        embedding_retriever=embedding,
        use_dynamic_weighting=True
    )
    
    weight_computer = DynamicWeightComputer()
    
    test_queries = [
        "VPN bağlantı",
        "Outlook şifre sıfırlama",
        "Yazıcı yazdırmıyor nasıl çözülür"
    ]
    
    for query in test_queries:
        print(f"📝 Sorgu: '{query}'")
        alpha = weight_computer.compute_alpha(query)
        print(f"   Dinamik Alpha: {alpha:.2f}")
        
        results = hybrid_retriever.search(query, top_k=3)
        
        if results:
            print(f"   ✅ {len(results)} sonuç:")
            for i, result in enumerate(results[:2], 1):
                ticket_id = result.get('ticket_id', 'N/A')
                short_desc = result.get('short_description', '')[:40]
                score = result.get('score', 0.0)
                print(f"      {i}. [{ticket_id}] {short_desc}... (skor: {score:.3f})")
        else:
            print("   ⚠️  Sonuç bulunamadı")
        print()
    
    print("=" * 70)
    print("✅ Tüm testler tamamlandı!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


















