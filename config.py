"""
SmartGrid AI — Centralized Configuration Management
====================================================
Uses Pydantic Settings for type-safe, environment-aware config.
All secrets sourced from environment variables / .env file.
Never hardcode credentials.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL / TimescaleDB connection settings."""

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    name: str = Field(default="smartgrid", alias="DB_NAME")
    user: str = Field(default="sgadmin", alias="DB_USER")
    password: str = Field(default="changeme", alias="DB_PASSWORD")
    pool_min_size: int = Field(default=5, alias="DB_POOL_MIN")
    pool_max_size: int = Field(default=20, alias="DB_POOL_MAX")
    echo_sql: bool = Field(default=False, alias="DB_ECHO_SQL")
    schema: str = Field(default="smartgrid", alias="DB_SCHEMA")

    @property
    def url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Redis cache and Celery broker settings."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB")
    ttl_seconds: int = Field(default=3600, alias="REDIS_TTL")

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class MLSettings(BaseSettings):
    """Machine learning hyperparameter defaults."""

    isolation_forest_contamination: float = Field(default=0.05)
    isolation_forest_n_estimators: int = Field(default=200)
    autoencoder_encoding_dim: int = Field(default=32)
    autoencoder_epochs: int = Field(default=50)
    autoencoder_batch_size: int = Field(default=256)
    autoencoder_anomaly_threshold_sigma: float = Field(default=3.0)
    lstm_sequence_length: int = Field(default=24)  # 24 hours look-back
    lstm_forecast_horizon: int = Field(default=48)  # 48 hours ahead
    lstm_units: int = Field(default=128)
    lstm_epochs: int = Field(default=100)
    xgb_n_estimators: int = Field(default=500)
    xgb_max_depth: int = Field(default=6)
    xgb_learning_rate: float = Field(default=0.05)
    model_artifact_dir: str = Field(default="artifacts/models")
    retrain_threshold_days: int = Field(default=30)


class APISettings(BaseSettings):
    """FastAPI application settings."""

    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=False, alias="API_DEBUG")
    secret_key: str = Field(default="CHANGE_ME_IN_PRODUCTION", alias="API_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30)
    cors_origins: list[str] = Field(default=["http://localhost:3000"])
    api_prefix: str = Field(default="/api/v1")
    docs_url: str = Field(default="/docs")


class IngestionSettings(BaseSettings):
    """Data ingestion configuration."""

    mqtt_broker_host: str = Field(default="localhost", alias="MQTT_HOST")
    mqtt_broker_port: int = Field(default=1883, alias="MQTT_PORT")
    mqtt_topic_pattern: str = Field(default="meters/+/readings")
    mqtt_client_id: str = Field(default="smartgrid-ingestor")
    mqtt_qos: int = Field(default=1)
    batch_size: int = Field(default=1000)
    batch_flush_interval_seconds: int = Field(default=10)
    weather_api_key: Optional[str] = Field(default=None, alias="WEATHER_API_KEY")
    weather_api_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast"
    )


class MATLABSettings(BaseSettings):
    """MATLAB engine integration settings."""

    matlab_root: str = Field(
        default="/usr/local/MATLAB/R2023b", alias="MATLAB_ROOT"
    )
    use_matlab_engine: bool = Field(default=False, alias="USE_MATLAB_ENGINE")
    matlab_timeout_seconds: int = Field(default=120)
    fallback_to_python: bool = Field(default=True)  # Python scipy fallback


class Settings(BaseSettings):
    """Root settings aggregator."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SmartGrid AI"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # json | text

    # Nested settings
    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    ml: MLSettings = MLSettings()
    api: APISettings = APISettings()
    ingestion: IngestionSettings = IngestionSettings()
    matlab: MATLABSettings = MATLABSettings()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()


# Module-level convenience alias
settings = get_settings()