"""
Configuration for RAG (Retrieval-Augmented Generation) & Gemini LLM Pipeline.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"
KEY_FILE = BASE_DIR / "gemini_key.txt"


class RAGConfig:
    CHROMA_PERSIST_DIR: str = str(CHROMA_DIR)
    GEMINI_MODEL: str = "gemini-3.5-flash"
    DEFAULT_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    MAX_CONTEXT_CHUNKS: int = 5
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 40

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Loads Gemini API key from key file, environment variable, or .env (Prioritizes user key file)."""
        # 1. Key file under RAG/gemini_key.txt (Highest Priority: User's explicitly configured key)
        if KEY_FILE.exists():
            try:
                key = KEY_FILE.read_text(encoding="utf-8").strip()
                if key and len(key) > 10:
                    return key
            except Exception:
                pass

        # 2. Environment variable GEMINI_API_KEY
        env_gemini = os.environ.get("GEMINI_API_KEY")
        if env_gemini and len(env_gemini.strip()) > 10:
            return env_gemini.strip()

        # 3. Project root .env for GEMINI_API_KEY
        env_path = BASE_DIR.parent / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if len(val) > 10:
                            return val
            except Exception:
                pass

        # 4. Fallback: GOOGLE_API_KEY
        env_google = os.environ.get("GOOGLE_API_KEY")
        if env_google and len(env_google.strip()) > 10:
            return env_google.strip()

        return None

    @classmethod
    def save_api_key(cls, key: str) -> bool:
        """Saves user-provided Gemini API key to RAG/gemini_key.txt for permanent reuse."""
        try:
            cleaned = key.strip()
            KEY_FILE.write_text(cleaned, encoding="utf-8")
            os.environ["GEMINI_API_KEY"] = cleaned
            return True
        except Exception:
            return False

    @classmethod
    def has_api_key(cls) -> bool:
        return cls.get_api_key() is not None
