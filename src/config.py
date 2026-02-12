import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Project Paths ---
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

# Ensure directories exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Files ---
RECIPES_FILE = INPUT_DIR / "recipes.parquet"  
PERSONAS_FILE = OUTPUT_DIR / "personas.json"
RECOMMENDATIONS_FILE = OUTPUT_DIR / "recommendations.json"

# --- Model Settings ---
EMBEDDING_MODEL_NAME = "thenlper/gte-small"
LLM_MODEL_NAME = "gpt-4o"  # or "gpt-5.2"

# --- Parameters ---
CONSIDERATION_SET_SIZE = 100  # Number of candidates sent to Stage 2
FINAL_K = 6                  # Number of final recommendations