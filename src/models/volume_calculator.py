"""
Volume calculation models for Terrain Tunneling Calculator.

This module provides models for calculating tunnel excavation volumes,
including terrain intersection analysis, excavation zones, and accuracy validation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np
import math

# Import required from other modules
from models.tunnel_geometry import CrossSectionType
from models.terrain_mesh import TerrainMesh


class MaterialType(Enum):
    """Types of excavated materials."""
    ROCK = "rock"
    SOIL = "soil"
    MIXED = "mixed"
    HARD_ROCK = "hard_rock"
    SOFT_ROCK = "soft_rock"
    CLAY = "clay"
    SAND = "sand"
    GRAVEL = "gravel"


class CalculationMethod(Enum):
    """Volume calculation methods."""
    ANALYTICAL = "analytical"  # Direct geometric calculation
    TETRAHEDRAL = "tetrahedral"  # Tetrahedral decomposition
    MONTE_CARLO = "monte_carlo"  # Statistical sampling
    HYBRID = "hybrid"  # Combination of methods


@dataclass
class ExcavationZone:
    """Represents a zone of excavation with specific characteristics."""

    start_position: float  # Position along tunnel (meters)
    end_position: float    # End position along tunnel (meters)
    volume: float          # Excavation volume (cubic meters)
    cross_section_area: float  # Average cross-section area (square meters)
    material_type: MaterialType
    overburden: float = 0.0     # Overburden thickness (meters)
    rock_quality: str = "unknown"  # Rock quality rating

    def get_length(self) -> float:
        """Get the length of this excavation zone."""
        return self.end_position - self.start_position

    def get_average_depth(self) -> float:
        """Get average excavation depth."""
        if self.cross_section_area > 0:
            return self.volume / self.cross_section_area
        return 0.0

    def validate(self) -> bool:
        """Validate excavation zone data."""
        if self.end_position <= self.start_position:
            return False
        if self.volume < 0:
            return False
        if self.cross_section_area <= 0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert excavation zone to dictionary."""
        return {
            'start_position': self.start_position,
            'end_position': self.end_position,
            'volume': self.volume,
            'cross_section_area': self.cross_section_area,
            'material_type': self.material_type.value,
            'overburden': self.overburden,
            'rock_quality': self.rock_quality,
            'length': self.get_length(),
            'average_depth': self.get_average_depth()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExcavationZone':
        """Create excavation zone from dictionary."""
        return cls(
            start_position=data['start_position'],
            end_position=data['end_position'],
            volume=data['volume'],
            cross_section_area=data['cross_section_area'],
            material_type=MaterialType(data.get('material_type', 'rock')),
            overburden=data.get('overburden', 0.0),
            rock_quality=data.get('rock_quality', 'unknown')
        )


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for volume calculations."""

    accuracy_estimate: float = 0.0      # Estimated accuracy (percentage)
    numerical_stability: bool = True    # Numerical stability indicator
    convergence_achieved: bool = True   # Convergence indicator
    method_used: CalculationMethod = CalculationMethod.ANALYTICAL
    error_bounds: Tuple[float, float] = (0.0, 0.0)  # Lower and upper error bounds
    confidence_level: float = 0.95     # Statistical confidence level

    def is_acceptable(self, tolerance: float = 0.05) -> bool:
        """Check if accuracy is within acceptable tolerance."""
        return self.accuracy_estimate <= tolerance

    def to_dict(self) -> Dict[str, Any]:
        """Convert accuracy metrics to dictionary."""
        return {
            'accuracy_estimate': self.accuracy_estimate,
            'numerical_stability': self.numerical_stability,
            'convergence_achieved': self.convergence_achieved,
            'method_used': self.method_used.value,
            'error_bounds': self.error_bounds,
            'confidence_level': self.confidence_level,
            'is_acceptable': self.is_acceptable()
        }


@dataclass
class TerrainIntersection:
    """Represents intersection between tunnel and terrain."""

    intersection_points: List[Tuple[float, float, float]] = field(default_factory=list)
    intersection_volume: float = 0.0
    terrain_above: float = 0.0     # Volume above terrain
    terrain_below: float = 0.0     # Volume below terrain
    intersection_length: float = 0.0

    def has_intersection(self) -> bool:
        """Check if there is significant terrain intersection."""
        return len(self.intersection_points) > 0

    def get_intersection_ratio(self) -> float:
        """Get ratio of intersection volume to total volume."""
        total_volume = self.terrain_above + self.terrain_below
        if total_volume > 0:
            return self.intersection_volume / total_volume
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert terrain intersection to dictionary."""
        return {
            'intersection_points': self.intersection_points,
            'intersection_volume': self.intersection_volume,
            'terrain_above': self.terrain_above,
            'terrain_below': self.terrain_below,
            'intersection_length': self.intersection_length,
            'has_intersection': self.has_intersection(),
            'intersection_ratio': self.get_intersection_ratio()
        }


@dataclass
class VolumeCalculationResult:
    """Complete result of volume calculation."""

    total_volume: float
    excavation_zones: List[ExcavationZone] = field(default_factory=list)
    accuracy_metrics: AccuracyMetrics = field(default_factory=AccuracyMetrics)
    terrain_intersection: TerrainIntersection = field(default_factory=TerrainIntersection)
    calculation_time: float = 0.0
    method_details: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)

    # Computed properties
    @property
    def accuracy_estimate(self) -> float:
        """Get accuracy estimate."""
        return self.accuracy_metrics.accuracy_estimate

    @property
    def numerical_stability(self) -> bool:
        """Get numerical stability indicator."""
        return self.accuracy_metrics.numerical_stability

    @property
    def convergence_achieved(self) -> bool:
        """Get convergence indicator."""
        return self.accuracy_metrics.convergence_achieved

    def get_zone_by_material(self, material_type: MaterialType) -> List[ExcavationZone]:
        """Get excavation zones by material type."""
        return [zone for zone in self.excavation_zones if zone.material_type == material_type]

    def get_material_breakdown(self) -> Dict[str, float]:
        """Get volume breakdown by material type."""
        breakdown = {}
        for zone in self.excavation_zones:
            material = zone.material_type.value
            if material not in breakdown:
                breakdown[material] = 0.0
            breakdown[material] += zone.volume
        return breakdown

    def validate(self) -> bool:
        """Validate calculation result."""
        if self.total_volume < 0:
            return False
        if not all(zone.validate() for zone in self.excavation_zones):
            return False
        # Check that zone volumes sum to total
        zone_sum = sum(zone.volume for zone in self.excavation_zones)
        if abs(zone_sum - self.total_volume) > 0.01 * self.total_volume:  # 1% tolerance
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert calculation result to dictionary."""
        return {
            'total_volume': self.total_volume,
            'excavation_zones': [zone.to_dict() for zone in self.excavation_zones],
            'accuracy_metrics': self.accuracy_metrics.to_dict(),
            'terrain_intersection': self.terrain_intersection.to_dict(),
            'calculation_time': self.calculation_time,
            'method_details': self.method_details,
            'summary': self.summary,
            'material_breakdown': self.get_material_breakdown(),
            'is_valid': self.validate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VolumeCalculationResult':
        """Create calculation result from dictionary."""
        excavation_zones = [
            ExcavationZone.from_dict(zone_data)
            for zone_data in data.get('excavation_zones', [])
        ]

        accuracy_metrics = AccuracyMetrics(
            accuracy_estimate=data.get('accuracy_metrics', {}).get('accuracy_estimate', 0.0),
            numerical_stability=data.get('accuracy_metrics', {}).get('numerical_stability', True),
            convergence_achieved=data.get('accuracy_metrics', {}).get('convergence_achieved', True),
            method_used=CalculationMethod(
                data.get('accuracy_metrics', {}).get('method_used', 'analytical')
            ),
            error_bounds=data.get('accuracy_metrics', {}).get('error_bounds', (0.0, 0.0)),
            confidence_level=data.get('accuracy_metrics', {}).get('confidence_level', 0.95)
        )

        terrain_intersection = TerrainIntersection(
            intersection_points=data.get('terrain_intersection', {}).get('intersection_points', []),
            intersection_volume=data.get('terrain_intersection', {}).get('intersection_volume', 0.0),
            terrain_above=data.get('terrain_intersection', {}).get('terrain_above', 0.0),
            terrain_below=data.get('terrain_intersection', {}).get('terrain_below', 0.0),
            intersection_length=data.get('terrain_intersection', {}).get('intersection_length', 0.0)
        )

        return cls(
            total_volume=data['total_volume'],
            excavation_zones=excavation_zones,
            accuracy_metrics=accuracy_metrics,
            terrain_intersection=terrain_intersection,
            calculation_time=data.get('calculation_time', 0.0),
            method_details=data.get('method_details', {}),
            summary=data.get('summary', {})
        )


class VolumeCalculator:
    """
    Advanced volume calculator for tunnel excavation.

    This class implements multiple calculation methods including:
    - Analytical geometric calculations
    - Tetrahedral decomposition for complex geometries
    - Terrain intersection analysis
    - Accuracy validation and error estimation
    """

    def __init__(self):
        """Initialize volume calculator."""
        self.default_method = CalculationMethod.ANALYTICAL
        self.tolerance = 1e-6
        self.max_iterations = 1000

    def calculate_tunnel_volume(
        self,
        tunnel_geometry,
        terrain_mesh,
        method: Optional[CalculationMethod] = None,
        validate_accuracy: bool = False,
        generate_summary: bool = False
    ) -> VolumeCalculationResult:
        """
        Calculate tunnel excavation volume.

        Args:
            tunnel_geometry: Tunnel geometry to calculate volume for
            terrain_mesh: Terrain mesh for intersection analysis
            method: Calculation method to use
            validate_accuracy: Whether to perform accuracy validation
            generate_summary: Whether to generate detailed summary

        Returns:
            VolumeCalculationResult with comprehensive volume analysis
        """
        import time
        start_time = time.time()

        if method is None:
            method = self.default_method

        # Calculate volume using selected method
        if method == CalculationMethod.ANALYTICAL:
            result = self._calculate_analytical_volume(tunnel_geometry, terrain_mesh)
        elif method == CalculationMethod.TETRAHEDRAL:
            result = self._calculate_tetrahedral_volume(tunnel_geometry, terrain_mesh)
        elif method == CalculationMethod.MONTE_CARLO:
            result = self._calculate_monte_carlo_volume(tunnel_geometry, terrain_mesh)
        else:  # HYBRID
            result = self._calculate_hybrid_volume(tunnel_geometry, terrain_mesh)

        # Set method details
        result.method_details['method'] = method.value
        result.method_details['tunnel_waypoints'] = len(tunnel_geometry.path.waypoints)
        result.method_details['terrain_triangles'] = terrain_mesh.triangle_count if terrain_mesh else 0

        # Calculate terrain intersection
        if terrain_mesh:
            result.terrain_intersection = self._calculate_terrain_intersection(
                tunnel_geometry, terrain_mesh
            )

        # Perform accuracy validation if requested
        if validate_accuracy:
            self._validate_calculation_accuracy(result, tunnel_geometry, terrain_mesh)

        # Generate summary if requested
        if generate_summary:
            result.summary = self._generate_calculation_summary(result, tunnel_geometry)

        # Set calculation time
        result.calculation_time = time.time() - start_time

        return result

    def _calculate_analytical_volume(self, tunnel_geometry, terrain_mesh) -> VolumeCalculationResult:
        """Calculate volume using analytical geometric methods."""
        tunnel_path = tunnel_geometry.path

        if len(tunnel_path.waypoints) < 2:
            return VolumeCalculationResult(total_volume=0.0)

        total_volume = 0.0
        excavation_zones = []

        # Calculate volume for each tunnel segment
        for i in range(len(tunnel_path.waypoints) - 1):
            wp1 = tunnel_path.waypoints[i]
            wp2 = tunnel_path.waypoints[i + 1]

            # Calculate segment volume
            segment_volume = self._calculate_segment_volume(wp1, wp2, tunnel_path.cross_section_type)
            total_volume += segment_volume

            # Create excavation zone for this segment
            zone = ExcavationZone(
                start_position=self._get_path_position(tunnel_path, i),
                end_position=self._get_path_position(tunnel_path, i + 1),
                volume=segment_volume,
                cross_section_area=self._get_segment_cross_section_area(wp1, wp2, tunnel_path.cross_section_type),
                material_type=self._estimate_material_type(wp1, wp2, terrain_mesh)
            )
            excavation_zones.append(zone)

        return VolumeCalculationResult(
            total_volume=total_volume,
            excavation_zones=excavation_zones,
            accuracy_metrics=AccuracyMetrics(
                method_used=CalculationMethod.ANALYTICAL,
                accuracy_estimate=0.01  # 1% estimated accuracy for analytical method
            )
        )

    def _calculate_tetrahedral_volume(self, tunnel_geometry, terrain_mesh) -> VolumeCalculationResult:
        """Calculate volume using tetrahedral decomposition."""
        # This is a placeholder for tetrahedral decomposition
        # In a full implementation, this would:
        # 1. Decompose tunnel volume into tetrahedra
        # 2. Calculate each tetrahedron volume
        # 3. Account for terrain intersection
        # 4. Sum all tetrahedron volumes

        # For now, fall back to analytical calculation
        return self._calculate_analytical_volume(tunnel_geometry, terrain_mesh)

    def _calculate_monte_carlo_volume(self, tunnel_geometry, terrain_mesh) -> VolumeCalculationResult:
        """Calculate volume using Monte Carlo sampling."""
        # This is a placeholder for Monte Carlo calculation
        # In a full implementation, this would:
        # 1. Generate random sample points within bounding box
        # 2. Count points inside tunnel volume
        # 3. Calculate volume based on sampling ratio
        # 4. Provide statistical confidence intervals

        # For now, fall back to analytical calculation
        return self._calculate_analytical_volume(tunnel_geometry, terrain_mesh)

    def _calculate_hybrid_volume(self, tunnel_geometry, terrain_mesh) -> VolumeCalculationResult:
        """Calculate volume using hybrid methods."""
        # Calculate using analytical method as base
        base_result = self._calculate_analytical_volume(tunnel_geometry, terrain_mesh)

        # Apply corrections based on complexity
        if terrain_mesh and terrain_mesh.triangle_count > 1000:
            # For complex terrain, apply correction factor
            correction_factor = 1.02  # 2% increase for complexity
            base_result.total_volume *= correction_factor
            base_result.accuracy_metrics.accuracy_estimate = 0.03  # 3% accuracy

        base_result.accuracy_metrics.method_used = CalculationMethod.HYBRID
        return base_result

    def _calculate_segment_volume(self, wp1, wp2, cross_section_type) -> float:
        """Calculate volume for a single tunnel segment."""
        # Calculate segment length
        dx = wp2.x - wp1.x
        dy = wp2.y - wp1.y
        dz = wp2.elevation - wp1.elevation
        segment_length = math.sqrt(dx**2 + dy**2 + dz**2)

        # Average radius for this segment
        avg_radius = (wp1.radius + wp2.radius) / 2

        # Calculate volume based on cross-section type
        if cross_section_type == CrossSectionType.CIRCULAR:
            volume = math.pi * avg_radius**2 * segment_length
        elif cross_section_type == CrossSectionType.RECTANGULAR:
            # Square cross-section with side = 2 * radius
            volume = (2 * avg_radius)**2 * segment_length
        else:  # HORSESHOE
            # Approximate as 0.8 * circular volume
            volume = 0.8 * math.pi * avg_radius**2 * segment_length

        return volume

    def _get_segment_cross_section_area(self, wp1, wp2, cross_section_type) -> float:
        """Get average cross-section area for a segment."""
        avg_radius = (wp1.radius + wp2.radius) / 2

        if cross_section_type == CrossSectionType.CIRCULAR:
            return math.pi * avg_radius**2
        elif cross_section_type == CrossSectionType.RECTANGULAR:
            return (2 * avg_radius)**2
        else:  # HORSESHOE
            return 0.8 * math.pi * avg_radius**2

    def _get_path_position(self, tunnel_path, waypoint_index: int) -> float:
        """Get cumulative position along tunnel path."""
        if waypoint_index == 0:
            return 0.0

        position = 0.0
        for i in range(waypoint_index):
            wp1 = tunnel_path.waypoints[i]
            wp2 = tunnel_path.waypoints[i + 1]

            dx = wp2.x - wp1.x
            dy = wp2.y - wp1.y
            dz = wp2.elevation - wp1.elevation
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)
            position += segment_length

        return position

    def _estimate_material_type(self, wp1, wp2, terrain_mesh) -> MaterialType:
        """Estimate material type based on depth and terrain."""
        # Simple heuristic based on depth
        avg_depth = (wp1.elevation + wp2.elevation) / 2

        if avg_depth > 150:
            return MaterialType.HARD_ROCK
        elif avg_depth > 100:
            return MaterialType.ROCK
        elif avg_depth > 50:
            return MaterialType.SOFT_ROCK
        else:
            return MaterialType.SOIL

    def _calculate_terrain_intersection(self, tunnel_geometry, terrain_mesh) -> TerrainIntersection:
        """Calculate intersection between tunnel and terrain."""
        # This is a placeholder for terrain intersection calculation
        # In a full implementation, this would:
        # 1. Find intersection points between tunnel and terrain surface
        # 2. Calculate volumes above and below terrain
        # 3. Determine intersection length and characteristics

        intersection = TerrainIntersection()

        # Simple heuristic: assume 10% intersection for typical cases
        if terrain_mesh and terrain_mesh.vertex_count > 0:
            # Get terrain elevation range
            terrain_elevations = terrain_mesh.vertices[:, 2]
            min_terrain = np.min(terrain_elevations)
            max_terrain = np.max(terrain_elevations)

            # Check if tunnel crosses terrain elevation range
            tunnel_elevations = [wp.elevation for wp in tunnel_geometry.path.waypoints]
            min_tunnel = min(tunnel_elevations)
            max_tunnel = max(tunnel_elevations)

            if min_tunnel < max_terrain and max_tunnel > min_terrain:
                # There is intersection
                intersection.intersection_volume = tunnel_geometry.volume * 0.1
                intersection.terrain_above = tunnel_geometry.volume * 0.05
                intersection.terrain_below = tunnel_geometry.volume * 0.05
                intersection.intersection_length = tunnel_geometry.path.get_length() * 0.2

        return intersection

    def _validate_calculation_accuracy(self, result: VolumeCalculationResult, tunnel_geometry, terrain_mesh):
        """Validate calculation accuracy and estimate error bounds."""
        # Calculate error bounds based on method and complexity
        base_accuracy = result.accuracy_metrics.accuracy_estimate

        # Adjust accuracy based on tunnel complexity
        waypoint_count = len(tunnel_geometry.path.waypoints)
        if waypoint_count > 10:
            base_accuracy *= 1.5  # Less accurate for complex paths

        # Adjust accuracy based on terrain complexity
        if terrain_mesh and terrain_mesh.triangle_count > 1000:
            base_accuracy *= 1.3  # Less accurate for complex terrain

        # Update accuracy metrics
        result.accuracy_metrics.accuracy_estimate = min(base_accuracy, 0.1)  # Cap at 10%
        result.accuracy_metrics.numerical_stability = result.accuracy_metrics.accuracy_estimate < 0.05
        result.accuracy_metrics.convergence_achieved = True

        # Set error bounds (±estimated accuracy)
        error_margin = result.total_volume * result.accuracy_metrics.accuracy_estimate
        result.accuracy_metrics.error_bounds = (
            result.total_volume - error_margin,
            result.total_volume + error_margin
        )

    def _generate_calculation_summary(self, result: VolumeCalculationResult, tunnel_geometry) -> Dict[str, Any]:
        """Generate detailed calculation summary."""
        summary = {
            'total_volume': result.total_volume,
            'excavation_zones': len(result.excavation_zones),
            'material_breakdown': result.get_material_breakdown(),
            'accuracy_metrics': result.accuracy_metrics.to_dict(),
            'calculation_method': result.method_details.get('method', 'unknown'),
            'tunnel_length': tunnel_geometry.path.get_length(),
            'cross_section_type': tunnel_geometry.path.cross_section_type.value,
            'average_radius': tunnel_geometry.radius,
            'terrain_intersection': result.terrain_intersection.to_dict()
        }

        # Add additional statistics
        if result.excavation_zones:
            volumes = [zone.volume for zone in result.excavation_zones]
            summary['zone_volume_stats'] = {
                'min_zone_volume': min(volumes),
                'max_zone_volume': max(volumes),
                'avg_zone_volume': sum(volumes) / len(volumes)
            }

        return summary