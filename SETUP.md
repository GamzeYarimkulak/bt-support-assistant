# Setup Guide

This guide will help you set up and run the BT Support Assistant project.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Virtual environment tool (venv, conda, etc.)

## Installation

### 1. Clone the repository (if not already done)

```bash
cd bt-support-assistant
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download spaCy language model (optional, for advanced NLP)

```bash
python -m spacy download en_core_web_sm
```

### 5. Create environment file

Copy the example environment file and customize it:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` to set your configuration.

## Quick Start

### 1. Build sample indexes for testing

This creates sample ITSM tickets and builds search indexes:

```bash
python scripts/build_sample_index.py
```

### 2. Run the API server

```bash
python scripts/run_server.py
```

Or directly with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the API

- **API Documentation (Swagger):** http://localhost:8000/docs
- **Alternative Documentation (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/v1/health

## Running Tests

Run all tests:

```bash
pytest
```

Run with coverage report:

```bash
pytest --cov=core --cov=app --cov=data_pipeline --cov-report=html
```

View coverage report:

```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

## Project Structure

```
bt-support-assistant/
├── app/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── config.py          # Configuration management
│   └── routers/           # API endpoints
├── core/                  # Core functionality
│   ├── nlp/              # Text preprocessing and intent
│   ├── retrieval/        # BM25, embeddings, hybrid search
│   ├── rag/              # RAG pipeline and prompts
│   └── anomaly/          # Anomaly and drift detection
├── data_pipeline/        # Data ingestion and indexing
│   ├── ingestion.py      # Data ingestion
│   ├── anonymize.py      # PII anonymization
│   └── build_indexes.py  # Index building
├── tests/                # Unit tests
├── scripts/              # Helper scripts
├── models/               # Local model files (not in git)
├── data/                 # Data directory (not in git)
├── indexes/              # Search indexes (not in git)
└── logs/                 # Application logs (not in git)
```

## Next Steps

### 1. Add your ITSM data

Place your ticket data in the `data/` directory and use the ingestion pipeline:

```python
from data_pipeline.ingestion import DataIngestion
from data_pipeline.anonymize import DataAnonymizer
from data_pipeline.build_indexes import IndexBuilder

# Ingest tickets
ingestion = DataIngestion()
tickets = ingestion.ingest_tickets_from_json("data/tickets.json")

# Anonymize
anonymizer = DataAnonymizer(anonymization_enabled=True)
anonymized_tickets = anonymizer.anonymize_tickets(tickets)

# Build indexes
index_builder = IndexBuilder()
documents = index_builder.prepare_documents_for_indexing(anonymized_tickets)
bm25_retriever, embedding_retriever = index_builder.build_hybrid_indexes(documents)
```

### 2. Configure LLM model

The system is designed to work with local LLM models. You'll need to:

1. Download a model (e.g., Mistral 7B)
2. Place it in the `models/` directory
3. Update the `LLM_MODEL_NAME` in your `.env` file
4. Implement the LLM generation in `core/rag/pipeline.py`

### 3. Set up Elasticsearch (optional)

For production use with large datasets, you can set up Elasticsearch:

1. Install Elasticsearch
2. Update `ELASTICSEARCH_URL` in `.env`
3. Use the Elasticsearch client instead of in-memory BM25

## API Usage Examples

### Chat endpoint

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to reset my password?",
    "language": "en"
  }'
```

### Anomaly detection endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/anomaly/detect?hours=24&include_drift=true"
```

## Troubleshooting

### Import errors

Make sure you're in the project root directory and your virtual environment is activated.

### Model download issues

If sentence-transformers models fail to download:
- Check your internet connection
- Try setting HF_HOME environment variable
- Manually download models to `models/` directory

### Memory issues

If you encounter memory errors with large datasets:
- Use smaller batch sizes for embeddings
- Consider using quantized models
- Increase system memory or use a machine with more RAM

## Development

### Code style

We use:
- **black** for code formatting
- **flake8** for linting
- **mypy** for type checking

Run formatters:

```bash
black .
flake8 .
mypy .
```

### Adding new features

1. Create feature branch
2. Implement with tests
3. Ensure all tests pass
4. Update documentation
5. Submit pull request

## Support

For issues and questions:
- Check the documentation in `README.md`
- Review test files for usage examples
- Check logs in `logs/app.log`

