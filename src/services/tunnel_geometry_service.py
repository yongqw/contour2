"""
Tunnel geometry service for Terrain Tunneling Calculator.

This service provides high-level operations for tunnel geometry creation,
validation, and analysis. It bridges the gap between the GUI controls
and the tunnel geometry models.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import math
from dataclasses import dataclass

from models.tunnel_geometry import (
    TunnelPath, TunnelGeometry, TunnelWaypoint, CrossSectionType
)
from models.contour_data import ContourData
from models.visualization_state import VisualizationState
from utils.validation import (
    ValidationFramework, ValidationResult, ValidationSeverity,
    CommonValidationRules, ValidationConstants, ValidationRule
)


@dataclass
class TunnelCreationRequest:
    """Request object for tunnel creation."""
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    radius: float
    cross_section_type: CrossSectionType
    intermediate_points: List[Tuple[float, float]] = None

    def __post_init__(self):
        if self.intermediate_points is None:
            self.intermediate_points = []


@dataclass
class TunnelCreationResult:
    """Result object for tunnel creation operations."""
    success: bool
    tunnel_geometry: Optional[TunnelGeometry] = None
    validation_result: Optional[ValidationResult] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class TunnelGeometryService:
    """Service for tunnel geometry operations and validation."""

    def __init__(self):
        """Initialize the tunnel geometry service."""
        self.validation_framework = ValidationFramework()
        self._setup_validation_rules()

    def _setup_validation_rules(self) -> None:
        """Set up validation rules for tunnel geometry."""
        # Radius validation
        radius_rule = CommonValidationRules.tunnel_radius_rule()
        self.validation_framework.add_rule("tunnel_radius", radius_rule)

        # Coordinate validation
        coord_rule = CommonValidationRules.coordinate_rule()
        self.validation_framework.add_rule("coordinates", coord_rule)

        # Path length validation
        path_length_rule = ValidationRule(
            name="path_length",
            condition=lambda x: isinstance(x, (int, float)) and
                              ValidationConstants.MIN_TUNNEL_LENGTH <= x <= ValidationConstants.MAX_TUNNEL_LENGTH,
            error_message=f"Tunnel length must be between {ValidationConstants.MIN_TUNNEL_LENGTH} and {ValidationConstants.MAX_TUNNEL_LENGTH} meters",
            severity=ValidationSeverity.ERROR
        )
        self.validation_framework.add_rule("tunnel_length", path_length_rule)

    def create_tunnel_from_request(
        self,
        request: TunnelCreationRequest,
        contour_data: ContourData
    ) -> TunnelCreationResult:
        """
        Create tunnel geometry from a creation request and contour data.

        Args:
            request: Tunnel creation parameters
            contour_data: Terrain contour data for elevation interpolation

        Returns:
            TunnelCreationResult with tunnel geometry or validation errors
        """
        result = TunnelCreationResult(success=False)

        # Validate the request first
        validation_result = self._validate_creation_request(request)
        result.validation_result = validation_result

        if validation_result.has_errors():
            result.errors = [issue.message for issue in validation_result.get_errors()]
            return result

        try:
            # Create tunnel path
            tunnel_path = self._create_tunnel_path(request, contour_data)

            # Create tunnel geometry
            tunnel_geometry = TunnelGeometry(path=tunnel_path)

            # Validate the created geometry
            geometry_validation = self._validate_tunnel_geometry(tunnel_geometry)

            if geometry_validation.has_errors():
                result.errors = [issue.message for issue in geometry_validation.get_errors()]
                return result

            result.success = True
            result.tunnel_geometry = tunnel_geometry
            result.warnings = [issue.message for issue in geometry_validation.get_warnings()]

        except Exception as e:
            result.errors.append(f"Failed to create tunnel geometry: {str(e)}")

        return result

    def _validate_creation_request(self, request: TunnelCreationRequest) -> ValidationResult:
        """Validate a tunnel creation request."""
        result = ValidationResult(is_valid=True)

        # Validate radius
        radius_validation = self.validation_framework.validate_field(
            request.radius, "radius", "tunnel_radius"
        )
        result.issues.extend(radius_validation.issues)

        # Validate start point
        start_validation = self.validation_framework.validate_field(
            request.start_point, "start_point", "coordinates"
        )
        result.issues.extend(start_validation.issues)

        # Validate end point
        end_validation = self.validation_framework.validate_field(
            request.end_point, "end_point", "coordinates"
        )
        result.issues.extend(end_validation.issues)

        # Validate intermediate points
        for i, point in enumerate(request.intermediate_points):
            point_validation = self.validation_framework.validate_field(
                point, f"intermediate_point_{i}", "coordinates"
            )
            result.issues.extend(point_validation.issues)

        # Calculate and validate path length
        path_length = self._calculate_2d_path_length(request)
        length_validation = self.validation_framework.validate_field(
            path_length, "path_length", "tunnel_length"
        )
        result.issues.extend(length_validation.issues)

        # Check for self-intersection
        if self._path_self_intersects(request):
            result.add_issue(
                "Tunnel path self-intersects",
                ValidationSeverity.ERROR,
                suggestion="Adjust intermediate points to avoid intersection"
            )

        return result

    def _create_tunnel_path(
        self,
        request: TunnelCreationRequest,
        contour_data: ContourData
    ) -> TunnelPath:
        """Create a tunnel path from request and contour data."""
        path = TunnelPath()
        path.cross_section_type = request.cross_section_type

        # Build list of all points in order
        all_points = [request.start_point] + request.intermediate_points + [request.end_point]

        for point in all_points:
            # Get elevation from contour data
            elevation = self._get_elevation_at_point(point, contour_data)

            # Add waypoint with specified radius
            path.add_waypoint(point[0], point[1], elevation, request.radius)

        return path

    def _get_elevation_at_point(self, point: Tuple[float, float], contour_data: ContourData) -> float:
        """Get interpolated elevation at a specific point."""
        try:
            elevation = contour_data.get_elevation_at(point[0], point[1])
            return elevation
        except (ValueError, IndexError):
            # If elevation lookup fails, estimate from nearby contours
            return self._estimate_elevation_from_contours(point, contour_data)

    def _estimate_elevation_from_contours(
        self,
        point: Tuple[float, float],
        contour_data: ContourData
    ) -> float:
        """Estimate elevation by finding nearest contour lines."""
        if not contour_data.contours:
            return 0.0  # Default elevation

        min_distance = float('inf')
        closest_elevation = 0.0

        for contour_line in contour_data.contours:
            for contour_point in contour_line.points:
                distance = math.sqrt(
                    (contour_point[0] - point[0])**2 +
                    (contour_point[1] - point[1])**2
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_elevation = contour_line.elevation

        return closest_elevation

    def _calculate_2d_path_length(self, request: TunnelCreationRequest) -> float:
        """Calculate 2D path length including intermediate points."""
        all_points = [request.start_point] + request.intermediate_points + [request.end_point]

        total_length = 0.0
        for i in range(len(all_points) - 1):
            p1, p2 = all_points[i], all_points[i + 1]
            segment_length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            total_length += segment_length

        return total_length

    def _path_self_intersects(self, request: TunnelCreationRequest) -> bool:
        """Check if the tunnel path self-intersects."""
        all_points = [request.start_point] + request.intermediate_points + [request.end_point]

        if len(all_points) < 4:
            return False

        # Check for intersection between non-adjacent segments
        for i in range(len(all_points) - 2):
            for j in range(i + 2, len(all_points) - 1):
                if i == 0 and j == len(all_points) - 2:
                    continue  # Skip checking first segment against last (closed path)

                if self._segments_intersect(
                    all_points[i], all_points[i + 1],
                    all_points[j], all_points[j + 1]
                ):
                    return True

        return False

    def _segments_intersect(
        self,
        p1: Tuple[float, float], p2: Tuple[float, float],
        p3: Tuple[float, float], p4: Tuple[float, float]
    ) -> bool:
        """Check if two line segments intersect."""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    def _validate_tunnel_geometry(self, tunnel_geometry: TunnelGeometry) -> ValidationResult:
        """Validate created tunnel geometry."""
        result = ValidationResult(is_valid=True)

        # Validate path
        if not tunnel_geometry.path.validate():
            result.add_issue(
                "Tunnel path validation failed",
                ValidationSeverity.ERROR
            )

        # Check for reasonable gradient
        max_gradient = self._calculate_max_gradient(tunnel_geometry.path)
        if max_gradient > 15.0:  # 15% maximum gradient
            result.add_issue(
                f"Tunnel gradient ({max_gradient:.1f}%) exceeds recommended maximum (15%)",
                ValidationSeverity.WARNING,
                suggestion="Consider adjusting tunnel path to reduce gradient"
            )

        # Check clearance
        min_clearance = self._calculate_min_clearance(tunnel_geometry)
        if min_clearance < 2.0:  # 2 meters minimum clearance
            result.add_issue(
                f"Minimum clearance ({min_clearance:.1f}m) below recommended minimum (2m)",
                ValidationSeverity.WARNING,
                suggestion="Increase tunnel radius or adjust path"
            )

        return result

    def _calculate_max_gradient(self, tunnel_path: TunnelPath) -> float:
        """Calculate maximum gradient along tunnel path."""
        if len(tunnel_path.waypoints) < 2:
            return 0.0

        max_gradient = 0.0
        for i in range(len(tunnel_path.waypoints) - 1):
            wp1, wp2 = tunnel_path.waypoints[i], tunnel_path.waypoints[i + 1]

            # Calculate horizontal distance
            horizontal_dist = math.sqrt((wp2.x - wp1.x)**2 + (wp2.y - wp1.y)**2)
            if horizontal_dist == 0:
                continue

            # Calculate gradient
            elevation_change = wp2.elevation - wp1.elevation
            gradient = abs(elevation_change / horizontal_dist) * 100
            max_gradient = max(max_gradient, gradient)

        return max_gradient

    def _calculate_min_clearance(self, tunnel_geometry: TunnelGeometry) -> float:
        """Calculate minimum clearance (radius) along tunnel."""
        if not tunnel_geometry.path.waypoints:
            return 0.0

        min_radius = min(wp.radius for wp in tunnel_geometry.path.waypoints)
        return min_radius

    def optimize_tunnel_path(
        self,
        tunnel_path: TunnelPath,
        contour_data: ContourData,
        optimization_target: str = "length"  # "length", "gradient", "volume"
    ) -> TunnelPath:
        """
        Optimize tunnel path based on specified target.

        Args:
            tunnel_path: Original tunnel path to optimize
            contour_data: Terrain data for optimization
            optimization_target: What to optimize for

        Returns:
            Optimized tunnel path
        """
        # This is a placeholder for path optimization algorithms
        # In a full implementation, this would use algorithms like:
        # - Dijkstra's algorithm for shortest path
        # - Gradient optimization for minimal slope
        # - Cost functions for minimal excavation volume

        optimized_path = TunnelPath()
        optimized_path.cross_section_type = tunnel_path.cross_section_type

        # For now, just copy the original path
        for wp in tunnel_path.waypoints:
            optimized_path.add_waypoint(wp.x, wp.y, wp.elevation, wp.radius)

        return optimized_path

    def calculate_tunnel_statistics(self, tunnel_geometry: TunnelGeometry) -> Dict[str, Any]:
        """Calculate comprehensive tunnel statistics."""
        if not tunnel_geometry.path.waypoints:
            return {}

        # Calculate volume and surface area dynamically if not already calculated
        volume = tunnel_geometry.volume
        surface_area = tunnel_geometry.surface_area

        # If volume is 0, calculate it dynamically
        if volume <= 0:
            volume = self._calculate_tunnel_volume(tunnel_geometry)

        # If surface area is 0, calculate it dynamically
        if surface_area <= 0:
            surface_area = self._calculate_tunnel_surface_area(tunnel_geometry)

        stats = {
            "total_length": tunnel_geometry.path.get_length(),
            "volume": volume,
            "surface_area": surface_area,
            "cross_section_type": tunnel_geometry.cross_section_type.value,
            "waypoint_count": len(tunnel_geometry.path.waypoints),
            "average_radius": tunnel_geometry.radius,
            "max_gradient": self._calculate_max_gradient(tunnel_geometry.path),
            "min_clearance": self._calculate_min_clearance(tunnel_geometry)
        }

        # Calculate elevation statistics
        elevations = [wp.elevation for wp in tunnel_geometry.path.waypoints]
        stats.update({
            "min_elevation": min(elevations),
            "max_elevation": max(elevations),
            "elevation_change": max(elevations) - min(elevations)
        })

        return stats

    def _calculate_tunnel_volume(self, tunnel_geometry: TunnelGeometry) -> float:
        """Calculate tunnel volume using cylinder approximation."""
        if not tunnel_geometry.path.waypoints:
            return 0.0

        total_volume = 0.0
        waypoints = tunnel_geometry.path.waypoints

        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]

            # Calculate segment length
            dx = wp2.x - wp1.x
            dy = wp2.y - wp1.y
            dz = wp2.elevation - wp1.elevation
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)

            # Use average radius for this segment
            avg_radius = (wp1.radius + wp2.radius) / 2.0
            # Volume = π * r² * length
            segment_volume = math.pi * avg_radius**2 * segment_length
            total_volume += segment_volume

        return total_volume

    def _calculate_tunnel_surface_area(self, tunnel_geometry: TunnelGeometry) -> float:
        """Calculate tunnel surface area using cylinder approximation."""
        if not tunnel_geometry.path.waypoints:
            return 0.0

        total_area = 0.0
        waypoints = tunnel_geometry.path.waypoints

        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]

            # Calculate segment length
            dx = wp2.x - wp1.x
            dy = wp2.y - wp1.y
            dz = wp2.elevation - wp1.elevation
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)

            # Use average radius for this segment
            avg_radius = (wp1.radius + wp2.radius) / 2.0
            # Surface area = 2 * π * r * length
            segment_area = 2 * math.pi * avg_radius * segment_length
            total_area += segment_area

        return total_area

    def export_tunnel_geometry(
        self,
        tunnel_geometry: TunnelGeometry,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export tunnel geometry in specified format."""
        if format.lower() == "json":
            return tunnel_geometry.to_dict()
        else:
            raise ValueError(f"Unsupported export format: {format}")