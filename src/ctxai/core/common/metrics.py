import time
import threading
from typing import Dict, Any, List

class Metric:
    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()

    def _get_label_tuple(self, labels: Dict[str, str]) -> tuple:
        return tuple(labels.get(l, "") for l in self.labels)

class Counter(Metric):
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        label_tuple = self._get_label_tuple(labels or {})
        with self._lock:
            self._values[label_tuple] = self._values.get(label_tuple, 0.0) + value

class Gauge(Metric):
    def set(self, value: float, labels: Dict[str, str] = None):
        label_tuple = self._get_label_tuple(labels or {})
        with self._lock:
            self._values[label_tuple] = value

class MetricsManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetricsManager, cls).__new__(cls)
                cls._instance._metrics: Dict[str, Metric] = {}
        return cls._instance

    def counter(self, name: str, description: str, labels: List[str] = None) -> Counter:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name, description, labels)
            return self._metrics[name]

    def gauge(self, name: str, description: str, labels: List[str] = None) -> Gauge:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name, description, labels)
            return self._metrics[name]

    def get_prometheus_metrics(self) -> str:
        lines = []
        with self._lock:
            for name, metric in self._metrics.items():
                lines.append(f"# HELP {name} {metric.description}")
                lines.append(f"# TYPE {name} {'counter' if isinstance(metric, Counter) else 'gauge'}")
                for labels, value in metric._values.items():
                    label_str = ",".join([f'{l}="{v}"' for l, v in zip(metric.labels, labels)])
                    if label_str:
                        lines.append(f"{name}{{{label_str}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
        return "\n".join(lines) + "\n"

metrics = MetricsManager()
