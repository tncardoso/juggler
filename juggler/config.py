import yaml
import logging
from typing import Optional
from pydantic import BaseModel
from pathlib import Path


class AnthropicConfig(BaseModel):
    key: str


class OpenAIConfig(BaseModel):
    key: str


class DeepseekConfig(BaseModel):
    key: str


class GeminiConfig(BaseModel):
    key: str


class Config(BaseModel):
    openai: Optional[OpenAIConfig]
    anthropic: Optional[AnthropicConfig]
    deepseek: Optional[DeepseekConfig]
    gemini: Optional[GeminiConfig]


def read_config() -> Config:
    # try to read from config local dir
    # otherwise from ~/.config/juggler/juggler.yaml
    home_dir = Path.home()
    home_config = home_dir.joinpath(".config/juggler/juggler.yaml")
    path = Path(__file__).parent.parent.joinpath("juggler.yaml")

    if not path.exists():
        path = home_config

    logging.info("using config", path)
    with path.open("r") as f:
        raw = yaml.safe_load(f.read())
        return Config(**raw)  # ty: ignore[missing-argument]
