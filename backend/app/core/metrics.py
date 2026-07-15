from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class InvestigationMetrics:
    investigation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    connector_count: int = 0
    connector_failures: int = 0
    normalized_fact_count: int = 0
    correlated_entity_count: int = 0
    graph_node_count: Optional[int] = None


class MetricsCollector:
    def __init__(self):
        self._metrics: Dict[str, InvestigationMetrics] = {}
    
    def start_investigation(self, investigation_id: str) -> InvestigationMetrics:
        metrics = InvestigationMetrics(
            investigation_id=investigation_id,
            start_time=datetime.utcnow()
        )
        self._metrics[investigation_id] = metrics
        return metrics
    
    def complete_investigation(self, investigation_id: str):
        if investigation_id in self._metrics:
            metrics = self._metrics[investigation_id]
            metrics.end_time = datetime.utcnow()
            metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
    
    def record_connector_execution(self, investigation_id: str, success: bool):
        if investigation_id in self._metrics:
            metrics = self._metrics[investigation_id]
            metrics.connector_count += 1
            if not success:
                metrics.connector_failures += 1
    
    def record_normalized_facts(self, investigation_id: str, count: int):
        if investigation_id in self._metrics:
            self._metrics[investigation_id].normalized_fact_count = count
    
    def record_correlated_entities(self, investigation_id: str, count: int):
        if investigation_id in self._metrics:
            self._metrics[investigation_id].correlated_entity_count = count
    
    def record_graph_nodes(self, investigation_id: str, count: int):
        if investigation_id in self._metrics:
            self._metrics[investigation_id].graph_node_count = count
    
    def get_metrics(self, investigation_id: str) -> Optional[InvestigationMetrics]:
        return self._metrics.get(investigation_id)
    
    def get_all_metrics(self) -> Dict[str, InvestigationMetrics]:
        return self._metrics.copy()


metrics_collector = MetricsCollector()
