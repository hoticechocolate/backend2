"""Read one config file and inject typed settings into application classes."""
import json
import os
from pathlib import Path
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]

class DatabaseConfig(BaseModel):
    uri: str
    name: str = Field(min_length=1)

class StorageConfig(BaseModel):
    base_url: str

class WebConfig(BaseModel):
    host: str = '127.0.0.1'
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins: list[str] = []

class AdminConfig(BaseModel):
    host: str = '127.0.0.1'
    port: int = Field(default=8001, ge=1, le=65535)
    token_env: str = 'POLARICE_ADMIN_TOKEN'

class Settings(BaseModel):
    database: DatabaseConfig
    storage: StorageConfig
    web: WebConfig
    admin: AdminConfig

    @model_validator(mode='after')
    def distinct_ports(self):
        if self.web.port == self.admin.port:
            raise ValueError('Web and admin ports must differ')
        return self

    @classmethod
    def load(cls, path: str | Path | None = None):
        source = Path(path or os.environ.get('POLARICE_CONFIG', ROOT / 'config/local.example.json'))
        values = json.loads(source.read_text(encoding='utf-8-sig'))
        if os.environ.get('POLARICE_MONGODB_URI'):
            values['database']['uri'] = os.environ['POLARICE_MONGODB_URI']
        return cls.model_validate(values)
