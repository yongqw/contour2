"""
Custom exceptions for Terrain Tunneling Calculator.

This module defines application-specific exceptions for better error handling
and user feedback.
"""

class ContourError(Exception):
    """Base exception for all contour-related errors."""
    pass


class InvalidContourFileError(ContourError):
    """Raised when contour file format is invalid or corrupted."""
    pass


class ValidationError(ContourError):
    """Raised when contour data fails validation rules."""
    pass


class TriangulationError(ContourError):
    """Raised when triangulation process fails."""
    pass


class VolumeCalculationError(ContourError):
    """Raised when volume calculation fails."""
    pass


class VisualizationError(ContourError):
    """Raised when 3D visualization fails."""
    pass


class TunnelGeometryError(ContourError):
    """Raised when tunnel geometry is invalid."""
    pass


class PerformanceError(ContourError):
    """Raised when performance limits are exceeded."""
    pass


class FileOperationError(ContourError):
    """Raised when file operations fail."""
    pass


class ConfigurationError(ContourError):
    """Raised when configuration is invalid."""
    pass


class CoordinateSystemError(ContourError):
    """Raised when coordinate system operations fail."""
    pass


class ExportError(ContourError):
    """Raised when data export fails."""
    pass


class AnimationError(ContourError):
    """Raised when animation generation fails."""
    pass