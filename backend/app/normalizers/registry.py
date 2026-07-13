from __future__ import annotations

from typing import Dict, Optional, Type

from .base import BaseNormalizer


class NormalizerRegistry:
    def __init__(self):
        self._normalizers: Dict[str, Type[BaseNormalizer]] = {}

    def register(self, normalizer_cls: Type[BaseNormalizer]) -> Type[BaseNormalizer]:
        self._normalizers[normalizer_cls.name] = normalizer_cls
        return normalizer_cls

    def get_normalizer(self, connector_name: str) -> Optional[Type[BaseNormalizer]]:
        return self._normalizers.get(connector_name)


registry = NormalizerRegistry()
