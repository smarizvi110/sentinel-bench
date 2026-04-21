# Sentinel-Bench

[![arXiv](https://img.shields.io/badge/arXiv-2604.16913-b31b1b.svg)](https://arxiv.org/abs/2604.16913)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/release/python-3140/)
[![License: Custom Academic](https://img.shields.io/badge/License-Academic_Pre--Publication-red.svg)](#license)

**Sentinel-Bench** is the empirical evaluation suite for the working paper:  
> **[The Cognitive Penalty: Ablating System 1 and System 2 Reasoning in Edge-Native SLMs for Decentralized Consensus](https://arxiv.org/abs/2604.16913)**

This repository contains the data ingestion pipeline, inference engine, and evaluation suite used to measure **Juridical Consistency**, **Reasoning Non-Convergence**, and **Reasoning-Induced Sycophancy** in modern AI architectures acting as automated constitutional firewalls for Decentralized Autonomous Organizations (DAOs).

## Objective

This benchmark isolates inference-time reasoning behavior through a strict intra-model ablation study on the Qwen-3.5-9B architecture. We compare:

- **Control Arm (System 1):** `ollama_chat/qwen3.5:9b` with latent reasoning disabled (`think=False`).
- **Experiment Arm (System 2):** `ollama_chat/qwen3.5:9b` with latent reasoning enabled (`think=True`).

Both arms are evaluated across a 3-tier governance dataset (Baseline, Perturbed Sycophancy Traps, and highly contentious Case Studies) sourced authentically from the Optimism Agora REST API and Discourse JSON endpoints.

## Hardware & Compute Requirements

Running this benchmark locally requires significant compute resources to accommodate the 16,384 token context window and massive reasoning trace generation:
- **VRAM:** Minimum 10 GB dedicated VRAM or ≥16 GB unified memory (Apple Silicon class). Higher-capacity configurations (≥24 GB VRAM or ≥32 GB unified memory) are highly recommended.
- **Execution Time:** A full 840-inference benchmark run (21 proposals × 20 trials × 2 configurations) takes approximately **24–26 hours**, heavily dependent on GPU memory bandwidth and System 2 reasoning volume.

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

## Environment Setup

1. **Prerequisites:** 
   - Python 3.14
   - [Poetry](https://python-poetry.org/)
   - [Ollama](https://ollama.com/) running locally as a background service (`http://localhost:11434`)

2. **Pull the Model:**
```bash
ollama pull qwen3.5:9b
```

3. **Configure the Environment:**
Add your Optimism Agora API key to `.env`:
```env
AGORA_API_KEY=your_key_here
```

4. **Install Dependencies:**
```bash
poetry env use python3.14
poetry install
```

5. **Register Notebook Kernel:**
```bash
poetry run python -m ipykernel install --user --name sentinel-bench --display-name "Sentinel-Bench"
```

## Running the Benchmark

Open and execute `research_notebook.ipynb` sequentially. 

**Data Provenance & Caching:**
The notebook includes a data-source toggle in Cell 2:
- `FORCE_REFRESH_FROM_WEB = False`: Cache-first mode (ensures reproducibility by reusing local snapshots).
- `FORCE_REFRESH_FROM_WEB = True`: Forces fresh API pulls from Agora and Discourse.

*Note: The Jupyter Notebook includes a robust append-only checkpointing system. If your hardware crashes or thermal-throttles mid-execution, simply restart the notebook; it will safely resume at the exact trial it dropped using the RNG seed.*

## Citation

If you reference this benchmark, dataset, or use this code for academic comparison, please cite the associated working paper:

```bibtex
@misc{rizvi2026cognitivepenaltyablating1,
      title={The Cognitive Penalty: Ablating System 1 and System 2 Reasoning in Edge-Native SLMs for Decentralized Consensus}, 
      author={Syed Muhammad Aqdas Rizvi},
      year={2026},
      eprint={2604.16913},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2604.16913}, 
}
```

## Contact & Collaboration
I am actively seeking to collaborate with researchers. If you are interested in discussing these findings, proposing architectural modifications, or utilizing this framework, please reach out!

**Syed Muhammad Aqdas Rizvi**

Independent Researcher | Alumnus, LUMS

Website: [smarizvi110.com](https://smarizvi110.com/)

Email: [25100166@lums.edu.pk](mailto:25100166@lums.edu.pk) | [s.muhammadaqdasrizvi@gmail.com](mailto:s.muhammadaqdasrizvi@gmail.com)
