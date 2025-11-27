"""
Pytest configuration and fixtures.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.contour_data import ContourData, ContourLine
from models.terrain_mesh import TerrainMesh, Triangle
from models.tunnel_geometry import TunnelGeometry, TunnelPath, TunnelWaypoint, CrossSectionType


@pytest.fixture
def sample_terrain_mesh():
    """Create a simple terrain mesh for testing."""
    # Create a pyramid mesh
    vertices = np.array([
        [0, 0, 0],      # Base corner 1
        [1, 0, 0],      # Base corner 2
        [1, 1, 0],      # Base corner 3
        [0, 1, 0],      # Base corner 4
        [0.5, 0.5, 0.5]  # Peak
    ])
    
    triangles = [
        Triangle(vertex_indices=[0, 1, 4]),  # Side 1
        Triangle(vertex_indices=[1, 2, 4]),  # Side 2
        Triangle(vertex_indices=[2, 3, 4]),  # Side 3
        Triangle(vertex_indices=[3, 0, 4]),  # Side 4
        Triangle(vertex_indices=[0, 3, 2]),  # Base part 1
        Triangle(vertex_indices=[0, 2, 1])   # Base part 2
    ]
    
    return TerrainMesh(vertices=vertices, triangles=triangles)


@pytest.fixture
def sample_tunnel_geometry():
    """Create a simple tunnel geometry for testing."""
    waypoints = [
        TunnelWaypoint(x=0, y=0, elevation=100, radius=5),
        TunnelWaypoint(x=100, y=0, elevation=100, radius=5)
    ]
    
    path = TunnelPath(waypoints=waypoints, cross_section_type=CrossSectionType.CIRCULAR)
    return TunnelGeometry(path=path)


@pytest.fixture
def sample_contour_data():
    """Create simple contour data for testing."""
    # Square contour at elevation 100
    contour1 = ContourLine(
        elevation=100.0,
        points=np.array([
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0]  # Close the loop
        ])
    )
    
    # Square contour at elevation 110
    contour2 = ContourLine(
        elevation=110.0,
        points=np.array([
            [2, 2],
            [8, 2],
            [8, 8],
            [2, 8],
            [2, 2]  # Close the loop
        ])
    )
    
    return ContourData(
        name="Test Terrain",
        contours=[contour1, contour2]
    )