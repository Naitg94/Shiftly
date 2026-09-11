import os
from typing import List
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Settings:
    PROJECT_NAME: str = "Shiftly API"
    VERSION: str = "0.4.0"
    TAGLINE: str = "Find what matters."

    # Environment & Logging
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ENABLE_DOCS: bool = os.getenv("ENABLE_DOCS", "true").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Security & Limits
    MAX_INPUT_TEXT_CHARS: int = int(os.getenv("MAX_INPUT_TEXT_CHARS", "200000"))
    RATE_LIMIT_ANALYZE_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_ANALYZE_PER_MINUTE", "10"))
    RATE_LIMIT_PROJECTS_WRITE_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PROJECTS_WRITE_PER_MINUTE", "30"))

    # CORS
    CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    
    @property
    def cors_origins(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]
        # Never allow wildcard '*' with allow_credentials=True
        filtered = [o for o in origins if o != "*"]
        return filtered if filtered else ["http://localhost:3000"]

    # Gemini
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Supabase PostgreSQL Project Memory
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_PUBLISHABLE_KEY: str | None = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_ANON_KEY: str | None = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")


settings = Settings()

