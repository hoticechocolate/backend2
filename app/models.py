from datetime import datetime
from pathlib import PurePosixPath
from typing import Any
from pydantic import BaseModel, Field, field_validator

class SicMap(BaseModel):
    year: int = Field(ge=1900, le=2200)
    month: int = Field(ge=1, le=12)
    observed_path: str | None = None
    predicted_path: str | None = None
    error_path: str | None = None
    created_at: datetime | None = None

    @field_validator('observed_path', 'predicted_path', 'error_path')
    @classmethod
    def relative_path(cls, value):
        if value is None:
            return None
        if not value or value.startswith('/') or '\\' in value or ':' in value or '..' in PurePosixPath(value).parts:
            raise ValueError('Expected a relative storage path')
        return value

class Evaluation(BaseModel):
    experiment_id: str = Field(min_length=1)
    learning_curve: dict[str, Any]
    classification_metrics: dict[str, Any]
    monthly_metrics: list[dict[str, Any]] | None = None
    created_at: datetime | None = None
