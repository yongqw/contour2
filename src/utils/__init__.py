"""
Utility functions and helper classes for Terrain Tunneling Calculator.

This module contains shared utilities for validation, file I/O, mathematical operations,
configuration management, exception handling, and demo data generation.
"""

from .validation import ValidationFramework, ValidationResult, ValidationConstants
from .file_utils import FileUtils
from .math_utils import BoundingBox, MathUtils
from .config import ConfigManager
from .exceptions import ContourError, ValidationError, TriangulationError

__all__ = [
    "ValidationFramework",
    "ValidationResult",
    "ValidationConstants",
    "FileUtils",
    "BoundingBox",
    "MathUtils",
    "ConfigManager",
    "ContourError",
    "ValidationError",
    "TriangulationError"
]