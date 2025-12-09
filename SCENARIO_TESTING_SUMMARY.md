# ✅ **SCENARIO-BASED TESTING - IMPLEMENTATION COMPLETE**

## 🎯 **WHAT WAS ADDED**

End-to-end scenario tests for the `/api/v1/chat` endpoint to verify RAG pipeline quality.

---

## 📁 **FILES CREATED**

### **1. `scripts/run_chat_scenarios.py`**
Standalone script for manual testing with beautiful colored output.

**Features:**
- ✅ 6 predefined IT support scenarios
- ✅ Health check before running
- ✅ Confidence threshold validation
- ✅ Keyword presence verification
- ✅ Color-coded pass/fail output
- ✅ Detailed summary report
- ✅ Exit code (0 = all pass, 1 = some fail)

**Run:**
```bash
python scripts/run_chat_scenarios.py
```

---

### **2. `tests/test_chat_scenarios.py`**
Pytest integration for automated testing.

**Features:**
- ✅ Same 6 scenarios as standalone script
- ✅ Parametrized tests (one test per scenario)
- ✅ `@pytest.mark.integration` marker
- ✅ Server availability check (skips if not running)
- ✅ Detailed assertions with error messages
- ✅ Summary test (70% pass rate required)

**Run:**
```bash
pytest tests/test_chat_scenarios.py -v
```

---

### **3. `SCENARIO_TESTING_GUIDE.md`**
Comprehensive documentation (30+ pages).

**Covers:**
- 📖 Overview and goals
- 📝 All 6 scenarios detailed
- 🚀 How to run (manual + pytest)
- 📊 Interpreting results
- 🔍 Debugging failures
- 🛠️ Customization guide
- 🔄 CI/CD integration
- 📈 Best practices

---

### **4. Updated `requirements.txt`**
Added dependencies:
```
requests>=2.31.0
colorama>=0.4.6
```

---

### **5. Updated `README.md`**
New section: **"Scenario-Based Evaluation"**
- How to run tests
- Table of scenarios
- Success criteria
- How to add custom scenarios

---

## 🧪 **DEFINED SCENARIOS**

| # | Scenario | Question | Min Conf | Keywords |
|---|----------|----------|----------|----------|
| 1 | Outlook Password Reset | "Outlook şifremi unuttum" | 0.4 | outlook, parola, şifre, sıfırlama, bağlantı |
| 2 | VPN Connection Issue | "VPN'e bağlanamıyorum" | 0.4 | vpn, bağlantı, ayar, istemci, kimlik |
| 3 | Printer Not Working | "Yazıcı yazdırmıyor" | 0.3 | yazıcı, sürücü, bağlantı, ayar |
| 4 | Slow Laptop | "Laptop çok yavaş" | 0.3 | performans, disk, bellek, güncelleme |
| 5 | Cannot Send Email | "Email gönderemiyorum" | 0.3 | email, mail, gönder, ayar, sunucu |
| 6 | Disk Full Error | "Disk alanı doldu" | 0.35 | disk, alan, temizlik, dosya, silme |

---

## ✅ **SUCCESS CRITERIA**

A scenario **PASSES** if:
1. ✅ **Confidence** ≥ minimum threshold
2. ✅ **Keywords** ≥ 50% found in answer (case-insensitive)
3. ✅ **Sources** ≥ 1 document retrieved
4. ✅ **Answer** ≥ 50 characters long

**Overall success:** ≥ 70% of scenarios passing

---

## 🚀 **HOW TO RUN**

### **Quick Test:**
```bash
# Terminal 1: Start server
python scripts/run_server.py

# Terminal 2: Run scenarios
python scripts/run_chat_scenarios.py
```

### **Expected Output:**
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
✅ VPN Bağlantı Sorunu
   ...

======================================================================
SUMMARY
======================================================================
Total scenarios: 6
Passed: 5
Failed: 1
Pass rate: 83%

✅ Overall status: GOOD - Most scenarios passed
```

---

### **Pytest:**
```bash
pytest tests/test_chat_scenarios.py -v -m integration
```

**Expected Output:**
```
tests/test_chat_scenarios.py::test_chat_scenario[outlook_password_reset] PASSED [ 16%]
tests/test_chat_scenarios.py::test_chat_scenario[vpn_connection_issue] PASSED [ 33%]
tests/test_chat_scenarios.py::test_chat_scenario[printer_not_working] PASSED [ 50%]
tests/test_chat_scenarios.py::test_chat_scenario[slow_laptop] PASSED [ 66%]
tests/test_chat_scenarios.py::test_chat_scenario[cannot_send_email] PASSED [ 83%]
tests/test_chat_scenarios.py::test_chat_scenario[disk_full_error] PASSED [100%]

============================== 6 passed in 12.34s ===============================
```

---

## 🎨 **FEATURES**

### **Standalone Script:**
- 🎨 **Colorama** for beautiful terminal output
- 🟢 Green = Pass, 🔴 Red = Fail, 🟡 Yellow = Warning
- 📊 Detailed per-scenario breakdown
- 📈 Summary statistics
- 🚦 Exit code for CI/CD integration

### **Pytest:**
- ✅ Parametrized tests (DRY principle)
- ✅ `@pytest.mark.integration` marker
- ✅ Server health check (auto-skip if not running)
- ✅ Detailed assertion messages
- ✅ `-v` flag shows full details
- ✅ Can be run in CI/CD pipelines

---

## 🔧 **CUSTOMIZATION**

### **Add New Scenario:**

**In `scripts/run_chat_scenarios.py`:**
```python
SCENARIOS.append(
    ChatScenario(
        name="Wi-Fi Not Working",
        question="Wi-Fi'ye bağlanamıyorum",
        expected_keywords=["wifi", "kablosuz", "ağ", "bağlantı"],
        min_confidence=0.35,
    )
)
```

**In `tests/test_chat_scenarios.py`:**
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

### **Adjust Thresholds:**

```python
# More lenient (for less critical scenarios)
min_confidence = 0.25  # Instead of 0.4

# More strict (for critical scenarios)
min_confidence = 0.6  # Instead of 0.4

# Keyword threshold (in code)
keyword_ratio >= 0.3  # Instead of 0.5 (30% instead of 50%)
```

---

## 📊 **WHAT GETS TESTED**

### **1. Confidence Score**
- Ensures RAG is confident in its answer
- Prevents low-quality/uncertain responses
- Threshold varies by scenario complexity

### **2. Keyword Presence**
- Verifies answer is on-topic
- Checks for domain-specific terms
- Case-insensitive matching
- At least 50% of expected keywords

### **3. Source Retrieval**
- Ensures documents were found
- Validates RAG pipeline end-to-end
- At least 1 source required

### **4. Answer Quality**
- Minimum 50 characters
- Not just "I don't know"
- Substantial response

---

## 🎯 **USE CASES**

### **Development:**
- ✅ Test after code changes
- ✅ Verify RAG improvements
- ✅ Validate new document additions

### **QA:**
- ✅ Manual testing with visual feedback
- ✅ Smoke test before deployment
- ✅ Regression testing

### **CI/CD:**
- ✅ Automated pytest runs
- ✅ GitHub Actions integration
- ✅ Quality gates

### **Monitoring:**
- ✅ Track pass rate over time
- ✅ Detect degradation
- ✅ A/B testing different RAG configs

---

## 🔍 **DEBUGGING**

### **Scenario Failing?**

**Check:**
1. **Is the server running?**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **Are indexes built?**
   ```bash
   ls -lh indexes/
   # Should see: bm25_index.pkl, faiss_index.bin
   ```

3. **Do relevant documents exist?**
   ```bash
   grep -i "outlook" data/sample_itsm_tickets.csv
   ```

4. **Is retrieval working?**
   - Check console logs when running server
   - Look for "Retrieved N documents"

5. **Is LLM responding?**
   - Check `.env` has `OPENAI_API_KEY`
   - Check `USE_REAL_LLM=true`

---

## 📈 **PASS RATE INTERPRETATION**

| Pass Rate | Status | Meaning |
|-----------|--------|---------|
| **90-100%** | 🟢 EXCELLENT | RAG working great! |
| **80-89%** | 🟡 GOOD | Minor issues, acceptable |
| **70-79%** | 🟠 ACCEPTABLE | Some scenarios need work |
| **< 70%** | 🔴 POOR | Significant problems |

---

## 🎉 **BENEFITS**

### **For Developers:**
- ✅ Quick feedback on RAG changes
- ✅ Catch regressions early
- ✅ Confidence before deployment

### **For QA:**
- ✅ Automated quality checks
- ✅ Reproducible test results
- ✅ Easy to extend scenarios

### **For Product:**
- ✅ Track system quality
- ✅ Measure improvements
- ✅ Identify weak areas

---

## 🚀 **READY TO TEST!**

```bash
# 1. Install dependencies (if not done)
pip install -r requirements.txt

# 2. Start server
python scripts/run_server.py

# 3. Run tests (new terminal)
python scripts/run_chat_scenarios.py

# Expected: Pass rate ≥ 70%
```

**Want to try now?** 😊



