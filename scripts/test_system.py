"""
Sistem Test Scripti - Mevcut durumu kontrol eder
"""

import sys
import os

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Gerekli kütüphanelerin kurulu olup olmadığını kontrol eder"""
    print("=" * 70)
    print("1. KÜTÜPHANE KONTROLÜ")
    print("=" * 70)
    
    required_modules = {
        "fastapi": "FastAPI",
        "sentence_transformers": "Sentence Transformers",
        "faiss": "FAISS",
        "rank_bm25": "BM25",
        "numpy": "NumPy",
        "pandas": "Pandas",
        "sklearn": "Scikit-learn",
        "transformers": "Transformers",
    }
    
    missing = []
    installed = []
    
    for module, name in required_modules.items():
        try:
            __import__(module)
            installed.append(f"✅ {name}")
        except ImportError:
            missing.append(f"❌ {name}")
            print(f"❌ {name} - KURULU DEĞİL")
        else:
            print(f"✅ {name} - KURULU")
    
    print()
    if missing:
        print(f"⚠️  {len(missing)} kütüphane eksik!")
        print("Kurulum için: pip install -r requirements.txt")
    else:
        print("✅ Tüm kütüphaneler kurulu!")
    
    return len(missing) == 0


def test_directories():
    """Gerekli dizinlerin varlığını kontrol eder"""
    print("\n" + "=" * 70)
    print("2. DİZİN KONTROLÜ")
    print("=" * 70)
    
    required_dirs = {
        "app": "API uygulaması",
        "core": "Core modüller",
        "data_pipeline": "Veri pipeline",
        "tests": "Test dosyaları",
    }
    
    optional_dirs = {
        "indexes": "İndeks dosyaları (oluşturulacak)",
        "data": "Veri dosyaları (oluşturulacak)",
        "models": "Model dosyaları (opsiyonel)",
        "logs": "Log dosyaları (otomatik oluşur)",
    }
    
    missing_required = []
    missing_optional = []
    
    for dir_name, desc in required_dirs.items():
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ - {desc}")
        else:
            print(f"❌ {dir_name}/ - EKSİK!")
            missing_required.append(dir_name)
    
    print("\nOpsiyonel dizinler:")
    for dir_name, desc in optional_dirs.items():
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ - {desc}")
        else:
            print(f"⚠️  {dir_name}/ - Yok (normal)")
            missing_optional.append(dir_name)
    
    return len(missing_required) == 0


def test_config():
    """Config dosyasını kontrol eder"""
    print("\n" + "=" * 70)
    print("3. CONFIG KONTROLÜ")
    print("=" * 70)
    
    try:
        from app.config import settings
        
        print(f"✅ Config yüklendi")
        print(f"   - App Name: {settings.app_name}")
        print(f"   - Environment: {settings.environment}")
        print(f"   - Embedding Model: {settings.embedding_model_name}")
        print(f"   - LLM Model: {settings.llm_model}")
        print(f"   - Use Real LLM: {settings.use_real_llm}")
        print(f"   - OpenAI API Key: {'✅ Set' if settings.openai_api_key else '❌ Not Set'}")
        
        return True
    except Exception as e:
        print(f"❌ Config yüklenemedi: {e}")
        return False


def test_indexes():
    """İndeks dosyalarını kontrol eder"""
    print("\n" + "=" * 70)
    print("4. İNDEKS KONTROLÜ")
    print("=" * 70)
    
    index_dir = "indexes"
    required_files = {
        "bm25_index.pkl": "BM25 indeksi",
        "embedding_data.pkl": "Embedding verileri",
        "faiss_index.bin": "FAISS indeksi",
    }
    
    if not os.path.exists(index_dir):
        print(f"⚠️  {index_dir}/ dizini yok")
        print("   İndeks oluşturmak için: python scripts/build_sample_index.py")
        return False
    
    all_exist = True
    for filename, desc in required_files.items():
        filepath = os.path.join(index_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath) / 1024  # KB
            print(f"✅ {filename} - {desc} ({size:.1f} KB)")
        else:
            print(f"❌ {filename} - EKSİK")
            all_exist = False
    
    if not all_exist:
        print("\n   İndeks oluşturmak için: python scripts/build_sample_index.py")
    
    return all_exist


def test_retrieval():
    """Retrieval sistemini test eder"""
    print("\n" + "=" * 70)
    print("5. RETRIEVAL SİSTEMİ TESTİ")
    print("=" * 70)
    
    try:
        from data_pipeline.build_indexes import IndexBuilder
        
        index_builder = IndexBuilder(index_dir="indexes/")
        bm25 = index_builder.load_bm25_index()
        embedding = index_builder.load_embedding_index()
        
        if bm25 is None:
            print("❌ BM25 indeksi yüklenemedi")
            return False
        
        if embedding is None:
            print("❌ Embedding indeksi yüklenemedi")
            return False
        
        print("✅ BM25 retriever yüklendi")
        print("✅ Embedding retriever yüklendi")
        
        # Test araması
        test_query = "Outlook şifre"
        print(f"\n   Test sorgusu: '{test_query}'")
        
        bm25_results = bm25.search(test_query, top_k=3)
        print(f"   ✅ BM25: {len(bm25_results)} sonuç bulundu")
        
        embedding_results = embedding.search(test_query, top_k=3)
        print(f"   ✅ Embedding: {len(embedding_results)} sonuç bulundu")
        
        return True
        
    except Exception as e:
        print(f"❌ Retrieval testi başarısız: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ana test fonksiyonu"""
    print("\n" + "=" * 70)
    print("BT SUPPORT ASSISTANT - SİSTEM KONTROLÜ")
    print("=" * 70)
    print()
    
    results = {
        "Kütüphaneler": test_imports(),
        "Dizinler": test_directories(),
        "Config": test_config(),
        "İndeksler": test_indexes(),
        "Retrieval": test_retrieval(),
    }
    
    print("\n" + "=" * 70)
    print("SONUÇ")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"{name}: {status}")
    
    print(f"\nToplam: {passed}/{total} test başarılı")
    
    if passed == total:
        print("\n🎉 Sistem hazır! Dinamik ağırlıklandırma eklenebilir.")
    else:
        print("\n⚠️  Bazı testler başarısız. Lütfen eksiklikleri giderin.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



















