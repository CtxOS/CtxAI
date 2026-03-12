import pytest
from ctxai.core.common.metrics import MetricsManager, Counter, Gauge

def test_counter():
    manager = MetricsManager()
    # Use a unique name to avoid interference if tests run in same process
    name = "test_counter_total"
    counter = manager.counter(name, "Test counter", ["label1"])
    
    counter.inc(1.0, {"label1": "val1"})
    counter.inc(2.0, {"label1": "val1"})
    counter.inc(1.0, {"label1": "val2"})
    
    prom = manager.get_prometheus_metrics()
    assert f'# HELP {name} Test counter' in prom
    assert f'# TYPE {name} counter' in prom
    assert f'{name}{{label1="val1"}} 3.0' in prom
    assert f'{name}{{label1="val2"}} 1.0' in prom

def test_gauge():
    manager = MetricsManager()
    name = "test_gauge_current"
    gauge = manager.gauge(name, "Test gauge", ["label1"])
    
    gauge.set(10.0, {"label1": "val1"})
    gauge.set(20.0, {"label1": "val2"})
    gauge.set(15.0, {"label1": "val1"})
    
    prom = manager.get_prometheus_metrics()
    assert f'# TYPE {name} gauge' in prom
    assert f'{name}{{label1="val1"}} 15.0' in prom
    assert f'{name}{{label1="val2"}} 20.0' in prom

def test_singleton():
    m1 = MetricsManager()
    m2 = MetricsManager()
    assert m1 is m2
