"""
All configuration in one place
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
STOCK_API_KEY = os.getenv("STOCK_API_KEY")

# Settings
COLLECTION_NAME = "langgraph_memory"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "openai/gpt-4o-mini"
MAX_TOKENS = 1000
DB_PATH = "data/chatbot.db"

# ============ Authentication ============
PASSWORD_SALT = "your_secret_salt_change_this_123456"  # CHANGE THIS!

# ============ File Upload ============
UPLOAD_FOLDER = "uploads"
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']

# Check if important keys exist
def check_config():
    """Make sure API keys are loaded"""
    if not OPENROUTER_API_KEY:
        print("⚠️ Warning: OPENROUTER_API_KEY not found in .env")
    if not QDRANT_URL:
        print("⚠️ Warning: QDRANT_URL not found in .env")
    print("✅ Configuration loaded")

check_config()