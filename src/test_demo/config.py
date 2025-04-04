"""
Configuration module with API keys and settings.
"""

# Database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "graphdb"
DB_USER = "admin"

# API Keys (sensitive information)
GITHUB_API_KEY = "ghp_12345abcdefABCDEF67890ghijklmnopqrstuv"  # This should be detected as a secret
OPENAI_API_KEY = "sk-abcdef1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # This should be detected as a secret

# Application settings
DEBUG = True
LOG_LEVEL = "INFO"
MAX_CONNECTIONS = 100

def get_database_url():
    """Return the database URL."""
    return f"postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_api_credentials():
    """Return API credentials (for demonstration only)."""
    return {
        "github": {"api_key": GITHUB_API_KEY},
        "openai": {"api_key": OPENAI_API_KEY}
    } 