from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field


class NormalizedFact(BaseModel):
    fact_type: str
    value: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None
    source_connector: str
    raw_reference: Optional[str] = None


class BaseNormalizer(ABC):
    name: ClassVar[str]

    @abstractmethod
    def normalize(self, raw_payload: dict, source_connector: str) -> List[NormalizedFact]:
        pass
