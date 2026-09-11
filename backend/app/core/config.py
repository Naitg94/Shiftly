import os
from typing import List
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Settings:
    PROJECT_NAME: str = "Shiftly API"
    VERSION: str = "0.4.0"
    TAGLINE: str = "Find what matters."

    # Environment, Server & Logging
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Documentation exposure: default to disabled in production unless explicitly set to true
    ENABLE_DOCS: bool = os.getenv(
        "ENABLE_DOCS", 
        "false" if os.getenv("ENVIRONMENT", "").lower() == "production" else "true"
    ).lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Security & Limits
    MAX_INPUT_TEXT_CHARS: int = int(os.getenv("MAX_INPUT_TEXT_CHARS", "200000"))
    MAX_TEXT_CHAR_COUNT: int = MAX_INPUT_TEXT_CHARS
    GUEST_MAX_TEXT_CHAR_COUNT: int = int(os.getenv("GUEST_MAX_TEXT_CHAR_COUNT", "3000"))
    RATE_LIMIT_ANALYZE_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_ANALYZE_PER_MINUTE", "10"))
    RATE_LIMIT_PROJECTS_WRITE_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PROJECTS_WRITE_PER_MINUTE", "30"))
    RATE_LIMIT_RECOVERY_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_RECOVERY_PER_MINUTE", "5"))

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
    DATABASE_URL: str | None = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

    # Supabase Administrative / Service-Role Key for MVP Password Recovery
    # CRITICAL SECURITY REQUIREMENTS:
    # 1. Strictly server-side only; NEVER expose to frontend or NEXT_PUBLIC_* variables.
    # 2. NEVER log, commit, or return this key in API responses.
    # 3. Used exclusively for administrative user lookup and password updates via Supabase Auth GoTrue.
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


settings = Settings()

