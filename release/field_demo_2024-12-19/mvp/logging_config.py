"""
Structured Logging Configuration for TheBox
==========================================

Centralized logging configuration with structured logging, log levels,
and output formats suitable for production deployment.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> None:
    """
    Configure structured logging for TheBox.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "console")
        log_file: Optional log file path
        enable_console: Whether to enable console output
    """
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        stream=sys.stdout if enable_console else None
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add output processor based on format
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure file logging if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Use JSON format for file logs
        file_processors = processors[:-1] + [structlog.processors.JSONRenderer()]
        file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=file_processors[-1]
        ))
        
        # Add file handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class LoggingMixin:
    """Mixin class to add structured logging to any class"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls with parameters and results"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug("Function called", 
                    function=func.__name__,
                    args=args,
                    kwargs=kwargs)
        
        try:
            result = func(*args, **kwargs)
            logger.debug("Function completed", 
                        function=func.__name__,
                        result=result)
            return result
        except Exception as e:
            logger.error("Function failed", 
                        function=func.__name__,
                        error=str(e),
                        exc_info=True)
            raise
    
    return wrapper


def log_plugin_event(plugin_name: str, event_type: str, **kwargs):
    """Log a plugin event with structured data"""
    logger = get_logger("plugins")
    logger.info("Plugin event",
               plugin=plugin_name,
               event_type=event_type,
               **kwargs)


def log_sensor_data(sensor_type: str, data: Dict[str, Any]):
    """Log sensor data with structured format"""
    logger = get_logger("sensors")
    logger.info("Sensor data received",
               sensor_type=sensor_type,
               data_size=len(str(data)),
               **data)


def log_detection(detection: Dict[str, Any]):
    """Log a detection event"""
    logger = get_logger("detections")
    logger.info("Detection processed",
               bearing=detection.get("bearing_deg"),
               confidence=detection.get("confidence"),
               source=detection.get("source"),
               track_id=detection.get("track_id"))


def log_performance(operation: str, duration: float, **kwargs):
    """Log performance metrics"""
    logger = get_logger("performance")
    logger.info("Performance metric",
               operation=operation,
               duration_ms=duration * 1000,
               **kwargs)


def log_error(error: Exception, context: str = "", **kwargs):
    """Log an error with context"""
    logger = get_logger("errors")
    logger.error("Error occurred",
                error=str(error),
                context=context,
                exc_info=True,
                **kwargs)


def log_system_event(event: str, **kwargs):
    """Log a system event"""
    logger = get_logger("system")
    logger.info("System event",
               event=event,
               **kwargs)


# Pre-configured loggers for common use cases
sensor_logger = get_logger("sensors")
detection_logger = get_logger("detections")
plugin_logger = get_logger("plugins")
performance_logger = get_logger("performance")
error_logger = get_logger("errors")
system_logger = get_logger("system")
