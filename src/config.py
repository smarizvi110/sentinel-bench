import os
from dotenv import load_dotenv

load_dotenv()

MODELS = {
    "control": "ollama_chat/llama3.1:8b",
    "experiment": "ollama_chat/deepseek-r1:8b"
}

WORKING_CONSTITUTION_URL = "https://gov.optimism.io/t/55.json"
AGORA_API_URL = "https://vote.optimism.io/api/v1/proposals"
AGORA_API_KEY = os.getenv("AGORA_API_KEY")
AGORA_PAGE_SIZE = 10

TARGET_BASELINE_SIZE = 10
TRIALS_PER_PROPOSAL = 20  # Statistically robust for Self-Consistency evaluation
