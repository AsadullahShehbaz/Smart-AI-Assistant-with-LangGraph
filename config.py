"""
All configuration in one place
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ================= API Keys =================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
STOCK_API_KEY = os.getenv("STOCK_API_KEY")

# ================= Settings =================
COLLECTION_NAME = "langgraph_memory"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "openai/gpt-4o-mini"
MAX_TOKENS = 1000

# ================= Database Path =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "chatbot.db")

# ================= Config Check =================
def check_config():
    if not OPENROUTER_API_KEY:
        print("⚠️ Warning: OPENROUTER_API_KEY not found in .env")
    if not QDRANT_URL:
        print("⚠️ Warning: QDRANT_URL not found in .env")
    print("✅ Configuration loaded")

check_config()
