from pydantic import BaseModel
from typing import Dict, List, Optional

class UpstreamConfig(BaseModel):
    name: str
    priority: int
    base_url: str
    api_key: str
    model_mapping: Dict[str, str]
    timeout: int

class Settings(BaseModel):
    api_key: str

class Config(BaseModel):
    upstream_services: List[UpstreamConfig]
    settings: Settings 