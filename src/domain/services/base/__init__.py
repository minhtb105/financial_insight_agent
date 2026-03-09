"""
Base Services

This module contains base services and utilities for the domain layer.
"""

from .time_processor import TimeProcessor, process_service_time_params

__all__ = [
    'TimeProcessor',
    'process_service_time_params',
]