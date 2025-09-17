"""
Reliability Utilities for TheBox
================================

Utilities for timeouts, exponential backoff, graceful shutdown,
and other reliability patterns.
"""

import asyncio
import signal
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Union

import structlog
from tenacity import (
    RetryError,
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed,
)

from .logging_config import get_logger

logger = get_logger(__name__)


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


@contextmanager
def timeout(seconds: float):
    """Context manager for timeouts"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(seconds))
    
    try:
        yield
    finally:
        # Restore the old handler
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)


class GracefulShutdown:
    """Manages graceful shutdown of the application"""
    
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.cleanup_functions: List[Callable] = []
        self.shutdown_timeout = 30.0  # seconds
        
    def register_cleanup(self, func: Callable):
        """Register a cleanup function to be called on shutdown"""
        self.cleanup_functions.append(func)
        
    def signal_shutdown(self):
        """Signal that shutdown should begin"""
        logger.info("Shutdown signal received")
        self.shutdown_event.set()
        
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown signal"""
        timeout = timeout or self.shutdown_timeout
        return self.shutdown_event.wait(timeout)
        
    def is_shutdown(self) -> bool:
        """Check if shutdown has been signaled"""
        return self.shutdown_event.is_set()
        
    def cleanup(self):
        """Run all registered cleanup functions"""
        logger.info("Running cleanup functions", count=len(self.cleanup_functions))
        
        for func in self.cleanup_functions:
            try:
                func()
            except Exception as e:
                logger.error("Cleanup function failed", function=func.__name__, error=str(e))
                
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info("Received signal", signal=signum)
            self.signal_shutdown()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # On Windows, also handle SIGBREAK
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)


class ExponentialBackoff:
    """Exponential backoff with jitter"""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt = 0
        
    def next_delay(self) -> float:
        """Get the next delay value"""
        delay = min(self.base_delay * (self.multiplier ** self.attempt), self.max_delay)
        
        if self.jitter:
            # Add random jitter to prevent thundering herd
            import random
            delay *= (0.5 + random.random() * 0.5)
            
        self.attempt += 1
        return delay
        
    def reset(self):
        """Reset the backoff counter"""
        self.attempt = 0


class RetryableOperation:
    """Wrapper for operations that should be retried"""
    
    def __init__(
        self,
        operation: Callable,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        self.operation = operation
        self.max_attempts = max_attempts
        self.backoff = ExponentialBackoff(base_delay, max_delay, backoff_multiplier)
        self.exceptions = exceptions
        
    def execute(self, *args, **kwargs) -> Any:
        """Execute the operation with retries"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return self.operation(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = self.backoff.next_delay()
                    logger.warning(
                        "Operation failed, retrying",
                        operation=self.operation.__name__,
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Operation failed after all retries",
                        operation=self.operation.__name__,
                        attempts=self.max_attempts,
                        error=str(e)
                    )
                    
        raise last_exception


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for retrying operations with exponential backoff"""
    def decorator(func):
        retry_op = RetryableOperation(
            func, max_attempts, base_delay, max_delay, backoff_multiplier, exceptions
        )
        return retry_op.execute
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function through circuit breaker"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
                
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
            
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker transitioning to CLOSED")
            
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )


class HealthChecker:
    """Health check utility"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func
        
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                duration = time.time() - start_time
                
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "duration": duration,
                    "timestamp": time.time()
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time()
                }
                
        return results
        
    def is_healthy(self) -> bool:
        """Check if all health checks pass"""
        results = self.run_checks()
        return all(result["status"] == "healthy" for result in results.values())


class RateLimiter:
    """Rate limiter using token bucket algorithm"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()
        
    def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket"""
        with self.lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
                
    def wait_for_tokens(self, tokens: int = 1, timeout: float = 10.0) -> bool:
        """Wait for tokens to become available"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.acquire(tokens):
                return True
            time.sleep(0.01)  # Small delay to prevent busy waiting
            
        return False


class BoundedQueue:
    """Thread-safe bounded queue with overflow handling"""
    
    def __init__(self, maxsize: int, overflow_strategy: str = "drop_oldest"):
        self.maxsize = maxsize
        self.overflow_strategy = overflow_strategy
        self.queue = []
        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)
        
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Put item in queue"""
        with self.not_full:
            if len(self.queue) >= self.maxsize:
                if not block:
                    return False
                    
                if self.overflow_strategy == "drop_oldest":
                    self.queue.pop(0)
                elif self.overflow_strategy == "drop_newest":
                    return False
                elif self.overflow_strategy == "block":
                    if not self.not_full.wait(timeout):
                        return False
                        
            self.queue.append(item)
            self.not_empty.notify()
            return True
            
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """Get item from queue"""
        with self.not_empty:
            if not self.queue:
                if not block:
                    raise EmptyQueueError("Queue is empty")
                if not self.not_empty.wait(timeout):
                    raise EmptyQueueError("Timeout waiting for item")
                    
            item = self.queue.pop(0)
            self.not_full.notify()
            return item
            
    def size(self) -> int:
        """Get current queue size"""
        with self.lock:
            return len(self.queue)
            
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        with self.lock:
            return len(self.queue) == 0
            
    def is_full(self) -> bool:
        """Check if queue is full"""
        with self.lock:
            return len(self.queue) >= self.maxsize


class EmptyQueueError(Exception):
    """Exception raised when trying to get from empty queue"""
    pass


# Global instances
graceful_shutdown = GracefulShutdown()
health_checker = HealthChecker()

# Setup signal handlers
graceful_shutdown.setup_signal_handlers()
