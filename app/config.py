import yaml
from .models import Config

def load_config() -> Config:
    with open("config.yaml", "r") as f:
        config_dict = yaml.safe_load(f)
    return Config(**config_dict) 