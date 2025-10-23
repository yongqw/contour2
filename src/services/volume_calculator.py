"""
Volume calculation service for Terrain Tunneling Calculator.

This service provides advanced volume calculation algorithms including
tetrahedral decomposition, terrain intersection analysis, and accuracy validation.
"""

import numpy as np
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from models.volume_calculator import (
    VolumeCalculator as VolumeCalculatorModel,
    VolumeCalculationResult,
    ExcavationZone,
    MaterialType,
    CalculationMethod,
    AccuracyMetrics,
    TerrainIntersection
)
from models.tunnel_geometry import TunnelGeometry, TunnelPath, CrossSectionType
from models.terrain_mesh import TerrainMesh


class VolumeCalculator:
    """
    Service layer for volume calculations with advanced algorithms.

    This class provides a service interface to the VolumeCalculator model
    with additional business logic and validation capabilities.
    """

    def __init__(self):
        """Initialize volume calculator service."""
        self.calculator = VolumeCalculatorModel()
        self.validation_framework = self._setup_validation()

    def _setup_validation(self):
        """Set up validation framework."""
        # Placeholder for validation setup
        return None

    def calculate_tunnel_volume(
        self,
        tunnel_geometry: TunnelGeometry,
        terrain_mesh: Optional[TerrainMesh] = None,
        method: Optional[str] = None,
        validate_accuracy: bool = False,
        generate_summary: bool = False
    ) -> VolumeCalculationResult:
        """
        Calculate tunnel excavation volume.

        Args:
            tunnel_geometry: Tunnel geometry to calculate volume for
            terrain_mesh: Terrain mesh for intersection analysis
            method: Calculation method ('analytical', 'tetrahedral', 'monte_carlo', 'hybrid')
            validate_accuracy: Whether to perform accuracy validation
            generate_summary: Whether to generate detailed summary

        Returns:
            VolumeCalculationResult with comprehensive volume analysis
        """
        # Convert method to enum
        calc_method = None
        if method:
            # If method is already a CalculationMethod enum, use it directly
            if isinstance(method, CalculationMethod):
                calc_method = method
            # If method is a string, convert it to enum
            elif isinstance(method, str):
                method_map = {
                    'analytical': CalculationMethod.ANALYTICAL,
                    'tetrahedral': CalculationMethod.TETRAHEDRAL,
                    'monte_carlo': CalculationMethod.MONTE_CARLO,
                    'hybrid': CalculationMethod.HYBRID
                }
                calc_method = method_map.get(method.lower(), CalculationMethod.ANALYTICAL)
            else:
                # Fallback to analytical method
                calc_method = CalculationMethod.ANALYTICAL

        # Delegate to model calculator
        return self.calculator.calculate_tunnel_volume(
            tunnel_geometry=tunnel_geometry,
            terrain_mesh=terrain_mesh,
            method=calc_method,
            validate_accuracy=validate_accuracy,
            generate_summary=generate_summary
        )

    def validate_calculation_input(
        self,
        tunnel_geometry: TunnelGeometry,
        terrain_mesh: Optional[TerrainMesh] = None
    ) -> bool:
        """
        Validate input data for volume calculation.

        Args:
            tunnel_geometry: Tunnel geometry to validate
            terrain_mesh: Terrain mesh to validate

        Returns:
            True if input is valid for calculation
        """
        # Validate tunnel geometry
        if not tunnel_geometry or not tunnel_geometry.path:
            return False

        if len(tunnel_geometry.path.waypoints) < 2:
            return False

        # Validate terrain mesh if provided
        if terrain_mesh:
            if terrain_mesh.vertex_count == 0 or terrain_mesh.triangle_count == 0:
                return False

        return True

    def get_calculation_methods(self) -> List[str]:
        """Get available calculation methods."""
        return ['analytical', 'tetrahedral', 'monte_carlo', 'hybrid']

    def estimate_calculation_time(
        self,
        tunnel_geometry: TunnelGeometry,
        terrain_mesh: Optional[TerrainMesh] = None,
        method: str = 'analytical'
    ) -> float:
        """
        Estimate calculation time in seconds.

        Args:
            tunnel_geometry: Tunnel geometry
            terrain_mesh: Terrain mesh
            method: Calculation method

        Returns:
            Estimated calculation time in seconds
        """
        base_time = 0.1  # Base calculation time

        # Adjust based on tunnel complexity
        waypoint_count = len(tunnel_geometry.path.waypoints)
        complexity_factor = 1.0 + (waypoint_count - 2) * 0.1

        # Adjust based on terrain complexity
        if terrain_mesh:
            terrain_factor = 1.0 + (terrain_mesh.triangle_count / 1000) * 0.5
        else:
            terrain_factor = 1.0

        # Adjust based on method
        method_factors = {
            'analytical': 1.0,
            'tetrahedral': 5.0,
            'monte_carlo': 10.0,
            'hybrid': 3.0
        }

        method_factor = method_factors.get(method, 1.0)

        estimated_time = base_time * complexity_factor * terrain_factor * method_factor

        return min(estimated_time, 60.0)  # Cap at 1 minute