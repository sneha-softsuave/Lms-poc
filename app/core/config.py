"""Application configuration (env-driven).

Deliberately lean vs the ThinkArguments original: only the settings the Defense
LMS POC needs. The model-provider settings drive the gateway (PRD 4.9) — the
one place the app chooses an AI backend.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Application
    APP_NAME: str = "Defense AI LMS (POC)"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://poc:poc@localhost:5432/defense_lms"

    # Security / JWT
    SECRET_KEY: str = "change-me"
    JWT_SECRET_KEY: str = "change-me-too"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # Bootstrap admin (created on first startup if absent)
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@defense-lms.org"
    BOOTSTRAP_ADMIN_PASSWORD: str = "admin12345"

    # ── Model Gateway (PRD 4.9) ────────────────────────────────────────────────
    # cloud  -> Anthropic Claude + MiniLM embeddings
    # openai -> OpenAI GPT + OpenAI embeddings (needs only the openai package + key)
    # local  -> vLLM/Ollama + BGE/E5 (air-gap phase; stubbed)
    MODEL_PROVIDER: str = "cloud"
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-5"
    GATEWAY_MAX_TOKENS: int = 2048
    GATEWAY_TEMPERATURE: float = 0.0
    # OpenAI provider
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_BASE_URL: str = ""  # optional: Azure/OpenRouter/local OpenAI-compatible endpoint
    # Local provider
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "qwen2.5:7b"

    # Vector store + embeddings
    VECTOR_BACKEND: str = "memory"  # 'qdrant' | 'memory' (memory = no external Qdrant needed)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Chatbot retrieval (RAG)
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    RETRIEVAL_TOP_K: int = 4
    ABSTAIN_THRESHOLD: float = 0.25  # top cosine below this -> chatbot abstains
    # Generated lessons are a lossy summary of the uploaded document, so the raw
    # source segments are indexed too and retrieved as a supplement. Reviewed course
    # material still leads the context; these are the extra source blocks appended.
    INDEX_SOURCE_DOCUMENT: bool = True
    SOURCE_RETRIEVAL_TOP_K: int = 4
    COMPONENT_SOURCE_TOP_K: int = 6  # 3D component explainer wants more source detail
    # Lesson awareness: chunks from the lesson the learner is currently on are
    # preferred, but only as a re-rank nudge — a hard filter would break the many
    # legitimate questions whose answer lives in a different lesson.
    LESSON_BOOST: float = 0.05
    LESSON_CANDIDATE_MULTIPLIER: int = 3  # over-fetch so the boost has room to promote
    # Multi-turn: prior exchanges included in the prompt so follow-ups ("and its
    # range?") resolve. Retrieval still embeds the raw question - see the note in
    # ChatbotService._history.
    CHAT_HISTORY_TURNS: int = 3
    CHAT_HISTORY_CHAR_CAP: int = 400  # per message, keeps long threads bounded

    # Object storage (MinIO / S3-compatible)
    STORAGE_PROVIDER: str = "minio"  # 'minio' | 'local'
    MINIO_ENDPOINT_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "defense-lms"
    LOCAL_STORAGE_PATH: str = "media"

    # Content extraction / OCR
    CONTENT_EXTRACTION_MAX_FILE_SIZE: int = 20 * 1024 * 1024
    TESSERACT_PATH: str = ""
    POPPLER_PATH: str = ""


settings = Settings()
