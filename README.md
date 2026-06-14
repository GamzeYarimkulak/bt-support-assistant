# BT Support Assistant

Context-aware BT support assistant prototype with hybrid retrieval and anomaly detection.

## Scope

This repository contains the application code, data preparation scripts, indexing pipeline, retrieval evaluation, anomaly evaluation, frontend UI, and report artifacts for the bitirme/TÜBİTAK-oriented prototype.

The project is designed around two main capabilities:

- Hybrid RAG for IT support tickets and KB documents using BM25 + FAISS.
- Window-based anomaly detection for support-ticket streams using volume, category distribution, and semantic drift signals.

Large local artifacts are intentionally not committed:

- `data/`
- `indexes/`
- `.env`
- cache and test output folders

These files are generated locally by the preparation, indexing, and evaluation scripts.

## Main Commands

Prepare processed data:

```powershell
python scripts\prepare_data_for_indexing.py
```

Build indexes:

```powershell
python data_pipeline\build_indexes.py
```

Build a limited demo index:

```powershell
python data_pipeline\build_indexes.py --limit 10000
```

Evaluate retrieval:

```powershell
python scripts\evaluate_retrieval.py
```

Evaluate anomaly detection:

```powershell
python scripts\evaluate_anomaly.py
```

Run the web app:

```powershell
python scripts\run_server.py
```

Then open:

```text
http://127.0.0.1:8010/
```

## Current Evaluation Summary

The latest controlled retrieval evaluation used 180 queries over a 34,975-document index.

Key retrieval results:

- Strategy Recall@5: 0.8500
- Strategy Recall@10: 0.9111
- Strategy nDCG@10: 0.7566
- Category Hit@5: 0.9611
- Subcategory Hit@5: 0.8611

The anomaly validation set contains an independent synthetic day-level stream with positive and negative days.

Key anomaly results:

- Event precision: 0.8605
- Event recall: 0.9487
- Event F1: 0.9024
- Day-level specificity: 0.9469

These values are prototype validation results, not production-field measurements.

## Important Paths

- Backend routes: `app/routers/`
- Retrieval logic: `core/retrieval/`
- RAG pipeline: `core/rag/`
- Anomaly engine: `core/anomaly/`
- Data preparation: `scripts/prepare_data_for_indexing.py`
- Index building: `data_pipeline/build_indexes.py`
- Retrieval evaluation: `scripts/evaluate_retrieval.py`
- Anomaly evaluation: `scripts/evaluate_anomaly.py`
- Frontend: `frontend/`
- Report notes and visuals: `reports/`

## Notes

The repository intentionally avoids committing generated datasets, indexes, environment variables, and cache files. To reproduce the full local demo, regenerate `data/processed` and `indexes` with the scripts above.
