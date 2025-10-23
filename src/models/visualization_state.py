"""
Visualization state management for Terrain Tunneling Calculator.

This module provides models and state management for visualization components,
including camera controls, display options, and interaction state.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np


class ViewMode(Enum):
    """Visualization view modes."""
    CONTOUR_2D = "contour_2d"
    TUNNEL_2D = "tunnel_2d"
    TERRAIN_3D = "terrain_3d"
    TUNNEL_3D = "tunnel_3d"
    CROSS_SECTION = "cross_section"


class InteractionMode(Enum):
    """User interaction modes."""
    VIEW_ONLY = "view_only"
    POINT_SELECTION = "point_selection"
    TUNNEL_EDITING = "tunnel_editing"
    MEASUREMENT = "measurement"


@dataclass
class CameraState:
    """Camera position and orientation state."""
    position: Tuple[float, float, float] = (0.0, 0.0, 100.0)
    target: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    up_vector: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    fov: float = 45.0  # Field of view in degrees
    zoom: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert camera state to dictionary."""
        return {
            'position': self.position,
            'target': self.target,
            'up_vector': self.up_vector,
            'fov': self.fov,
            'zoom': self.zoom
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CameraState':
        """Create camera state from dictionary."""
        return cls(
            position=tuple(data.get('position', (0.0, 0.0, 100.0))),
            target=tuple(data.get('target', (0.0, 0.0, 0.0))),
            up_vector=tuple(data.get('up_vector', (0.0, 1.0, 0.0))),
            fov=data.get('fov', 45.0),
            zoom=data.get('zoom', 1.0)
        )


@dataclass
class DisplayOptions:
    """Visualization display options and settings."""
    show_contours: bool = True
    show_tunnel: bool = True
    show_terrain_mesh: bool = True
    show_elevation_labels: bool = False
    show_grid: bool = True
    show_axis: bool = True

    # Color settings
    contour_color: str = "#2E86AB"
    tunnel_color: str = "#A23B72"
    terrain_color: str = "#F18F01"
    selected_color: str = "#C73E1D"

    # Transparency settings
    terrain_transparency: float = 0.8
    tunnel_transparency: float = 0.9

    # Line widths and sizes
    contour_width: float = 1.5
    tunnel_width: float = 3.0
    point_size: float = 8.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert display options to dictionary."""
        return {
            'show_contours': self.show_contours,
            'show_tunnel': self.show_tunnel,
            'show_terrain_mesh': self.show_terrain_mesh,
            'show_elevation_labels': self.show_elevation_labels,
            'show_grid': self.show_grid,
            'show_axis': self.show_axis,
            'contour_color': self.contour_color,
            'tunnel_color': self.tunnel_color,
            'terrain_color': self.terrain_color,
            'selected_color': self.selected_color,
            'terrain_transparency': self.terrain_transparency,
            'tunnel_transparency': self.tunnel_transparency,
            'contour_width': self.contour_width,
            'tunnel_width': self.tunnel_width,
            'point_size': self.point_size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DisplayOptions':
        """Create display options from dictionary."""
        return cls(
            show_contours=data.get('show_contours', True),
            show_tunnel=data.get('show_tunnel', True),
            show_terrain_mesh=data.get('show_terrain_mesh', True),
            show_elevation_labels=data.get('show_elevation_labels', False),
            show_grid=data.get('show_grid', True),
            show_axis=data.get('show_axis', True),
            contour_color=data.get('contour_color', "#2E86AB"),
            tunnel_color=data.get('tunnel_color', "#A23B72"),
            terrain_color=data.get('terrain_color', "#F18F01"),
            selected_color=data.get('selected_color', "#C73E1D"),
            terrain_transparency=data.get('terrain_transparency', 0.8),
            tunnel_transparency=data.get('tunnel_transparency', 0.9),
            contour_width=data.get('contour_width', 1.5),
            tunnel_width=data.get('tunnel_width', 3.0),
            point_size=data.get('point_size', 8.0)
        )


@dataclass
class SelectionState:
    """State for user selections and interactions."""
    selected_points: List[Tuple[float, float]] = field(default_factory=list)
    selected_waypoints: List[int] = field(default_factory=list)  # Waypoint indices
    selection_mode: str = "point"  # "point", "area", "path"
    selection_tolerance: float = 5.0  # Pixels for point selection

    # Temporary selection state
    hover_point: Optional[Tuple[float, float]] = None
    drag_start: Optional[Tuple[float, float]] = None
    drag_end: Optional[Tuple[float, float]] = None

    def clear_selection(self) -> None:
        """Clear all selections."""
        self.selected_points.clear()
        self.selected_waypoints.clear()
        self.hover_point = None
        self.drag_start = None
        self.drag_end = None

    def add_point(self, x: float, y: float) -> None:
        """Add a point to selection."""
        self.selected_points.append((x, y))

    def remove_point(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        """Remove a point from selection if within tolerance."""
        for i, (px, py) in enumerate(self.selected_points):
            if abs(px - x) <= tolerance and abs(py - y) <= tolerance:
                del self.selected_points[i]
                return True
        return False

    def is_point_selected(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        """Check if a point is selected within tolerance."""
        for px, py in self.selected_points:
            if abs(px - x) <= tolerance and abs(py - y) <= tolerance:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert selection state to dictionary."""
        return {
            'selected_points': self.selected_points,
            'selected_waypoints': self.selected_waypoints,
            'selection_mode': self.selection_mode,
            'selection_tolerance': self.selection_tolerance,
            'hover_point': self.hover_point,
            'drag_start': self.drag_start,
            'drag_end': self.drag_end
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectionState':
        """Create selection state from dictionary."""
        return cls(
            selected_points=data.get('selected_points', []),
            selected_waypoints=data.get('selected_waypoints', []),
            selection_mode=data.get('selection_mode', "point"),
            selection_tolerance=data.get('selection_tolerance', 5.0),
            hover_point=data.get('hover_point'),
            drag_start=data.get('drag_start'),
            drag_end=data.get('drag_end')
        )


@dataclass
class VisualizationState:
    """Main visualization state container."""
    view_mode: ViewMode = ViewMode.CONTOUR_2D
    interaction_mode: InteractionMode = InteractionMode.VIEW_ONLY
    camera: CameraState = field(default_factory=CameraState)
    display_options: DisplayOptions = field(default_factory=DisplayOptions)
    selection: SelectionState = field(default_factory=SelectionState)

    # Viewport settings
    viewport_size: Tuple[int, int] = (800, 600)
    viewport_bounds: Tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)  # (x_min, y_min, x_max, y_max)

    # Animation state
    animation_active: bool = False
    animation_progress: float = 0.0
    animation_speed: float = 1.0

    def set_view_mode(self, mode: ViewMode) -> None:
        """Set the current view mode."""
        self.view_mode = mode

    def set_interaction_mode(self, mode: InteractionMode) -> None:
        """Set the current interaction mode."""
        self.interaction_mode = mode

    def get_view_bounds(self) -> Tuple[float, float, float, float]:
        """Get current view bounds."""
        return self.viewport_bounds

    def set_view_bounds(self, x_min: float, y_min: float, x_max: float, y_max: float) -> None:
        """Set view bounds."""
        self.viewport_bounds = (x_min, y_min, x_max, y_max)

    def zoom_to_bounds(self, bounds: Tuple[float, float, float, float]) -> None:
        """Zoom to specific bounds."""
        self.set_view_bounds(*bounds)
        # Adjust camera zoom accordingly
        x_range = bounds[2] - bounds[0]
        y_range = bounds[3] - bounds[1]
        self.camera.zoom = min(800.0 / x_range, 600.0 / y_range)

    def reset_view(self) -> None:
        """Reset view to default state."""
        self.camera = CameraState()
        self.viewport_bounds = (0.0, 0.0, 100.0, 100.0)
        self.animation_progress = 0.0
        self.animation_active = False

    def start_animation(self) -> None:
        """Start animation."""
        self.animation_active = True
        self.animation_progress = 0.0

    def stop_animation(self) -> None:
        """Stop animation."""
        self.animation_active = False
        self.animation_progress = 0.0

    def update_animation(self, delta_time: float) -> None:
        """Update animation progress."""
        if self.animation_active:
            self.animation_progress += delta_time * self.animation_speed
            if self.animation_progress >= 1.0:
                self.animation_progress = 1.0
                self.animation_active = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert visualization state to dictionary."""
        return {
            'view_mode': self.view_mode.value,
            'interaction_mode': self.interaction_mode.value,
            'camera': self.camera.to_dict(),
            'display_options': self.display_options.to_dict(),
            'selection': self.selection.to_dict(),
            'viewport_size': self.viewport_size,
            'viewport_bounds': self.viewport_bounds,
            'animation_active': self.animation_active,
            'animation_progress': self.animation_progress,
            'animation_speed': self.animation_speed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualizationState':
        """Create visualization state from dictionary."""
        return cls(
            view_mode=ViewMode(data.get('view_mode', 'contour_2d')),
            interaction_mode=InteractionMode(data.get('interaction_mode', 'view_only')),
            camera=CameraState.from_dict(data.get('camera', {})),
            display_options=DisplayOptions.from_dict(data.get('display_options', {})),
            selection=SelectionState.from_dict(data.get('selection', {})),
            viewport_size=tuple(data.get('viewport_size', (800, 600))),
            viewport_bounds=tuple(data.get('viewport_bounds', (0.0, 0.0, 100.0, 100.0))),
            animation_active=data.get('animation_active', False),
            animation_progress=data.get('animation_progress', 0.0),
            animation_speed=data.get('animation_speed', 1.0)
        )


# Utility functions for visualization state management
def create_default_2d_state() -> VisualizationState:
    """Create default 2D visualization state."""
    state = VisualizationState()
    state.view_mode = ViewMode.CONTOUR_2D
    state.interaction_mode = InteractionMode.POINT_SELECTION
    state.camera.position = (50.0, 50.0, 100.0)
    state.camera.target = (50.0, 50.0, 0.0)
    return state


def create_default_3d_state() -> VisualizationState:
    """Create default 3D visualization state."""
    state = VisualizationState()
    state.view_mode = ViewMode.TERRAIN_3D
    state.interaction_mode = InteractionMode.VIEW_ONLY
    state.camera.position = (50.0, 100.0, 150.0)
    state.camera.target = (50.0, 50.0, 0.0)
    state.camera.fov = 60.0
    return state


def create_tunnel_planning_state() -> VisualizationState:
    """Create visualization state optimized for tunnel planning."""
    state = create_default_2d_state()
    state.interaction_mode = InteractionMode.TUNNEL_EDITING
    state.display_options.show_tunnel = True
    state.display_options.show_contours = True
    state.display_options.tunnel_width = 4.0
    state.display_options.point_size = 10.0
    state.selection.selection_tolerance = 10.0
    return state