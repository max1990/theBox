"""
Performance Monitoring for TheBox
================================

Performance probes, metrics collection, and fail-open behavior
for production deployment monitoring.
"""

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager

import structlog
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    name: str
    warning_threshold: float
    critical_threshold: float
    unit: str = ""
    description: str = ""


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.thresholds: Dict[str, PerformanceThreshold] = {}
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.lock = threading.Lock()
        self.start_time = time.time()
        
        # Performance counters
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.gauges: Dict[str, float] = {}
        
        # Fail-open state
        self.fail_open = False
        self.fail_open_reason = ""
        
    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric"""
        with self.lock:
            self.metrics.append(metric)
            self._check_thresholds(metric)
            
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self.lock:
            self.counters[name] += value
            
        self.add_metric(PerformanceMetric(
            name=f"{name}_count",
            value=self.counters[name],
            timestamp=time.time(),
            tags=tags or {},
            unit="count"
        ))
        
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        with self.lock:
            self.gauges[name] = value
            
        self.add_metric(PerformanceMetric(
            name=f"{name}_gauge",
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            unit="gauge"
        ))
        
    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric"""
        with self.lock:
            self.timers[name].append(duration)
            # Keep only last 1000 measurements
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
                
        self.add_metric(PerformanceMetric(
            name=f"{name}_duration",
            value=duration,
            timestamp=time.time(),
            tags=tags or {},
            unit="seconds"
        ))
        
    def set_threshold(self, threshold: PerformanceThreshold):
        """Set a performance threshold"""
        self.thresholds[threshold.name] = threshold
        
    def add_callback(self, threshold_name: str, callback: Callable):
        """Add a callback for threshold violations"""
        self.callbacks[threshold_name].append(callback)
        
    def _check_thresholds(self, metric: PerformanceMetric):
        """Check if metric violates any thresholds"""
        if metric.name not in self.thresholds:
            return
            
        threshold = self.thresholds[metric.name]
        
        if metric.value >= threshold.critical_threshold:
            self._trigger_callback(threshold.name, "critical", metric)
        elif metric.value >= threshold.warning_threshold:
            self._trigger_callback(threshold.name, "warning", metric)
            
    def _trigger_callback(self, threshold_name: str, level: str, metric: PerformanceMetric):
        """Trigger callbacks for threshold violations"""
        for callback in self.callbacks[threshold_name]:
            try:
                callback(threshold_name, level, metric)
            except Exception as e:
                logger.error("Callback failed", threshold=threshold_name, error=str(e))
                
    def get_metrics(self, name: Optional[str] = None, limit: int = 100) -> List[PerformanceMetric]:
        """Get recent metrics"""
        with self.lock:
            if name:
                return [m for m in self.metrics if m.name == name][-limit:]
            return list(self.metrics)[-limit:]
            
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        with self.lock:
            uptime = time.time() - self.start_time
            
            # Calculate rates
            rates = {}
            for name, count in self.counters.items():
                rates[f"{name}_rate"] = count / uptime if uptime > 0 else 0
                
            # Calculate timer statistics
            timer_stats = {}
            for name, durations in self.timers.items():
                if durations:
                    timer_stats[f"{name}_avg"] = sum(durations) / len(durations)
                    timer_stats[f"{name}_min"] = min(durations)
                    timer_stats[f"{name}_max"] = max(durations)
                    timer_stats[f"{name}_p95"] = sorted(durations)[int(len(durations) * 0.95)]
                    
            return {
                "uptime_seconds": uptime,
                "metrics_count": len(self.metrics),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "rates": rates,
                "timer_stats": timer_stats,
                "fail_open": self.fail_open,
                "fail_open_reason": self.fail_open_reason
            }
            
    def set_fail_open(self, reason: str):
        """Set fail-open state"""
        self.fail_open = True
        self.fail_open_reason = reason
        logger.warning("Fail-open mode activated", reason=reason)
        
    def clear_fail_open(self):
        """Clear fail-open state"""
        self.fail_open = False
        self.fail_open_reason = ""
        logger.info("Fail-open mode cleared")


class PerformanceProbe:
    """Performance probe decorator and context manager"""
    
    def __init__(self, monitor: PerformanceMonitor, name: str, tags: Optional[Dict[str, str]] = None):
        self.monitor = monitor
        self.name = name
        self.tags = tags or {}
        
    def __call__(self, func):
        """Decorator for function timing"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                self.monitor.record_timer(self.name, duration, self.tags)
                return result
            except Exception as e:
                duration = time.time() - start_time
                self.monitor.record_timer(f"{self.name}_error", duration, self.tags)
                self.monitor.increment_counter(f"{self.name}_errors", tags=self.tags)
                raise
        return wrapper
        
    def __enter__(self):
        """Context manager entry"""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        duration = time.time() - self.start_time
        if exc_type:
            self.monitor.record_timer(f"{self.name}_error", duration, self.tags)
            self.monitor.increment_counter(f"{self.name}_errors", tags=self.tags)
        else:
            self.monitor.record_timer(self.name, duration, self.tags)


class FailOpenManager:
    """Manages fail-open behavior for critical components"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.components: Dict[str, Dict[str, Any]] = {}
        self.fail_open_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "response_time": 5.0,  # 5 seconds
            "memory_usage": 0.9,  # 90% memory usage
            "cpu_usage": 0.9,  # 90% CPU usage
        }
        
    def register_component(self, name: str, critical: bool = True):
        """Register a component for monitoring"""
        self.components[name] = {
            "critical": critical,
            "error_count": 0,
            "total_requests": 0,
            "last_error": None,
            "fail_open": False
        }
        
    def record_success(self, component: str):
        """Record successful operation"""
        if component in self.components:
            self.components[component]["total_requests"] += 1
            
    def record_error(self, component: str, error: Exception):
        """Record failed operation"""
        if component in self.components:
            self.components[component]["error_count"] += 1
            self.components[component]["last_error"] = str(error)
            self.components[component]["total_requests"] += 1
            
            # Check if component should fail open
            self._check_fail_open(component)
            
    def _check_fail_open(self, component: str):
        """Check if component should fail open"""
        comp = self.components[component]
        
        if not comp["critical"]:
            return
            
        # Calculate error rate
        if comp["total_requests"] > 0:
            error_rate = comp["error_count"] / comp["total_requests"]
            
            if error_rate >= self.fail_open_thresholds["error_rate"]:
                comp["fail_open"] = True
                self.monitor.set_fail_open(f"Component {component} error rate too high: {error_rate:.2%}")
                logger.error("Component failed open", component=component, error_rate=error_rate)
                
    def is_fail_open(self, component: str) -> bool:
        """Check if component is in fail-open state"""
        return self.components.get(component, {}).get("fail_open", False)
        
    def reset_component(self, component: str):
        """Reset component fail-open state"""
        if component in self.components:
            self.components[component]["fail_open"] = False
            self.components[component]["error_count"] = 0
            self.components[component]["total_requests"] = 0
            self.components[component]["last_error"] = None
            
    def get_status(self) -> Dict[str, Any]:
        """Get fail-open status for all components"""
        status = {}
        for name, comp in self.components.items():
            error_rate = 0
            if comp["total_requests"] > 0:
                error_rate = comp["error_count"] / comp["total_requests"]
                
            status[name] = {
                "fail_open": comp["fail_open"],
                "error_rate": error_rate,
                "error_count": comp["error_count"],
                "total_requests": comp["total_requests"],
                "last_error": comp["last_error"]
            }
        return status


# Global instances
performance_monitor = PerformanceMonitor()
fail_open_manager = FailOpenManager(performance_monitor)

# Set up default thresholds
performance_monitor.set_threshold(PerformanceThreshold(
    name="response_time",
    warning_threshold=2.0,
    critical_threshold=5.0,
    unit="seconds",
    description="Response time threshold"
))

performance_monitor.set_threshold(PerformanceThreshold(
    name="memory_usage",
    warning_threshold=0.8,
    critical_threshold=0.9,
    unit="ratio",
    description="Memory usage threshold"
))

performance_monitor.set_threshold(PerformanceThreshold(
    name="cpu_usage",
    warning_threshold=0.8,
    critical_threshold=0.9,
    unit="ratio",
    description="CPU usage threshold"
))

# Register default components
fail_open_manager.register_component("database", critical=True)
fail_open_manager.register_component("event_manager", critical=True)
fail_open_manager.register_component("plugin_manager", critical=True)
fail_open_manager.register_component("web_interface", critical=True)
fail_open_manager.register_component("sensor_listeners", critical=False)


def performance_probe(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for performance probing"""
    return PerformanceProbe(performance_monitor, name, tags)


@contextmanager
def performance_timer(name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager for performance timing"""
    probe = PerformanceProbe(performance_monitor, name, tags)
    with probe:
        yield


def record_success(component: str):
    """Record successful operation"""
    fail_open_manager.record_success(component)


def record_error(component: str, error: Exception):
    """Record failed operation"""
    fail_open_manager.record_error(component, error)


def is_fail_open(component: str) -> bool:
    """Check if component is in fail-open state"""
    return fail_open_manager.is_fail_open(component)
