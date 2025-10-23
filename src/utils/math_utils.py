"""
Mathematical utilities for Terrain Tunneling Calculator.

This module contains mathematical calculations, geometric operations,
and utility classes for spatial operations.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, List
import numpy as np
import math


@dataclass
class BoundingBox:
    """Geographic bounds for spatial operations."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float = -float('inf')
    max_z: float = float('inf')

    def __post_init__(self):
        """Validate bounding box after initialization."""
        if self.min_x > self.max_x:
            raise ValueError("min_x must be less than or equal to max_x")
        if self.min_y > self.max_y:
            raise ValueError("min_y must be less than or equal to max_y")
        if self.min_z > self.max_z:
            raise ValueError("min_z must be less than or equal to max_z")

    def contains_point(self, point: np.ndarray) -> bool:
        """Check if a point is within the bounding box."""
        if len(point) < 2:
            return False

        x, y = point[0], point[1]
        z = point[2] if len(point) > 2 else 0.0

        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y and
                self.min_z <= z <= self.max_z)

    def contains_point_2d(self, x: float, y: float) -> bool:
        """Check if a 2D point is within the bounding box."""
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y)

    def contains_point_3d(self, x: float, y: float, z: float) -> bool:
        """Check if a 3D point is within the bounding box."""
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y and
                self.min_z <= z <= self.max_z)

    def get_area(self) -> float:
        """Calculate the 2D area of the bounding box."""
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)

    def get_perimeter(self) -> float:
        """Calculate the perimeter of the 2D bounding box."""
        return 2 * ((self.max_x - self.min_x) + (self.max_y - self.min_y))

    def get_width(self) -> float:
        """Get the width of the bounding box."""
        return self.max_x - self.min_x

    def get_height(self) -> float:
        """Get the height of the bounding box."""
        return self.max_y - self.min_y

    def get_depth(self) -> float:
        """Get the depth (z-range) of the bounding box."""
        return self.max_z - self.min_z

    def get_center(self) -> Tuple[float, float]:
        """Get the center point of the 2D bounding box."""
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

    def get_center_3d(self) -> Tuple[float, float, float]:
        """Get the center point of the 3D bounding box."""
        return ((self.min_x + self.max_x) / 2,
                (self.min_y + self.max_y) / 2,
                (self.min_z + self.max_z) / 2)

    def expand(self, margin: float) -> 'BoundingBox':
        """Expand the bounding box by a margin."""
        return BoundingBox(
            min_x=self.min_x - margin,
            max_x=self.max_x + margin,
            min_y=self.min_y - margin,
            max_y=self.max_y + margin,
            min_z=self.min_z - margin,
            max_z=self.max_z + margin
        )

    def intersect(self, other: 'BoundingBox') -> 'BoundingBox':
        """Calculate the intersection of two bounding boxes."""
        return BoundingBox(
            min_x=max(self.min_x, other.min_x),
            max_x=min(self.max_x, other.max_x),
            min_y=max(self.min_y, other.min_y),
            max_y=min(self.max_y, other.max_y),
            min_z=max(self.min_z, other.min_z),
            max_z=min(self.max_z, other.max_z)
        )

    def union(self, other: 'BoundingBox') -> 'BoundingBox':
        """Calculate the union of two bounding boxes."""
        return BoundingBox(
            min_x=min(self.min_x, other.min_x),
            max_x=max(self.max_x, other.max_x),
            min_y=min(self.min_y, other.min_y),
            max_y=max(self.max_y, other.max_y),
            min_z=min(self.min_z, other.min_z),
            max_z=max(self.max_z, other.max_z)
        )

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box overlaps with another."""
        return not (self.max_x < other.min_x or self.min_x > other.max_x or
                   self.max_y < other.min_y or self.min_y > other.max_y or
                   self.max_z < other.min_z or self.min_z > other.max_z)

    def distance_to_point(self, x: float, y: float, z: float = 0.0) -> float:
        """Calculate the minimum distance from the bounding box to a point."""
        # Clamp point to bounding box
        clamped_x = max(self.min_x, min(x, self.max_x))
        clamped_y = max(self.min_y, min(y, self.max_y))
        clamped_z = max(self.min_z, min(z, self.max_z))

        # Calculate distance
        dx = x - clamped_x
        dy = y - clamped_y
        dz = z - clamped_z

        return math.sqrt(dx*dx + dy*dy + dz*dz)


class MathUtils:
    """Utility class for mathematical operations."""

    @staticmethod
    def distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two 2D points."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx*dx + dy*dy)

    @staticmethod
    def distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
        """Calculate Euclidean distance between two 3D points."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    @staticmethod
    def angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate the angle between two vectors in radians."""
        dot_product = np.dot(v1, v2)
        magnitude = np.linalg.norm(v1) * np.linalg.norm(v2)

        if magnitude == 0:
            return 0.0

        # Clamp to avoid numerical errors
        cos_angle = max(-1.0, min(1.0, dot_product / magnitude))
        return math.acos(cos_angle)

    @staticmethod
    def normalize_angle(angle: float) -> float:
        """Normalize angle to range [0, 2π]."""
        while angle < 0:
            angle += 2 * math.pi
        while angle >= 2 * math.pi:
            angle -= 2 * math.pi
        return angle

    @staticmethod
    def linear_interpolate(p1: np.ndarray, p2: np.ndarray, t: float) -> np.ndarray:
        """Linear interpolation between two points."""
        return p1 + t * (p2 - p1)

    @staticmethod
    def point_to_line_distance(point: np.ndarray, line_start: np.ndarray, line_end: np.ndarray) -> float:
        """Calculate the distance from a point to a line segment."""
        # Vector from line_start to line_end
        line_vec = line_end - line_start
        # Vector from line_start to point
        point_vec = point - line_start

        line_length = np.linalg.norm(line_vec)
        if line_length == 0:
            return np.linalg.norm(point_vec)

        # Project point onto line
        t = max(0, min(1, np.dot(point_vec, line_vec) / (line_length * line_length)))
        projection = line_start + t * line_vec

        return np.linalg.norm(point - projection)

    @staticmethod
    def area_of_triangle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """Calculate the area of a triangle using the cross product."""
        # Vectors from p1 to p2 and p1 to p3
        v1 = p2 - p1
        v2 = p3 - p1

        # Cross product magnitude divided by 2
        if len(p1) == 2:
            # 2D case
            return abs(v1[0] * v2[1] - v1[1] * v2[0]) / 2
        else:
            # 3D case
            cross_product = np.cross(v1, v2)
            return np.linalg.norm(cross_product) / 2

    @staticmethod
    def is_point_in_triangle(point: np.ndarray, v1: np.ndarray, v2: np.ndarray, v3: np.ndarray) -> bool:
        """Check if a point is inside a triangle using barycentric coordinates."""
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign(point, v1, v2)
        d2 = sign(point, v2, v3)
        d3 = sign(point, v3, v1)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

        return not (has_neg and has_pos)

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp a value to be within a specified range."""
        return max(min_val, min(value, max_val))

    @staticmethod
    def deg_to_rad(degrees: float) -> float:
        """Convert degrees to radians."""
        return degrees * math.pi / 180.0

    @staticmethod
    def rad_to_deg(radians: float) -> float:
        """Convert radians to degrees."""
        return radians * 180.0 / math.pi