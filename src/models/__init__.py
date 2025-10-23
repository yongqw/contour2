"""
Data models for Terrain Tunneling Calculator.

This module contains all the core data structures used throughout the application,
including contour data, terrain meshes, tunnel geometry, and visualization states.
"""

from .contour_data import ContourData, ContourLine, ContourMetadata
from .terrain_mesh import TerrainMesh

__all__ = [
    "ContourData",
    "ContourLine",
    "ContourMetadata",
    "TerrainMesh"
]