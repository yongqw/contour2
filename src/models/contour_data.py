"""
Contour data models for Terrain Tunneling Calculator.

This module defines the data structures for representing terrain elevation data,
contour lines, and related metadata.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import numpy as np


class CoordinateSystem(Enum):
    """Supported coordinate systems for contour data."""
    LOCAL = "local"
    UTM = "utm"
    LAT_LON = "lat_lon"
    STATE_PLANE = "state_plane"


@dataclass
class ContourMetadata:
    """Metadata for contour files."""
    name: str
    units: str = "meters"
    coordinate_system: CoordinateSystem = CoordinateSystem.LOCAL
    datum: str = "unknown"
    created_date: Optional[str] = None
    source: str = "generated"
    description: Optional[str] = None

    def validate(self) -> bool:
        """Validate metadata fields."""
        if not self.name or len(self.name.strip()) == 0:
            return False
        if self.units not in ["meters", "feet"]:
            return False
        return True


@dataclass
class ContourLine:
    """Single elevation contour with coordinate points."""
    elevation: float
    points: np.ndarray  # Shape: (n, 2) for [x, y] coordinates
    is_closed: bool = True

    def __post_init__(self):
        """Validate contour line after initialization."""
        if len(self.points.shape) != 2 or self.points.shape[1] != 2:
            raise ValueError("Points must be a 2D array with shape (n, 2)")
        if self.points.shape[0] < 3:
            raise ValueError("Contour must have at least 3 points")

    def get_length(self) -> float:
        """Calculate the total length of the contour line."""
        if len(self.points) < 2:
            return 0.0

        # Calculate distances between consecutive points
        distances = np.sqrt(np.sum(np.diff(self.points, axis=0)**2, axis=1))
        return float(np.sum(distances))

    def get_area(self) -> float:
        """Calculate the area enclosed by the contour using the shoelace formula."""
        if len(self.points) < 3:
            return 0.0

        x, y = self.points[:, 0], self.points[:, 1]
        area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        return area

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside the contour using ray casting algorithm."""
        if len(self.points) < 3:
            return False

        # Simple ray casting algorithm
        point = np.array([x, y])
        n = len(self.points)
        inside = False

        p1x, p1y = self.points[0]
        for i in range(1, n + 1):
            p2x, p2y = self.points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside


@dataclass
class ContourData:
    """Complete contour data structure."""
    metadata: ContourMetadata
    contours: List[ContourLine]
    bounds: 'BoundingBox'
    coordinate_system: CoordinateSystem = CoordinateSystem.LOCAL

    def validate(self) -> bool:
        """Validate contour data against business rules."""
        if not self.metadata.validate():
            return False

        if len(self.contours) == 0:
            return False

        # Validate elevation ranges
        for contour in self.contours:
            if contour.elevation < -1000 or contour.elevation > 10000:
                return False
            if not contour.is_closed:
                return False

        return True

    def get_elevation_at(self, x: float, y: float) -> float:
        """Get interpolated elevation at a specific point."""
        # Find the contour that contains the point
        containing_contours = [c for c in self.contours if c.contains_point(x, y)]

        if not containing_contours:
            # If point is outside all contours, return minimum elevation
            return min(c.elevation for c in self.contours)

        # If point is inside multiple contours, use the highest elevation
        return max(c.elevation for c in containing_contours)

    def get_bounds(self) -> 'BoundingBox':
        """Get the bounding box of all contour data."""
        return self.bounds

    def get_elevation_range(self) -> tuple[float, float]:
        """Get the minimum and maximum elevation."""
        if not self.contours:
            return 0.0, 0.0

        elevations = [c.elevation for c in self.contours]
        return min(elevations), max(elevations)

    def get_contour_at_elevation(self, elevation: float, tolerance: float = 0.1) -> Optional[ContourLine]:
        """Get the contour closest to a specific elevation."""
        closest_contour = None
        min_diff = float('inf')

        for contour in self.contours:
            diff = abs(contour.elevation - elevation)
            if diff < min_diff and diff <= tolerance:
                min_diff = diff
                closest_contour = contour

        return closest_contour


# Import BoundingBox here to avoid circular imports
from utils.math_utils import BoundingBox