"""
GeoViable — Application Configuration

Loads settings from environment variables via pydantic-settings.
All values come from the .env file (or Docker Compose environment).
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration loaded from environment variables.

    Uses pydantic-settings to read from the process environment.
    Values are populated from the .env file automatically via Docker Compose.
    """

    # ── Database ──
    database_url: str
    """SQLAlchemy connection string.
    Example: postgresql+psycopg2://geoviable:pass@geoviable-db:5432/geoviable
    """

    # ── Runtime ──
    environment: str = "production"
    """Runtime environment: 'production' or 'development'."""

    log_level: str = "INFO"
    """Python logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL."""

    # ── Spatial Analysis Limits ──
    max_polygon_area_km2: float = 100.0
    """Maximum allowed polygon area in square kilometers."""

    max_polygon_vertices: int = 10000
    """Maximum number of vertices in a single polygon."""

    max_upload_size_mb: int = 5
    """Maximum request body size in megabytes."""

    query_timeout_seconds: int = 30
    """PostgreSQL statement timeout in seconds."""

    # ── CORS ──
    cors_origins: str = ""
    """Comma-separated list of allowed CORS origins.
    Example: "https://geoviable.movilab.es,http://localhost:3000"
    """

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a Python list, filtering empty strings."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB limit to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_polygon_area_m2(self) -> float:
        """Convert km² limit to square meters."""
        return self.max_polygon_area_km2 * 1_000_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Using lru_cache avoids re-parsing .env on every import.
    In production (Docker), the values are already in the environment.
    """
    return Settings()
