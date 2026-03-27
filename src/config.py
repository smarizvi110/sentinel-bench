from pathlib import Path

import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RESULTS_DIR = DATA_DIR / "results"

MODELS = {
    "control": "ollama_chat/qwen3.5:9b",
    "experiment": "ollama_chat/qwen3.5:9b",
}

MODEL_THINK_SETTINGS = {
    "control": False,
    "experiment": True,
}

MODEL_DISPLAY_NAMES = {
    ("ollama_chat/qwen3.5:9b", False): "Qwen-3.5 (9B, Think Off)",
    ("ollama_chat/qwen3.5:9b", True): "Qwen-3.5 (9B, Think On)",
}

WORKING_CONSTITUTION_URL = "https://gov.optimism.io/t/55.json"
AGORA_API_URL = "https://vote.optimism.io/api/v1/proposals"
AGORA_API_KEY = os.getenv("AGORA_API_KEY")
AGORA_PAGE_SIZE = 10

TARGET_BASELINE_SIZE = 10
TRIALS_PER_PROPOSAL = 20  # Statistically robust for Self-Consistency evaluation


def get_lite_llm_name(model_name: str) -> str:
    # Preserve explicit LiteLLM provider prefixes as-is.
    if model_name.startswith(("ollama_chat/", "ollama/", "openai/")):
        return model_name

    # Fallback for bare Ollama model names.
    if "ollama" in model_name:
        return f"ollama_chat/{model_name.split('/')[-1]}"
    return model_name


def get_model_think_setting(model_type: str) -> bool | None:
    return MODEL_THINK_SETTINGS.get(model_type)


def get_model_display_name(
    model_name: str,
    *,
    model_type: str | None = None,
    think: bool | None = None,
) -> str:
    inferred_think = think
    if inferred_think is None and model_type is not None:
        inferred_think = MODEL_THINK_SETTINGS.get(model_type)

    keyed = MODEL_DISPLAY_NAMES.get((model_name, inferred_think))
    if keyed:
        return keyed

    return model_name
