# Quick Start Guide

## Project Successfully Created! 🎉

Your BT Support Assistant project structure has been fully set up. Here's what you have:

## 📁 Project Structure

```
bt-support-assistant/
├── app/                      ✅ FastAPI application
│   ├── main.py              ✅ API entry point
│   ├── config.py            ✅ Configuration management
│   └── routers/             ✅ API endpoints (chat, health, anomaly)
├── core/                    ✅ Core functionality
│   ├── nlp/                 ✅ Text preprocessing & intent classification
│   ├── retrieval/           ✅ BM25, embeddings, hybrid retrieval
│   ├── rag/                 ✅ RAG pipeline with confidence estimation
│   └── anomaly/             ✅ Anomaly & drift detection
├── data_pipeline/           ✅ Data ingestion & anonymization
├── tests/                   ✅ Unit tests
├── scripts/                 ✅ Helper scripts
└── Documentation            ✅ README, SETUP, and this guide
```

## 🚀 Next Steps

### Step 1: Set up Python environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Test the setup

```powershell
# Build sample indexes (creates test data)
python scripts/build_sample_index.py

# Run tests
pytest

# Start the API server
python scripts/run_server.py
```

### Step 3: Access the API

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

## 📚 What Each Module Does

### 1. **app/** - FastAPI Application
- `main.py`: Server setup and startup
- `config.py`: Environment configuration
- `routers/`:
  - `chat.py`: Question answering endpoint
  - `anomaly.py`: Anomaly detection endpoint
  - `health.py`: Health checks

### 2. **core/nlp/** - Natural Language Processing
- `preprocessing.py`: Text cleaning, normalization, language detection
- `intent.py`: Query intent classification (how-to, troubleshoot, etc.)

### 3. **core/retrieval/** - Document Retrieval
- `bm25_retriever.py`: Keyword-based search (lexical)
- `embedding_retriever.py`: Semantic search using embeddings
- `hybrid_retriever.py`: Combines BM25 + embeddings
- `eval_metrics.py`: Retrieval quality metrics (Precision@k, Recall@k, nDCG)

### 4. **core/rag/** - Retrieval-Augmented Generation
- `pipeline.py`: Main RAG orchestration
- `prompts.py`: Prompt templates with "no source, no answer" policy
- `confidence.py`: Answer confidence estimation

### 5. **core/anomaly/** - Anomaly Detection
- `feature_extractor.py`: Extract features from tickets
- `anomaly_detector.py`: Statistical and ML-based anomaly detection
- `drift_detector.py`: Distribution drift detection

### 6. **data_pipeline/** - Data Processing
- `ingestion.py`: Load tickets from various sources
- `anonymize.py`: Remove PII (emails, phones, IPs, names)
- `build_indexes.py`: Build and save search indexes

### 7. **tests/** - Test Suite
- `test_nlp.py`: NLP module tests
- `test_retrieval.py`: Retrieval module tests
- `test_anonymization.py`: Anonymization tests

### 8. **scripts/** - Utilities
- `run_server.py`: Start the API server
- `build_sample_index.py`: Create sample data and indexes

## 🔧 Key Features Implemented

### ✅ Hybrid Retrieval
Combines keyword (BM25) and semantic (embedding) search for best results

### ✅ Strict "No Source, No Answer" Policy
RAG pipeline explicitly refuses to answer when confidence is low

### ✅ Privacy-First Design
Automatic PII detection and anonymization

### ✅ Anomaly Detection
Monitor ticket distributions and detect unusual patterns

### ✅ Drift Detection
Track semantic shifts in ticket content over time

### ✅ Intent Classification
Route queries to appropriate handlers

### ✅ Confidence Estimation
Multiple signals to determine answer reliability

## 📝 Example Usage

### Test Retrieval

```python
from core.retrieval import BM25Retriever, EmbeddingRetriever, HybridRetriever

# Load indexes
# (after running build_sample_index.py)

# Search
query = "How to reset password?"
results = hybrid_retriever.search(query, top_k=5)

for result in results:
    print(f"{result['title']} - Score: {result['score']:.3f}")
```

### Test Anonymization

```python
from data_pipeline.anonymize import DataAnonymizer

anonymizer = DataAnonymizer(anonymization_enabled=True)

text = "Contact john.doe@example.com for help"
anonymized = anonymizer.anonymize_text(text)
print(anonymized)  # "Contact [EMAIL] for help"
```

### Test Intent Classification

```python
from core.nlp.intent import IntentClassifier

classifier = IntentClassifier()
intent = classifier.classify("How to reset my password?")
print(intent)  # QueryIntent.HOW_TO
```

## 🎯 Current Implementation Status

### ✅ Fully Implemented
- Project structure
- FastAPI application skeleton
- NLP preprocessing and intent classification
- BM25, embedding, and hybrid retrieval
- RAG pipeline framework
- Confidence estimation
- Anomaly and drift detection
- Data anonymization
- Test suite
- Documentation

### ⚠️ Needs Configuration
- LLM model integration (in `core/rag/pipeline.py`)
  - Currently has placeholder for actual generation
  - You'll need to add model loading and inference
  
- Elasticsearch connection (optional, for production)
  - Can use in-memory BM25 for development

### 🔜 Future Enhancements
- Real-time ticket ingestion
- User feedback loop
- Model fine-tuning pipeline
- Dashboard for monitoring
- Multi-language support
- Advanced analytics

## 💡 Tips

1. **Start Small**: Use the sample data to test everything works
2. **Check Logs**: Look in `logs/app.log` for debugging
3. **Read Tests**: Test files show usage examples
4. **Iterate**: Start with simple queries and gradually add complexity

## 📖 Documentation

- **README.md**: Project overview and architecture
- **SETUP.md**: Detailed installation and configuration
- **This file**: Quick start and orientation

## 🆘 Troubleshooting

### Import errors?
Make sure you're in the project root and venv is activated

### Module not found?
```powershell
pip install -r requirements.txt
```

### Tests failing?
Some tests require sample indexes:
```powershell
python scripts/build_sample_index.py
```

## 🎉 You're Ready!

The project structure is complete and ready for development. Start with:

```powershell
# 1. Install
pip install -r requirements.txt

# 2. Test
python scripts/build_sample_index.py
pytest

# 3. Run
python scripts/run_server.py
```

Then visit http://localhost:8000/docs to explore the API!

---

**Need help?** Check SETUP.md for detailed instructions or review the code - it's well-documented with docstrings explaining each component.

