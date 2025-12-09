# 🧪 SCENARIO-BASED TESTING GUIDE

## 📋 **OVERVIEW**

The scenario-based testing system allows you to verify that the chat endpoint (`/api/v1/chat`) returns reasonable answers for typical IT support questions.

---

## 🎯 **WHAT DOES IT TEST?**

### **Test Criteria:**

1. **Confidence Score**
   - Ensures the RAG pipeline is confident enough in its answer
   - Each scenario has a minimum threshold (0.3-0.4)
   - Example: VPN questions should have ≥0.4 confidence

2. **Keyword Presence**
   - Verifies that expected keywords appear in the answer
   - At least 50% of keywords must be present (case-insensitive)
   - Example: "Outlook şifre" answer should contain "outlook", "şifre", "sıfırlama"

3. **Source Documents**
   - Checks that at least 1 relevant document was retrieved
   - Ensures RAG is finding sources, not just generating text

---

## 📝 **DEFINED SCENARIOS**

### **1. Outlook Password Reset**
```python
Question: "Outlook şifremi unuttum, nasıl sıfırlarım?"
Expected Keywords: outlook, parola, şifre, sıfırlama, bağlantı
Min Confidence: 0.4
```

**What it tests:** Email password reset workflows

---

### **2. VPN Connection Issue**
```python
Question: "VPN'e bağlanamıyorum, ne yapmalıyım?"
Expected Keywords: vpn, bağlantı, ayar, istemci, kimlik
Min Confidence: 0.4
```

**What it tests:** Network connectivity troubleshooting

---

### **3. Printer Not Working**
```python
Question: "Yazıcı yazdırmıyor, nasıl düzeltebilirim?"
Expected Keywords: yazıcı, sürücü, bağlantı, ayar
Min Confidence: 0.3
```

**What it tests:** Hardware troubleshooting

---

### **4. Slow Laptop**
```python
Question: "Laptop çok yavaş çalışıyor, ne yapmalıyım?"
Expected Keywords: performans, disk, bellek, güncelleme, temizlik
Min Confidence: 0.3
```

**What it tests:** Performance optimization advice

---

### **5. Cannot Send Email**
```python
Question: "Email gönderemiyorum, hata veriyor"
Expected Keywords: email, mail, gönder, ayar, sunucu
Min Confidence: 0.3
```

**What it tests:** Email configuration issues

---

### **6. Disk Full Error**
```python
Question: "Disk alanı doldu hatası alıyorum"
Expected Keywords: disk, alan, temizlik, dosya, silme
Min Confidence: 0.35
```

**What it tests:** Storage management

---

## 🚀 **HOW TO RUN**

### **Method 1: Standalone Script (Recommended for Manual Testing)**

```bash
# Terminal 1: Start server
conda activate bt-support
python scripts/run_server.py

# Terminal 2: Run scenarios
conda activate bt-support
python scripts/run_chat_scenarios.py
```

**Output:**
```
╔══════════════════════════════════════════════════════════════════╗
║  BT Support Assistant - End-to-End Scenario Tests               ║
╚══════════════════════════════════════════════════════════════════╝

🔍 Checking server health...
✅ Server is running

🚀 Running 6 scenarios...

[1/6] Testing: Outlook Şifre Sıfırlama...

✅ Outlook Şifre Sıfırlama
   Question: Outlook şifremi unuttum, nasıl sıfırlarım?
   Confidence: 0.67 (threshold: 0.40) ✓
   Keywords: 4/5 (80%) ✓
             outlook ✓, parola ✓, şifre ✓, sıfırlama ✓, bağlantı ✗
   Sources: 3 documents
   Answer length: 342 chars

[2/6] Testing: VPN Bağlantı Sorunu...
...
```

---

### **Method 2: Pytest (Recommended for CI/CD)**

```bash
# Run only scenario tests
pytest tests/test_chat_scenarios.py -v

# Run with markers
pytest tests/test_chat_scenarios.py -v -m integration

# Run and show detailed output
pytest tests/test_chat_scenarios.py -v -s
```

**Output:**
```
tests/test_chat_scenarios.py::test_chat_scenario[outlook_password_reset] PASSED
tests/test_chat_scenarios.py::test_chat_scenario[vpn_connection_issue] PASSED
tests/test_chat_scenarios.py::test_chat_scenario[printer_not_working] PASSED
tests/test_chat_scenarios.py::test_chat_scenario[slow_laptop] PASSED
tests/test_chat_scenarios.py::test_chat_scenario[cannot_send_email] PASSED
tests/test_chat_scenarios.py::test_chat_scenario[disk_full_error] PASSED

============================== 6 passed in 12.34s ===============================
```

---

## 📊 **UNDERSTANDING RESULTS**

### **Success Example:**
```
✅ VPN Bağlantı Sorunu
   Question: VPN'e bağlanamıyorum, ne yapmalıyım?
   Confidence: 0.72 (threshold: 0.40) ✓
   Keywords: 5/5 (100%) ✓
             vpn ✓, bağlantı ✓, ayar ✓, istemci ✓, kimlik ✓
   Sources: 4 documents
   Answer length: 456 chars
```

**Interpretation:**
- ✅ **Confidence 0.72** → High confidence (above 0.40 threshold)
- ✅ **Keywords 5/5** → All expected keywords found
- ✅ **4 sources** → Multiple relevant documents retrieved
- ✅ **456 chars** → Substantial answer provided

**Verdict:** EXCELLENT - RAG pipeline working perfectly for this scenario

---

### **Failure Example:**
```
❌ Yazıcı Yazdırmıyor
   Question: Yazıcı yazdırmıyor, nasıl düzeltebilirim?
   Confidence: 0.22 (threshold: 0.30) ✗
   Keywords: 1/4 (25%) ✗
             yazıcı ✓, sürücü ✗, bağlantı ✗, ayar ✗
   Sources: 1 documents
   Answer length: 87 chars
```

**Interpretation:**
- ❌ **Confidence 0.22** → Below 0.30 threshold (too uncertain)
- ❌ **Keywords 1/4** → Only "yazıcı" found, missing key troubleshooting terms
- ⚠️ **1 source** → Limited retrieval
- ⚠️ **87 chars** → Short answer (may be "no source" fallback)

**Verdict:** FAILING - Need to improve:
1. Add more printer-related documents to knowledge base
2. Check if printer keywords are properly indexed
3. Review BM25/embedding retrieval for printer queries

---

## 🔍 **DEBUGGING FAILURES**

### **Scenario 1: Low Confidence**

**Symptom:**
```
Confidence: 0.18 (threshold: 0.40) ✗
```

**Possible Causes:**
1. No relevant documents in knowledge base
2. Query keywords don't match document content
3. Retrieval not finding right documents
4. Confidence scoring too strict

**How to Fix:**
```bash
# 1. Check what documents exist
python -c "
from data_pipeline.ingestion import load_itsm_tickets_from_csv
tickets = load_itsm_tickets_from_csv('data/sample_itsm_tickets.csv')
for t in tickets:
    if 'outlook' in t['short_description'].lower():
        print(t['short_description'])
"

# 2. Test retrieval directly
python -c "
from core.retrieval.hybrid_retriever import HybridRetriever
retriever = HybridRetriever()
results = retriever.search('outlook şifre', top_k=5)
for r in results:
    print(f'{r[\"score\"]:.2f}: {r[\"title\"]}')
"
```

---

### **Scenario 2: Missing Keywords**

**Symptom:**
```
Keywords: 1/5 (20%) ✗
yazıcı ✓, sürücü ✗, bağlantı ✗, ayar ✗, kuyruk ✗
```

**Possible Causes:**
1. Answer is too generic (not using retrieved docs)
2. Retrieved docs don't contain expected keywords
3. LLM paraphrasing too much (synonyms used instead)

**How to Fix:**
```python
# Option 1: Add synonyms to expected keywords
expected_keywords = [
    "yazıcı", "printer",  # Add English variant
    "sürücü", "driver",
    "bağlantı", "connection",
    # ...
]

# Option 2: Lower keyword threshold
# In test: assert keyword_ratio >= 0.5
# Change to: assert keyword_ratio >= 0.3  # More lenient

# Option 3: Improve system prompt
# Edit: core/rag/prompts.py
# Add: "Include technical terms like 'sürücü', 'ayar', 'bağlantı'"
```

---

### **Scenario 3: No Sources Retrieved**

**Symptom:**
```
Sources: 0 documents
```

**Possible Causes:**
1. Index not built
2. Index file corrupted
3. Query preprocessing removes all meaningful terms

**How to Fix:**
```bash
# Rebuild indexes
python scripts/build_sample_index.py

# Or with PDF
python scripts/build_index_with_pdf.py

# Check index files exist
ls -lh indexes/
# Should see: bm25_index.pkl, faiss_index.bin, embedding_data.pkl
```

---

## 🛠️ **CUSTOMIZATION**

### **Adding New Scenarios**

**Edit:** `scripts/run_chat_scenarios.py`

```python
SCENARIOS.append(
    ChatScenario(
        name="Wi-Fi Not Working",
        question="Wi-Fi'ye bağlanamıyorum",
        expected_keywords=["wifi", "kablosuz", "ağ", "bağlantı", "şifre"],
        min_confidence=0.35,
    )
)
```

**For pytest:** `tests/test_chat_scenarios.py`

```python
SCENARIOS.append({
    "name": "wifi_not_working",
    "question": "Wi-Fi'ye bağlanamıyorum",
    "expected_keywords": ["wifi", "kablosuz", "ağ", "bağlantı"],
    "min_confidence": 0.35,
    "language": "tr",
})
```

---

### **Adjusting Thresholds**

**Lower Confidence Thresholds (More Lenient):**
```python
# For less critical scenarios
min_confidence = 0.25  # Instead of 0.4
```

**Raise Confidence Thresholds (More Strict):**
```python
# For critical scenarios (e.g., security, data loss)
min_confidence = 0.6  # Instead of 0.4
```

**Keyword Threshold:**
```python
# In test: assert keyword_ratio >= 0.5  # 50% of keywords

# More lenient:
assert keyword_ratio >= 0.3  # 30% of keywords

# More strict:
assert keyword_ratio >= 0.7  # 70% of keywords
```

---

## 📈 **INTERPRETING SUMMARY**

```
SUMMARY
Total scenarios: 6
Passed: 5
Failed: 1
Pass rate: 83%

✅ Overall status: GOOD - Most scenarios passed
```

### **Pass Rate Guidelines:**

| Pass Rate | Status | Action |
|-----------|--------|--------|
| **≥ 90%** | 🟢 EXCELLENT | System is working well |
| **80-89%** | 🟡 GOOD | Minor issues, monitor |
| **70-79%** | 🟠 ACCEPTABLE | Some scenarios need attention |
| **< 70%** | 🔴 POOR | Significant issues, investigate |

---

## 🔄 **CI/CD INTEGRATION**

### **GitHub Actions Example:**

```yaml
name: Scenario Tests

on: [push, pull_request]

jobs:
  test-scenarios:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Build indexes
        run: |
          python scripts/build_sample_index.py
      
      - name: Start server
        run: |
          python scripts/run_server.py &
          sleep 10  # Wait for server to start
      
      - name: Run scenario tests
        run: |
          pytest tests/test_chat_scenarios.py -v -m integration
```

---

## 📚 **BEST PRACTICES**

### **1. Keep Scenarios Realistic**
- Use actual questions from support tickets
- Don't make scenarios too easy (generic answers pass)
- Don't make scenarios too hard (overly specific keywords)

### **2. Update Scenarios with Knowledge Base**
- When adding new documents, add corresponding scenarios
- When removing features, remove related scenarios

### **3. Monitor Trends Over Time**
- Track pass rate across commits
- Investigate sudden drops in confidence
- Celebrate improvements!

### **4. Balance Coverage**
- Cover all major categories (network, email, hardware, software)
- Include both common and edge-case questions
- Test different phrasings of same issue

---

## 🎯 **SUCCESS CRITERIA SUMMARY**

A **scenario passes** if ALL conditions are met:

✅ **Confidence** ≥ `min_confidence`
✅ **Keywords** ≥ 50% of `expected_keywords` found in answer
✅ **Sources** ≥ 1 document retrieved
✅ **Answer Length** ≥ 50 characters

**Overall success:** ≥ 70% of scenarios passing

---

## 🔗 **RELATED DOCUMENTATION**

- **RAG Pipeline:** `core/rag/pipeline.py`
- **Retrieval:** `core/retrieval/hybrid_retriever.py`
- **Confidence Scoring:** `core/rag/confidence.py`
- **API Endpoint:** `app/routers/chat.py`

---

## 🎉 **READY TO TEST!**

```bash
# 1. Start server
python scripts/run_server.py

# 2. Run scenarios
python scripts/run_chat_scenarios.py

# 3. Check results
# ✅ Pass rate ≥ 80%? Great!
# ❌ Pass rate < 70%? Check debugging section above
```

**Good luck! 🚀**



