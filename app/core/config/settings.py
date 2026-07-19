"""Typed configuration management for AgentSphere OS v4 using Pydantic V2."""

from __future__ import annotations

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Runtime settings for the AgentSphere OS Microkernel.

    Loads values from environment variables and an optional .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Configuration
    app_name: str = Field(default="AgentSphere OS", description="Name of the OS runtime")
    app_version: str = Field(default="4.0.0", description="OS semantic version")
    environment: str = Field(default="production", description="Runtime environment (development/testing/production)")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Uvicorn server host binding")
    port: int = Field(default=8000, description="Uvicorn server port binding")
    
    # Logging
    log_level: str = Field(default="INFO", description="Global log level (DEBUG/INFO/WARNING/ERROR)")
    log_format: str = Field(default="json", description="Log output format (json or text)")

    # Storage and Cache
    database_path: str = Field(default="checkpoints.sqlite", description="SQLite database path")
    redis_url: Optional[str] = Field(default=None, description="Redis server connection URL")
    event_log_path: str = Field(default="events.jsonl", description="File path for standard event log persistence")
    dlq_log_path: str = Field(default="dlq.jsonl", description="File path for DLQ log persistence")


    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable API and process performance tracking")

    # Qwen Cloud Configurations
    qwen_base_url: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        description="Alibaba Qwen Cloud API endpoint compatibility layer",
    )
    qwen_api_key: Optional[str] = Field(default=None, description="Qwen API Auth Key")
    qwen_model: str = Field(default="qwen3.7-plus", description="Default/fallback model")
    qwen_model_max: str = Field(default="qwen3.7-max", description="High-quality reasoning model (planning, coding, review)")
    qwen_model_plus: str = Field(default="qwen3.7-plus", description="Standard quality model (script, storyboard, audio)")
    qwen_max_retries: int = Field(default=3, description="Model endpoint API failure retries")
    qwen_timeout: float = Field(default=60.0, description="Model API request timeout in seconds")

    # Video generation (Wan / HappyHorse)
    wan_video_model: str = Field(default="happyhorse-1.1-t2v", description="Wan/HappyHorse T2V model ID")
    happyhorse_t2v_model: str = Field(default="happyhorse-1.1-t2v", description="HappyHorse Text-to-Video model ID")
    happyhorse_i2v_model: str = Field(default="happyhorse-1.1-i2v", description="HappyHorse Image-to-Video model ID")

    # Image generation
    qwen_image_model: str = Field(default="wanx-v1", description="Qwen image generation model ID")

