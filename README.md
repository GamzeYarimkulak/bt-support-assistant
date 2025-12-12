# BT Support Assistant – Context-Aware Hybrid RAG & Anomaly Detection

This repository contains a **context-aware IT support assistant** for an enterprise ITSM environment.  
The assistant has two main goals:

1. **Reliable Question Answering** over ITSM tickets and internal documentation  
2. **Anomaly & Drift Detection** over incoming IT tickets and their semantic distributions

The system is designed with strong constraints against hallucinations:  
> If there is not enough trusted evidence in the retrieved context, the model must explicitly say it cannot answer.

---

## High-Level Architecture

### Online path (user query → answer)

1. **User Interface**
   - Web chat / portal or embedded chat inside ITSM tool
2. **API Backend** (`app/`)
   - FastAPI application exposing chat and anomaly endpoints
   - Handles auth, sessions, logging, routing
3. **NLP & Intent** (`core/nlp/`)
   - Language detection, normalization, optional intent classification
4. **Hybrid Retrieval** (`core/retrieval/`)
   - BM25 (lexical) + embedding-based dense retrieval
   - Fusion to get top-k relevant tickets/docs
5. **RAG Answering** (`core/rag/`)
   - Given the retrieved context and user query, run a local LLM
   - Apply "no source, no answer" policy with confidence scoring
6. **Logging & Metrics**
   - Store logs and feedback for later evaluation and model improvement

### Offline path (data ingestion → indexes → anomaly features)

1. **Data Ingestion** (`data_pipeline/`)
   - Pull ITSM tickets and internal documentation
2. **Anonymization & Cleaning** (`data_pipeline/anonymize.py`)
   - Remove or mask PII (names, emails, phones, IPs, etc.)
3. **Index & Embeddings Build** (`data_pipeline/build_indexes.py`)
   - Build/update BM25 index
   - Compute embeddings and build/update vector index
4. **Anomaly Features** (`core/anomaly/`)
   - Aggregate embeddings and counts per time window
   - Compute drift/anomaly scores

---

## Repository Structure

- `app/`
  - `main.py`: FastAPI application entry point
  - `routers/`: API endpoints for chat, health, anomaly
  - `config.py`: configuration handling (env vars, paths, model names)
- `core/`
  - `nlp/`: preprocessing and intent classification
  - `retrieval/`: BM25, embedding, hybrid retrieval, evaluation metrics
  - `rag/`: RAG pipeline, prompts, confidence estimation
  - `anomaly/`: feature extraction, drift & anomaly detectors
- `data_pipeline/`: ITSM & docs ingestion, anonymization, index building
- `models/`: local model files (LLM and embedding models), not committed to git
- `scripts/`: helper scripts for development and evaluation
- `tests/`: unit tests

---

## Tech Stack

- **Language**: Python (3.11+)
- **API Framework**: FastAPI
- **Retrieval**:
  - BM25 via Elasticsearch/OpenSearch or a local Python-based solution
  - Dense retrieval via sentence-transformer-like embeddings + FAISS/hnswlib
- **RAG**:
  - Local LLM (e.g. 7B–8B models via `transformers` or compatible runtime)
- **Anomaly Detection**:
  - scikit-learn / simple statistical detectors
- **Evaluation**:
  - nDCG, Recall@k and similar retrieval metrics

---

## Principles

- **Safety first**: no hallucinated answers; answer "I don't know based on current sources" when evidence is insufficient.
- **Explainability**: always return which tickets/documents were used to generate an answer.
- **Privacy**: all ITSM data is anonymized before indexing or training.

---

## Web UI (Phase 6)

A simple, lightweight web interface is available for demoing the system without external tools.

### Features

- **💬 Chat Panel**: Interactive RAG-based Q&A
  - Submit queries in Turkish or English
  - View answers with confidence scores
  - See source tickets with relevance scores
  
- **📊 Anomaly Panel**: Drift and anomaly detection dashboard
  - View window statistics and drift scores
  - Detect anomaly events (info/warning/critical)
  - Explore volume spikes, category shifts, and semantic drift

### How to Run

**1. Start the Backend:**

```bash
# Activate your conda environment
conda activate bt-support

# Run the FastAPI server
python scripts/run_server.py
```

The server starts at `http://localhost:8000`

**2. Open the Web UI:**

Open your browser and navigate to:

```
http://localhost:8000
```

or

```
http://localhost:8000/ui/index.html
```

The UI is served directly by FastAPI at the root path.

### Usage Examples

**Chat Example:**

1. Click the "💬 Chat (RAG)" tab
2. Enter a question: `"Outlook şifremi nasıl sıfırlarım?"`
3. Select language: `Türkçe`
4. Click "🚀 Gönder"
5. View:
   - Answer text
   - Confidence score (with color coding)
   - Source tickets with IDs and relevance scores

**Anomaly Example:**

1. Click the "📊 Anomali Tespiti" tab
2. Click "📊 İstatistikleri Yükle" to view window stats
3. Click "🚨 Anomalileri Yükle" to see detected anomalies
4. Explore:
   - Ticket volume trends
   - Category distribution changes
   - Semantic drift events

### Technical Details

**Frontend Stack:**
- Pure HTML/CSS/JavaScript (no build tools required)
- Fetch API for REST calls
- Located in `frontend/` directory

**API Integration:**
- POST `/api/v1/chat` - RAG-based question answering
- GET `/api/v1/anomaly/stats?days=7` - Window statistics
- GET `/api/v1/anomaly/detect?min_severity=info` - Anomaly events

**CORS:**
- Enabled for all origins (configure for production)
- Allows frontend to call backend APIs seamlessly

---

## Scenario-Based Evaluation

The system includes end-to-end scenario tests to verify that the chat endpoint returns reasonable answers for typical IT support questions.

### Running Scenario Tests

**Prerequisites:**
1. Server must be running at `http://localhost:8000`
2. Install dependencies: `pip install -r requirements.txt`

**Option 1: Manual Script (Detailed Output)**

Run the standalone script for a detailed, colored report:

```bash
# Start server in one terminal
python scripts/run_server.py

# Run scenarios in another terminal
python scripts/run_chat_scenarios.py
```

**Output Example:**
```
✅ Outlook Şifre Sıfırlama
   Question: Outlook şifremi unuttum, nasıl sıfırlarım?
   Confidence: 0.67 (threshold: 0.40) ✓
   Keywords: 4/5 (80%) ✓
             outlook ✓, parola ✓, şifre ✓, sıfırlama ✓, bağlantı ✗
   Sources: 3 documents
   Answer length: 342 chars

SUMMARY
Total scenarios: 6
Passed: 5
Failed: 1
Pass rate: 83%
```

**Option 2: Pytest (Automated Testing)**

Run as part of the test suite:

```bash
# Run only integration tests
pytest tests/test_chat_scenarios.py -v -m integration

# Run all tests including scenarios
pytest -v
```

### Test Scenarios

The following scenarios are tested:

| Scenario | Question | Min Confidence | Expected Keywords |
|----------|----------|----------------|-------------------|
| **Outlook Password Reset** | "Outlook şifremi unuttum" | 0.4 | outlook, parola, şifre, sıfırlama |
| **VPN Connection Issue** | "VPN'e bağlanamıyorum" | 0.4 | vpn, bağlantı, ayar, istemci |
| **Printer Not Working** | "Yazıcı yazdırmıyor" | 0.3 | yazıcı, sürücü, bağlantı |
| **Slow Laptop** | "Laptop çok yavaş" | 0.3 | performans, disk, güncelleme |
| **Cannot Send Email** | "Email gönderemiyorum" | 0.3 | email, mail, gönder, ayar |
| **Disk Full Error** | "Disk alanı doldu" | 0.35 | disk, alan, temizlik, dosya |

### Success Criteria

A scenario **passes** if:
1. **Confidence** ≥ minimum threshold (0.3-0.4 depending on scenario)
2. **Keywords** ≥ 50% of expected keywords appear in answer (case-insensitive)
3. **Sources** ≥ at least 1 source document returned

### Adding New Scenarios

To add custom scenarios, edit `scripts/run_chat_scenarios.py`:

```python
SCENARIOS.append(
    ChatScenario(
        name="Custom Scenario",
        question="Your question here",
        expected_keywords=["keyword1", "keyword2", "keyword3"],
        min_confidence=0.4,
    )
)
```

Then run the script to see results.

---








