# Sentinel-Bench

Sentinel-Bench is a formal empirical benchmark (April 2026) evaluating whether edge-native Small Language Models (SLMs) can function as automated constitutional firewalls for Decentralized Autonomous Organizations (DAOs).

This repository contains the data ingestion pipeline, inference engine, and evaluation suite used to measure **Juridical Entropy**, **Hyper-Regulatory Overreach**, and **Reasoning-Induced Sycophancy** in modern AI architectures.

## Objective

This benchmark isolates inference-time reasoning behavior through a strict intra-model ablation study. We compare:

- **Control Arm (System 1):** `ollama_chat/qwen3.5:9b` with latent reasoning disabled (`think=False`).
- **Experiment Arm (System 2):** `ollama_chat/qwen3.5:9b` with latent reasoning enabled (`think=True`).

Both arms are evaluated across a 3-tier governance dataset (Baseline, Perturbed Sycophancy Traps, and highly contentious Case Studies) sourced authentically from the Optimism Agora API and Discourse forums.

## Hardware & Compute Requirements

Running this benchmark locally requires significant compute resources to accommodate the 16,384 token context window and massive reasoning trace generation:
- **VRAM:** Minimum 10 GB dedicated VRAM or ≥16 GB unified memory (Apple Silicon class). Higher-capacity configurations (>=24 GB VRAM or >=32 GB unified memory) are recommended for optimal performance.
- **Execution Time:** A full 840-inference benchmark run (21 proposals × 20 trials × 2 configurations) takes approximately **24 hours**, ultimately depending on GPU parallelization and reasoning volume.

## Project Structure

```text
sentinel-bench/
├── pyproject.toml
├── .env
├── data/
│   ├── raw/                 # Canonical caches and dated snapshots
│   └── results/             # Benchmark outputs, logs, and plots
├── src/
│   ├── __init__.py
│   ├── config.py            # API routing and model configurations
│   ├── schema.py            # Pydantic ontologies for legal verdicts
│   ├── ingest.py            # Agora API and Discourse JSON fetchers
│   └── engine.py            # DSPy inference and cache-busting logic
└── research_notebook.ipynb  # Main execution and visualization pipeline
```

## Requirements

- Python 3.14
- Poetry
- [Ollama](https://ollama.com/) running locally as a background service (`http://localhost:11434`)
- Models pulled in Ollama:
  - `qwen3.5:9b` (`ollama pull qwen3.5:9b`)

## Environment Setup

1. Add your Optimism Agora API key to `.env`:

```env
AGORA_API_KEY=your_key_here
```

2. Configure Poetry and install dependencies:

```bash
poetry env use python3.14
poetry install
```

3. Register notebook kernel (optional if already available in VS Code/Jupyter):

```bash
poetry run python -m ipykernel install --user --name sentinel-bench --display-name "Sentinel-Bench"
```

## Running the Benchmark

Open and execute `research_notebook.ipynb` sequentially. 

**Data Provenance & Caching:**
The notebook includes a data-source toggle in Cell 2:
- `FORCE_REFRESH_FROM_WEB = False`: Cache-first mode (ensures reproducibility by reusing local snapshots).
- `FORCE_REFRESH_FROM_WEB = True`: Forces fresh API pulls from Agora and Discourse.

If cache reuse is enabled, the pipeline resolves in this order:
1. The explicitly requested date snapshot
2. The latest available dated snapshot
3. Canonical latest cache (`agora_proposals_latest.json`)
4. Live API fetch

## Outputs

All artifacts are generated in the `data/results/` directory:
- **Live benchmark records:** `benchmark_live.csv`
- **Diagnostic smoke-test records:** `diagnostic_live.csv`
- **Runtime telemetry:** `experiment.log`
- **Publication artifacts:** High-DPI Seaborn plots (`*.png`) and LaTeX tables (`tables/*.tex`)

*Note: The Jupyter Notebook includes a robust append-only checkpointing system. If your hardware crashes mid-execution, simply restart the notebook; it will safely resume at the exact trial it dropped.*
