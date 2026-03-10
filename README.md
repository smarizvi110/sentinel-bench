# Sentinel-Bench

Sentinel-Bench is a formal benchmark (April 2026) for evaluating whether edge-native SLMs can function as automated constitutional firewalls for DAO governance.

## Objective

This benchmark isolates inference-time reasoning behavior by comparing:

- Control model: `ollama_chat/llama3.1:8b`
- Experiment model: `ollama_chat/deepseek-r1:8b`

Both are evaluated on a 3-tier governance dataset with repeated adjudication trials.

## Project Structure

```text
sentinel-bench/
├── pyproject.toml
├── .env
├── data/
│   ├── raw/
│   └── results/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── schema.py
│   ├── ingest.py
│   └── engine.py
└── research_notebook.ipynb
```

## Requirements

- Python 3.14
- Poetry
- Ollama running locally on `http://localhost:11434`
- Models pulled in Ollama:
  - `llama3.1:8b`
  - `deepseek-r1:8b`

## Environment Setup

1. Add your Agora key to `.env`:

```env
AGORA_API_KEY=your_key_here
```

2. Configure Poetry and install dependencies:

```bash
poetry env use python3.14
poetry install
```

3. Register notebook kernel (optional if already available):

```bash
poetry run python -m ipykernel install --user --name sentinel-bench --display-name "Sentinel-Bench"
```

## Running the Benchmark

Open and run `research_notebook.ipynb` from top to bottom.

The notebook includes a data-source toggle in Cell 2:

- `FORCE_REFRESH_FROM_WEB = False`: cache-first mode (reuse local snapshots when available)

To force fresh API pulls, set:

- `FORCE_REFRESH_FROM_WEB = True`

## Dated Storage and Reuse

Ingestion writes dated snapshots under:

- `data/raw/snapshots/YYYY-MM-DD/context.txt`
- `data/raw/snapshots/YYYY-MM-DD/agora_proposals.json`
- `data/raw/snapshots/YYYY-MM-DD/benchmark_dataset.json`

Canonical latest caches are also written to:

- `data/raw/context.txt`
- `data/raw/agora_proposals_latest.json`
- `data/raw/benchmark_dataset.json`

If cache reuse is enabled, the pipeline tries:

1. The explicitly requested date snapshot
2. The latest available dated snapshot
3. Canonical latest cache
4. API fetch (if not forcing offline reuse)

## Outputs

- Live benchmark records: `data/results/benchmark_live.csv`
- Runtime log file: `data/results/experiment.log`

## Notes

- `build_scientific_dataset` guarantees 21 total records: 10 baseline, 10 perturbed, 1 case study.
- Checkpointing in the notebook allows interrupted benchmark runs to resume safely.
