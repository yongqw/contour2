"""
Contour view GUI component for Terrain Tunneling Calculator.

This module provides the 2D visualization panel for displaying terrain contours,
tunnel paths, and user interactions.
"""

import tkinter as tk
from tkinter import ttk, font as tkfont, Menu
from typing import Optional, Callable, List, Tuple, Dict, Any
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.collections import LineCollection

from models.contour_data import ContourData
from models.tunnel_geometry import TunnelGeometry, TunnelWaypoint
from models.visualization_state import VisualizationState, InteractionMode
from services.visualization_3d import Visualization3DService
from services.python_3d_renderer import Python3DRenderer


class ContourView(ttk.Frame):
    """2D contour visualization panel with tunnel planning support."""

    def __init__(
        self,
        parent: tk.Widget,
        visualization_state: VisualizationState,
        on_point_selected: Optional[Callable[[float, float], None]] = None,
        on_waypoint_selected: Optional[Callable[[int], None]] = None,
        scale_factor: float = 1.0
    ):
        """
        Initialize contour view.

        Args:
            parent: Parent widget
            visualization_state: Shared visualization state
            on_point_selected: Callback when point is selected on map
            on_waypoint_selected: Callback when waypoint is selected
            scale_factor: DPI scaling factor for fonts and sizes
        """
        super().__init__(parent)

        self.visualization_state = visualization_state
        self.on_point_selected = on_point_selected
        self.on_waypoint_selected = on_waypoint_selected
        self.scale_factor = scale_factor

        self.contour_data: Optional[ContourData] = None
        self.current_tunnel: Optional[TunnelGeometry] = None
        self.selected_waypoints: List[int] = []

        # Right-click menu state
        self.context_menu_active = False
        self.last_click_position = (0, 0)
        self.right_click_enabled = False  # Only enabled after selecting start and end points

        self._setup_matplotlib()
        self._setup_ui()
        self._setup_event_handlers()
        self._setup_context_menu()

    def _setup_matplotlib(self):
        """Set up matplotlib figure and axes."""
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.axes = self.figure.add_subplot(111)

        # Set up the plot
        self.axes.set_xlabel('X Coordinate (m)')
        self.axes.set_ylabel('Y Coordinate (m)')
        self.axes.set_title('Terrain Contour Map')
        self.axes.grid(True, alpha=0.3)
        self.axes.set_aspect('equal')

        # Initialize plot elements
        self.contour_lines = []
        self.tunnel_line = None
        self.waypoint_scatter = None
        self.selected_points_scatter = None
        self.selection_patches = []

    def _setup_ui(self):
        """Set up the user interface with DPI scaling and better contrast."""
        # Main container with dark background for better contrast
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Set background color for better visibility
        try:
            main_frame.configure(bg='#1E1E1E')
        except:
            pass  # Background color not supported

        # Create matplotlib canvas
        self.canvas = FigureCanvasTkAgg(self.figure, master=main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Create toolbar
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)


    
        # Enhanced toolbar configuration for high DPI
        try:
            # Scale toolbar icon size if possible
            toolbar_size = max(int(20 * self.scale_factor), 24)

            # Additional DPI-aware toolbar configuration
            # Try to set icon size for all toolbar items
            for toolbar_item in self.toolbar.toolitems:
                if hasattr(toolbar_item, 'set_iconsize'):
                    try:
                        toolbar_item.set_iconsize(toolbar_size)
                    except:
                        pass

            # Update toolbar layout
            self.toolbar.update()

            # Try to set DPI awareness for matplotlib window
            try:
                self.canvas.manager.set_window_title("Contour View")
                # Set DPI scaling for tkinter window (helps with matplotlib integration)
                if hasattr(self.canvas.manager, 'window'):
                    self.canvas.manager.window.tk.call('tk', 'scaling', 1.0)
            except Exception as e:
                print(f"DEBUG: Toolbar DPI scaling attempt: {e}")
                pass

        except Exception as e:
            print(f"DEBUG: Toolbar configuration failed: {e}")
            pass  # Continue even if toolbar scaling fails

        # Enhanced toolbar font scaling for tooltips and text
        try:
            # Find toolbar frame and enhance fonts
            toolbar_children = self.toolbar.winfo_children()
            for child in toolbar_children:
                try:
                    # Try to configure button fonts and tooltips
                    if hasattr(child, 'configure'):
                        # Scale button text if any
                        current_config = child.configure()
                        if 'font' in current_config:
                            font_size = max(int(9 * self.scale_factor), 11)
                            child.configure(font=("Arial", font_size))

                        # Try to enhance tooltip font size (if available)
                        if hasattr(child, 'tooltip') and child.tooltip:
                            try:
                                tooltip_font = tkfont.Font(size=max(int(9 * self.scale_factor), 11))
                                if hasattr(child.tooltip, 'configure'):
                                    child.tooltip.configure(font=tooltip_font)
                            except:
                                pass
                except:
                    pass

            # Try to directly configure matplotlib toolbar tooltip fonts
            if hasattr(self.toolbar, '_message'):
                # Some matplotlib versions use _message for tooltips
                try:
                    message_font = tkfont.Font(size=max(int(9 * self.scale_factor), 11))
                    if hasattr(self.toolbar, 'configure'):
                        self.toolbar.configure(font=message_font)
                except:
                    pass

            # Configure toolbar tooltip delay and appearance for high DPI
            try:
                # Access matplotlib's tooltip configuration if available
                if hasattr(self.toolbar, 'message'):
                    # Scale tooltip font size
                    import matplotlib.font_manager as fm
                    tooltip_font_prop = fm.FontProperties(size=max(int(9 * self.scale_factor), 11))
                    if hasattr(self.toolbar, 'message'):
                        self.toolbar.message.set_font(tooltip_font_prop)
            except:
                pass

        except Exception as e:
            print(f"DEBUG: Enhanced toolbar font scaling: {e}")
            pass

    def _setup_event_handlers(self):
        """Set up matplotlib event handlers."""
        # Mouse events
        self.canvas.mpl_connect('button_press_event', self._on_mouse_click)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_motion)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('scroll_event', self._on_mouse_scroll)

        # Keyboard events
        self.canvas.mpl_connect('key_press_event', self._on_key_press)

        # Track mouse position
        self.mouse_pressed = False
        self.drag_start = None

    def _setup_context_menu(self):
        """Set up right-click context menu."""
        # Create context menu
        self.context_menu = Menu(self, tearoff=0)

        # Plan Tunnel menu item
        self.context_menu.add_command(
            label="🛠️ Plan Tunnel",
            command=self._on_plan_tunnel_clicked,
            font=tkfont.Font(family="Arial", size=int(10 * self.scale_factor))
        )

        # View mode submenu
        view_mode_menu = Menu(self.context_menu, tearoff=0)
        view_mode_menu.add_command(
            label="📐 2D Contour View",
            command=lambda: self._on_view_mode_clicked("2d_contour")
        )
        view_mode_menu.add_command(
            label="🗺️ 3D Terrain View",
            command=lambda: self._on_view_mode_clicked("3d_terrain")
        )
        view_mode_menu.add_command(
            label="🌐 3D Integrated View (HTML)",
            command=lambda: self._on_view_mode_clicked("3d_integrated_html")
        )
        view_mode_menu.add_command(
            label="🐍 3D Integrated View (Python)",
            command=lambda: self._on_view_mode_clicked("3d_integrated_python")
        )
        view_mode_menu.add_separator()
        view_mode_menu.add_command(
            label="📊 Analysis View",
            command=lambda: self._on_view_mode_clicked("analysis")
        )

        self.context_menu.add_cascade(
            label="👁️ View Mode",
            menu=view_mode_menu,
            font=tkfont.Font(family="Arial", size=int(10 * self.scale_factor))
        )

    def _on_plan_tunnel_clicked(self):
        """Handle Plan Tunnel menu item click."""
        if self.right_click_enabled:
            # Emit event to trigger tunnel planning using existing selected points
            # This will trigger the same logic as the main menu Plan Tunnel button
            self.event_generate("<<PlanTunnel>>")

    def _on_view_mode_clicked(self, view_mode: str):
        """Handle View Mode menu item click."""
        # Always allow view mode change, but show info if no points selected
        if not self.right_click_enabled:
            try:
                import tkinter.messagebox as messagebox
                messagebox.showinfo("View Mode",
                    f"View mode changed to: {view_mode}\n\n"
                    "Note: For best results, select start and end points first "
                    "to see the tunnel in the 3D views.")
            except:
                pass

        # Always emit the view mode change signal
        # Store the current view mode in a temporary attribute for the handler to access
        self._current_view_mode = view_mode
        self.event_generate("<<ViewModeChanged>>")

    def set_contour_data(self, contour_data: ContourData):
        """Set the contour data to display."""
        self.contour_data = contour_data
        self._update_display()

    def set_tunnel_geometry(self, tunnel_geometry: Optional[TunnelGeometry]):
        """Set the tunnel geometry to display."""
        self.current_tunnel = tunnel_geometry
        self._update_tunnel_display()

    def add_selected_points(self, points: List[Tuple[float, float]]):
        """Add selected points for tunnel planning."""
        self.visualization_state.selection.selected_points = points
        self._update_selection_display()

    def clear_selected_points(self):
        """Clear all selected points."""
        self.visualization_state.selection.selected_points = []
        self.selected_waypoints = []
        self._update_selection_display()

    def _update_display(self):
        """Update the complete display."""
        self.axes.clear()
        self._setup_axes_style()
        self._draw_contours()
        self._draw_tunnel()
        self._draw_selection()
        self._draw_grid()
        self.canvas.draw()

    def _setup_axes_style(self):
        """Set up axes style and limits with DPI scaling."""
        # Calculate font sizes based on DPI scaling
        label_font_size = max(int(10 * self.scale_factor), 12)
        title_font_size = max(int(12 * self.scale_factor), 14)

        self.axes.set_xlabel('X Coordinate (m)', fontsize=label_font_size)
        self.axes.set_ylabel('Y Coordinate (m)', fontsize=label_font_size)
        self.axes.set_title('Terrain Contour Map - Tunnel Planning', fontsize=title_font_size, fontweight='bold')
        self.axes.grid(True, alpha=0.3)

        # Set tick label sizes
        tick_font_size = max(int(8 * self.scale_factor), 10)
        self.axes.tick_params(axis='both', which='major', labelsize=tick_font_size)

        # Set limits based on data or defaults
        if self.contour_data and self.contour_data.contours:
            bounds = self.contour_data.get_bounds()
            self.axes.set_xlim(bounds.min_x - 10, bounds.max_x + 10)
            self.axes.set_ylim(bounds.min_y - 10, bounds.max_y + 10)
        else:
            self.axes.set_xlim(0, 100)
            self.axes.set_ylim(0, 100)

        self.axes.set_aspect('equal')

    def _draw_contours(self):
        """Draw terrain contour lines."""
        if not self.contour_data:
            return

        # Draw each contour line
        for contour_line in self.contour_data.contours:
            if len(contour_line.points) > 1:
                points = np.array(contour_line.points)

                # Create line segments
                segments = []
                for i in range(len(points) - 1):
                    segments.append([points[i], points[i + 1]])

                if segments:
                    # Create line collection
                    lc = LineCollection(
                        segments,
                        colors=self.visualization_state.display_options.contour_color,
                        linewidths=self.visualization_state.display_options.contour_width,
                        alpha=0.8
                    )
                    self.axes.add_collection(lc)

                # Add elevation labels with DPI scaling
                if self.visualization_state.display_options.show_elevation_labels:
                    mid_point = points[len(points) // 2]
                    elevation_font_size = max(int(8 * self.scale_factor), 10)
                    self.axes.annotate(
                        f'{contour_line.elevation:.0f}m',
                        xy=mid_point,
                        fontsize=elevation_font_size,
                        ha='center',
                        va='bottom',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
                    )

    def _draw_tunnel(self):
        """Draw tunnel path and waypoints."""
        if not self.current_tunnel:
            return

        tunnel_path = self.current_tunnel.path

        if len(tunnel_path.waypoints) < 2:
            return

        # Extract coordinates
        x_coords = [wp.x for wp in tunnel_path.waypoints]
        y_coords = [wp.y for wp in tunnel_path.waypoints]

        # Draw tunnel path
        display_options = self.visualization_state.display_options

        # Draw path line
        self.axes.plot(
            x_coords, y_coords,
            color=display_options.tunnel_color,
            linewidth=display_options.tunnel_width,
            alpha=display_options.tunnel_transparency,
            label='Tunnel Path',
            zorder=5
        )

        # Draw tunnel tube (representation of width)
        if display_options.show_tunnel:
            for i in range(len(tunnel_path.waypoints) - 1):
                wp1, wp2 = tunnel_path.waypoints[i], tunnel_path.waypoints[i + 1]

                # Create tube representation
                self._draw_tunnel_segment(wp1, wp2)

        # Draw waypoints
        waypoint_sizes = [display_options.point_size] * len(x_coords)
        waypoint_colors = []

        for i, wp in enumerate(tunnel_path.waypoints):
            if i in self.selected_waypoints:
                waypoint_colors.append(display_options.selected_color)
                waypoint_sizes[i] = display_options.point_size * 1.5
            else:
                waypoint_colors.append(display_options.tunnel_color)

        self.waypoint_scatter = self.axes.scatter(
            x_coords, y_coords,
            c=waypoint_colors,
            s=waypoint_sizes,
            alpha=0.8,
            zorder=10,
            edgecolors='black',
            linewidths=1
        )

        # Add waypoint labels with DPI scaling
        for i, wp in enumerate(tunnel_path.waypoints):
            label = f"WP{i+1}"
            waypoint_font_size = max(int(8 * self.scale_factor), 10)
            self.axes.annotate(
                label,
                xy=(wp.x, wp.y),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=waypoint_font_size,
                alpha=0.8
            )

    def _draw_tunnel_segment(self, wp1: TunnelWaypoint, wp2: TunnelWaypoint):
        """Draw a single tunnel segment with width representation."""
        # Calculate perpendicular direction
        dx = wp2.x - wp1.x
        dy = wp2.y - wp1.y
        length = np.sqrt(dx**2 + dy**2)

        if length == 0:
            return

        # Unit perpendicular vector
        perp_x = -dy / length
        perp_y = dx / length

        # Average radius for this segment
        avg_radius = (wp1.radius + wp2.radius) / 2

        # Create tube outline
        tube_points = [
            (wp1.x + perp_x * avg_radius, wp1.y + perp_y * avg_radius),
            (wp2.x + perp_x * avg_radius, wp2.y + perp_y * avg_radius),
            (wp2.x - perp_x * avg_radius, wp2.y - perp_y * avg_radius),
            (wp1.x - perp_x * avg_radius, wp1.y - perp_y * avg_radius)
        ]

        tube_patch = patches.Polygon(
            tube_points,
            alpha=0.3,
            facecolor=self.visualization_state.display_options.tunnel_color,
            edgecolor=self.visualization_state.display_options.tunnel_color,
            linewidth=1
        )
        self.axes.add_patch(tube_patch)

    def _draw_selection(self):
        """Draw selected points and selection areas."""
        selected_points = self.visualization_state.selection.selected_points

        if not selected_points:
            return

        # Draw selected points
        x_coords = [p[0] for p in selected_points]
        y_coords = [p[1] for p in selected_points]

        self.selected_points_scatter = self.axes.scatter(
            x_coords, y_coords,
            c=self.visualization_state.display_options.selected_color,
            s=self.visualization_state.display_options.point_size * 2,
            marker='^',
            alpha=0.8,
            zorder=15,
            edgecolors='black',
            linewidths=2
        )

        # Draw selection labels with DPI scaling
        for i, (x, y) in enumerate(selected_points):
            label = "Start" if i == 0 else ("End" if i == len(selected_points) - 1 else f"P{i}")
            selection_font_size = max(int(9 * self.scale_factor), 11)
            self.axes.annotate(
                label,
                xy=(x, y),
                xytext=(5, -15),
                textcoords='offset points',
                fontsize=selection_font_size,
                fontweight='bold',
                color=self.visualization_state.display_options.selected_color
            )

        # Draw connecting line if multiple points
        if len(selected_points) > 1:
            self.axes.plot(
                x_coords, y_coords,
                '--',
                color=self.visualization_state.display_options.selected_color,
                linewidth=2,
                alpha=0.6,
                label='Planned Path'
            )

    def _draw_grid(self):
        """Draw coordinate grid if enabled."""
        if not self.visualization_state.display_options.show_grid:
            return

        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()

        # Grid lines
        grid_spacing = 10  # meters
        x_grid = np.arange(xlim[0], xlim[1], grid_spacing)
        y_grid = np.arange(ylim[0], ylim[1], grid_spacing)

        for x in x_grid:
            self.axes.axvline(x, color='gray', alpha=0.2, linewidth=0.5)

        for y in y_grid:
            self.axes.axhline(y, color='gray', alpha=0.2, linewidth=0.5)

    def _on_mouse_click(self, event):
        """Handle mouse click events."""
        if event.inaxes != self.axes:
            return

        x, y = event.xdata, event.ydata

        # Handle right-click context menu
        if event.button == 3:  # Right click
            self._show_context_menu(event)
            return

        # Store click position for context menu use
        self.last_click_position = (x, y)

        # Handle left-click based on interaction mode
        if event.button == 1:  # Left click
            if self.visualization_state.interaction_mode == InteractionMode.POINT_SELECTION:
                if self.on_point_selected:
                    self.on_point_selected(x, y)

                # Add visual feedback
                self._add_click_marker(x, y)

                # Update right-click enabled state
                self._update_right_click_enabled()

            elif self.visualization_state.interaction_mode == InteractionMode.TUNNEL_EDITING:
                # Select waypoint
                self._select_waypoint_at(x, y)
                # Update right-click enabled state for editing mode
                self._update_right_click_enabled()

        self.mouse_pressed = True
        self.drag_start = (x, y)

    def _show_context_menu(self, event):
        """Show context menu at the mouse position."""
        try:
            # Get the canvas coordinates
            canvas_x = self.canvas.get_tk_widget().winfo_pointerx()
            canvas_y = self.canvas.get_tk_widget().winfo_pointery()

            # Post the context menu at the mouse position
            self.context_menu.post(canvas_x, canvas_y)
            self.context_menu_active = True

        except Exception as e:
            print(f"Error showing context menu: {e}")

    def _update_right_click_enabled(self):
        """Update whether right-click menu should be enabled based on current state."""
        # Enable right-click if we have selected points
        if hasattr(self, 'visualization_state') and self.visualization_state:
            # Check for selected points in visualization state's selection
            selected_points_count = len(self.visualization_state.selection.selected_points)
            self.right_click_enabled = selected_points_count >= 2
        else:
            self.right_click_enabled = False

    def _on_mouse_motion(self, event):
        """Handle mouse motion events."""
        # Status bar removed - no coordinate display needed

        # Handle hover effects
        if event.inaxes == self.axes and self.visualization_state.interaction_mode == InteractionMode.TUNNEL_EDITING:
            x, y = event.xdata, event.ydata
            self._update_hover_effect(x, y)

    def _on_mouse_release(self, event):
        """Handle mouse release events."""
        self.mouse_pressed = False
        self.drag_start = None

        # Hide context menu if it's active and right button was released
        if self.context_menu_active and hasattr(self, 'context_menu'):
            self.context_menu.unpost()
            self.context_menu_active = False

    def _on_mouse_scroll(self, event):
        """Handle mouse scroll events for zooming."""
        if event.inaxes != self.axes:
            return

        # Zoom in/out
        scale_factor = 1.1 if event.button == 'up' else 0.9

        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()

        # Get mouse position in data coordinates
        x, y = event.xdata, event.ydata

        # Calculate new limits
        x_range = (xlim[1] - xlim[0]) * scale_factor
        y_range = (ylim[1] - ylim[0]) * scale_factor

        new_xlim = (x - x_range/2, x + x_range/2)
        new_ylim = (y - y_range/2, y + y_range/2)

        self.axes.set_xlim(new_xlim)
        self.axes.set_ylim(new_ylim)

        self.canvas.draw_idle()

    def _on_key_press(self, event):
        """Handle keyboard events."""
        if event.key == 'escape':
            # Cancel current operation
            self.clear_selected_points()
            # Status bar removed - no status message needed

        elif event.key == 'delete' and self.selected_waypoints:
            # Delete selected waypoints
            self._delete_selected_waypoints()

        elif event.key == 'a':
            # Add point mode
            self.visualization_state.set_interaction_mode(InteractionMode.POINT_SELECTION)
            # Status bar removed - no status message needed

        elif event.key == 'e':
            # Edit mode
            self.visualization_state.set_interaction_mode(InteractionMode.TUNNEL_EDITING)
            # Status bar removed - no status message needed

    def _add_click_marker(self, x: float, y: float):
        """Add a temporary click marker."""
        marker = self.axes.scatter(
            [x], [y],
            c='red',
            s=100,
            marker='+',
            alpha=0.7,
            zorder=20
        )
        self.canvas.draw_idle()

        # Remove marker after a short delay
        self.after(500, lambda: self._remove_marker(marker))

    def _remove_marker(self, marker):
        """Remove a click marker."""
        try:
            marker.remove()
            self.canvas.draw_idle()
        except:
            pass

    def _select_waypoint_at(self, x: float, y: float):
        """Select waypoint at given coordinates."""
        if not self.current_tunnel:
            return

        min_distance = float('inf')
        selected_index = None

        tolerance = self.visualization_state.selection.selection_tolerance

        for i, wp in enumerate(self.current_tunnel.path.waypoints):
            distance = np.sqrt((wp.x - x)**2 + (wp.y - y)**2)
            if distance < tolerance and distance < min_distance:
                min_distance = distance
                selected_index = i

        if selected_index is not None:
            if selected_index in self.selected_waypoints:
                self.selected_waypoints.remove(selected_index)
            else:
                self.selected_waypoints.append(selected_index)

            self._update_tunnel_display()

            if self.on_waypoint_selected:
                self.on_waypoint_selected(selected_index)

    def _update_hover_effect(self, x: float, y: float):
        """Update hover effects for waypoints."""
        # This would show waypoint information on hover
        pass

    def _delete_selected_waypoints(self):
        """Delete selected waypoints from tunnel."""
        if not self.current_tunnel or not self.selected_waypoints:
            return

        # Sort indices in descending order to avoid index shifting
        sorted_indices = sorted(self.selected_waypoints, reverse=True)

        for index in sorted_indices:
            self.current_tunnel.path.remove_waypoint(index)

        self.selected_waypoints = []
        self._update_tunnel_display()

    def _update_tunnel_display(self):
        """Update only the tunnel display elements."""
        # Remove old tunnel elements
        if self.tunnel_line:
            self.tunnel_line.remove()
            self.tunnel_line = None

        if self.waypoint_scatter:
            self.waypoint_scatter.remove()
            self.waypoint_scatter = None

        # Remove old patches
        for patch in self.selection_patches:
            patch.remove()
        self.selection_patches = []

        # Redraw tunnel
        self._draw_tunnel()
        self.canvas.draw_idle()

    def _update_selection_display(self):
        """Update only the selection display elements."""
        # Remove old selection elements
        if self.selected_points_scatter:
            self.selected_points_scatter.remove()
            self.selected_points_scatter = None

        # Redraw selection
        self._draw_selection()
        self.canvas.draw_idle()

    def zoom_to_fit(self):
        """Zoom view to fit all content."""
        # Calculate bounds of all content
        all_x = []
        all_y = []

        # Add contour data bounds
        if self.contour_data:
            bounds = self.contour_data.get_bounds()
            all_x.extend([bounds.min_x, bounds.max_x])
            all_y.extend([bounds.min_y, bounds.max_y])

        # Add selected points
        for point in self.visualization_state.selection.selected_points:
            all_x.append(point[0])
            all_y.append(point[1])

        # Add tunnel waypoints
        if self.current_tunnel:
            for wp in self.current_tunnel.path.waypoints:
                all_x.append(wp.x)
                all_y.append(wp.y)

        if all_x and all_y:
            margin = 10
            self.axes.set_xlim(min(all_x) - margin, max(all_x) + margin)
            self.axes.set_ylim(min(all_y) - margin, max(all_y) + margin)
            self.canvas.draw()

    def reset_view(self):
        """Reset view to default."""
        self._setup_axes_style()
        self.canvas.draw()

    def export_view(self, filename: str):
        """Export current view to file."""
        self.figure.savefig(filename, dpi=150, bbox_inches='tight')
        # Status bar removed - no export status message needed

    def set_status(self, message: str):
        """Set status message (status bar removed)."""
        # Status bar removed - method kept for compatibility but does nothing
        pass