"""
3D Visualization Panel GUI for Terrain Tunneling Calculator.

This module provides a comprehensive 3D visualization interface that integrates
plotly 3D scenes, camera controls, animation controls, and export functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any, List, Tuple, Callable
import logging
import numpy as np
from pathlib import Path
import webbrowser
import tempfile
import threading
import time

try:
    import customtkinter as ctk
except ImportError:
    # Fallback to standard tkinter if customtkinter not available
    ctk = None

try:
    import plotly.graph_objects as go
    from plotly.offline import plot
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    plot = None

from models.terrain_mesh import TerrainMesh
from models.tunnel_geometry import TunnelGeometry
from services.visualization_3d import Visualization3DService
from services.animation import AnimationService
from utils.exceptions import VisualizationError, AnimationError


class Visualization3DPanel(ttk.Frame):
    """Comprehensive 3D visualization panel with plotly integration."""

    def __init__(
        self,
        parent: tk.Widget,
        on_scene_update: Optional[Callable[[go.Figure], None]] = None,
        on_animation_update: Optional[Callable[[List], None]] = None
    ):
        """
        Initialize 3D visualization panel.

        Args:
            parent: Parent widget
            on_scene_update: Callback when 3D scene is updated
            on_animation_update: Callback when animation is updated
        """
        super().__init__(parent)

        self.on_scene_update = on_scene_update
        self.on_animation_update = on_animation_update
        self.logger = logging.getLogger(__name__)

        # Services
        self.viz_service = Visualization3DService()
        self.animation_service = AnimationService()

        # Data state
        self.terrain_mesh: Optional[TerrainMesh] = None
        self.tunnel_geometry: Optional[TunnelGeometry] = None
        self.current_figure: Optional[go.Figure] = None
        self.current_animation: Optional[List] = None

        # Camera control state
        self.camera_position = {'x': 1.5, 'y': 1.5, 'z': 1.5}
        self.camera_center = {'x': 0, 'y': 0, 'z': 0}
        self.zoom_level = 1.0

        
        # Check plotly availability
        if not PLOTLY_AVAILABLE:
            self._show_error("Plotly is required for 3D visualization. Please install plotly>=5.15.0")
            return

        self._create_widgets()
        self._setup_layout()

    def _create_widgets(self):
        """Create all GUI widgets."""
        if ctk:
            self._create_ctk_widgets()
        else:
            self._create_ttk_widgets()

    def _create_ctk_widgets(self):
        """Create CustomTkinter widgets."""
        # Main container with padding
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="3D Visualization",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(pady=(0, 15))

        # Create horizontal paned window for controls and visualization
        self.paned_window = ctk.CTkFrame(self.main_frame)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left panel for controls - make it scrollable with fixed width
        self.controls_scrollable = ctk.CTkScrollableFrame(self.paned_window, fg_color="transparent", width=350)
        self.controls_scrollable.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # Right panel for 3D visualization
        self.viz_frame = ctk.CTkFrame(self.paned_window)
        self.viz_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Create 3D plot display area
        self._create_3d_plot_area()

        # Control panels in scrollable left frame
        self._create_scene_controls_ctk()
        self._create_camera_controls_ctk()
        self._create_animation_controls_ctk()
        self._create_export_controls_ctk()

    def _create_ttk_widgets(self):
        """Create standard tkinter ttk widgets."""
        # Main container with padding
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        self.title_label = ttk.Label(
            self.main_frame,
            text="3D Visualization",
            font=('TkDefaultFont', 14, 'bold')
        )
        self.title_label.pack(pady=(0, 15))

        # Control panels
        self._create_scene_controls_ttk()
        self._create_camera_controls_ttk()
        self._create_animation_controls_ttk()
        self._create_export_controls_ttk()

    def _create_scene_controls_ctk(self):
        """Create scene control panel with CustomTkinter."""
        # Scene Controls Frame
        self.scene_frame = ctk.CTkFrame(self.controls_scrollable)
        self.scene_frame.pack(fill=tk.X, pady=(0, 10))

        # Scene Title
        scene_title = ctk.CTkLabel(
            self.scene_frame,
            text="Scene Controls",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        scene_title.pack(pady=(10, 5))

        # Scene Options
        options_frame = ctk.CTkFrame(self.scene_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Show terrain checkbox
        self.show_terrain_var = tk.BooleanVar(value=True)
        self.show_terrain_check = ctk.CTkCheckBox(
            options_frame,
            text="Show Terrain",
            variable=self.show_terrain_var,
            command=self._on_scene_options_changed
        )
        self.show_terrain_check.pack(anchor=tk.W, padx=5, pady=2)

        # Show tunnel checkbox
        self.show_tunnel_var = tk.BooleanVar(value=True)
        self.show_tunnel_check = ctk.CTkCheckBox(
            options_frame,
            text="Show Tunnel",
            variable=self.show_tunnel_var,
            command=self._on_scene_options_changed
        )
        self.show_tunnel_check.pack(anchor=tk.W, padx=5, pady=2)

        # Show wireframe checkbox
        self.show_wireframe_var = tk.BooleanVar(value=False)
        self.show_wireframe_check = ctk.CTkCheckBox(
            options_frame,
            text="Show Wireframe",
            variable=self.show_wireframe_var,
            command=self._on_scene_options_changed
        )
        self.show_wireframe_check.pack(anchor=tk.W, padx=5, pady=2)

        # Material Style Selection
        material_frame = ctk.CTkFrame(self.scene_frame)
        material_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        material_label = ctk.CTkLabel(material_frame, text="Terrain Style:")
        material_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        self.terrain_style_var = tk.StringVar(value="Earth")
        self.terrain_style_combo = ctk.CTkComboBox(
            material_frame,
            values=["Viridis", "Earth", "Blues", "Greens", "Hot", "Jet"],
            variable=self.terrain_style_var,
            command=self._on_terrain_style_changed
        )
        self.terrain_style_combo.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Update Scene Button
        self.update_scene_btn = ctk.CTkButton(
            self.scene_frame,
            text="Update Scene",
            command=self._update_3d_scene
        )
        self.update_scene_btn.pack(pady=5)

    def _create_camera_controls_ctk(self):
        """Create camera control panel with CustomTkinter."""
        # Camera Controls Frame
        self.camera_frame = ctk.CTkFrame(self.controls_scrollable)
        self.camera_frame.pack(fill=tk.X, pady=(0, 10))

        # Camera Title
        camera_title = ctk.CTkLabel(
            self.camera_frame,
            text="Camera Controls",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        camera_title.pack(pady=(10, 5))

        # Camera Position Controls
        position_frame = ctk.CTkFrame(self.camera_frame)
        position_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        position_label = ctk.CTkLabel(position_frame, text="Camera Position:")
        position_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        # X, Y, Z sliders
        self.camera_x_var = tk.DoubleVar(value=1.5)
        self.camera_y_var = tk.DoubleVar(value=1.5)
        self.camera_z_var = tk.DoubleVar(value=1.5)

        # X Position
        x_frame = ctk.CTkFrame(position_frame)
        x_frame.pack(fill=tk.X, padx=5, pady=2)
        ctk.CTkLabel(x_frame, text="X:", width=30).pack(side=tk.LEFT)
        self.camera_x_slider = ctk.CTkSlider(
            x_frame,
            from_=-5, to=5,
            variable=self.camera_x_var,
            command=lambda v: self._on_camera_position_changed()
        )
        self.camera_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Y Position
        y_frame = ctk.CTkFrame(position_frame)
        y_frame.pack(fill=tk.X, padx=5, pady=2)
        ctk.CTkLabel(y_frame, text="Y:", width=30).pack(side=tk.LEFT)
        self.camera_y_slider = ctk.CTkSlider(
            y_frame,
            from_=-5, to=5,
            variable=self.camera_y_var,
            command=lambda v: self._on_camera_position_changed()
        )
        self.camera_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Z Position
        z_frame = ctk.CTkFrame(position_frame)
        z_frame.pack(fill=tk.X, padx=5, pady=2)
        ctk.CTkLabel(z_frame, text="Z:", width=30).pack(side=tk.LEFT)
        self.camera_z_slider = ctk.CTkSlider(
            z_frame,
            from_=-5, to=5,
            variable=self.camera_z_var,
            command=lambda v: self._on_camera_position_changed()
        )
        self.camera_z_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Zoom Control
        zoom_frame = ctk.CTkFrame(self.camera_frame)
        zoom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        zoom_label = ctk.CTkLabel(zoom_frame, text="Zoom Level:")
        zoom_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_slider = ctk.CTkSlider(
            zoom_frame,
            from_=0.1, to=3.0,
            variable=self.zoom_var,
            command=lambda v: self._on_zoom_changed()
        )
        self.zoom_slider.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Camera Preset Buttons
        preset_frame = ctk.CTkFrame(self.camera_frame)
        preset_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        preset_label = ctk.CTkLabel(preset_frame, text="Camera Presets:")
        preset_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        presets_row = ctk.CTkFrame(preset_frame)
        presets_row.pack(fill=tk.X, padx=5, pady=(0, 5))

        ctk.CTkButton(
            presets_row,
            text="Top View",
            command=lambda: self._set_camera_preset(0, 0, 5),
            width=80
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            presets_row,
            text="Side View",
            command=lambda: self._set_camera_preset(5, 0, 0),
            width=80
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            presets_row,
            text="Isometric",
            command=lambda: self._set_camera_preset(1.5, 1.5, 1.5),
            width=80
        ).pack(side=tk.LEFT, padx=2)

    def _create_animation_controls_ctk(self):
        """Create animation control panel with CustomTkinter."""
        # Animation Controls Frame
        self.animation_frame = ctk.CTkFrame(self.controls_scrollable)
        self.animation_frame.pack(fill=tk.X, pady=(0, 10))

        # Animation Title
        animation_title = ctk.CTkLabel(
            self.animation_frame,
            text="Animation Controls",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        animation_title.pack(pady=(10, 5))

        # Animation Options
        anim_options_frame = ctk.CTkFrame(self.animation_frame)
        anim_options_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Speed Control
        speed_label = ctk.CTkLabel(anim_options_frame, text="Animation Speed:")
        speed_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        self.animation_speed_var = tk.DoubleVar(value=1.0)
        self.animation_speed_slider = ctk.CTkSlider(
            anim_options_frame,
            from_=0.1, to=3.0,
            variable=self.animation_speed_var,
            command=lambda v: self._on_animation_speed_changed()
        )
        self.animation_speed_slider.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Car Speed Control
        car_speed_label = ctk.CTkLabel(anim_options_frame, text="Car Speed (m/s):")
        car_speed_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        self.car_speed_var = tk.DoubleVar(value=10.0)
        self.car_speed_slider = ctk.CTkSlider(
            anim_options_frame,
            from_=1.0, to=50.0,
            variable=self.car_speed_var,
            command=lambda v: self._on_car_speed_changed()
        )
        self.car_speed_slider.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Camera Follow Mode
        self.camera_follow_var = tk.BooleanVar(value=True)
        self.camera_follow_check = ctk.CTkCheckBox(
            anim_options_frame,
            text="Camera Follows Car",
            variable=self.camera_follow_var,
            command=self._on_camera_follow_changed
        )
        self.camera_follow_check.pack(anchor=tk.W, padx=5, pady=5)

        # Create Animation Button
        self.create_animation_btn = ctk.CTkButton(
            self.animation_frame,
            text="Create Animation",
            command=self._create_animation
        )
        self.create_animation_btn.pack(pady=5)

    def _create_export_controls_ctk(self):
        """Create export control panel with CustomTkinter."""
        # Export Controls Frame
        self.export_frame = ctk.CTkFrame(self.controls_scrollable)
        self.export_frame.pack(fill=tk.X, pady=(0, 10))

        # Export Title
        export_title = ctk.CTkLabel(
            self.export_frame,
            text="Export Controls",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        export_title.pack(pady=(10, 5))

        # Export Options
        export_options_frame = ctk.CTkFrame(self.export_frame)
        export_options_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Export Format Selection
        format_label = ctk.CTkLabel(export_options_frame, text="Export Format:")
        format_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        self.export_format_var = tk.StringVar(value="HTML")
        self.export_format_combo = ctk.CTkComboBox(
            export_options_frame,
            values=["HTML", "PNG", "SVG", "PDF"],
            variable=self.export_format_var
        )
        self.export_format_combo.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Export Buttons
        button_frame = ctk.CTkFrame(export_options_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ctk.CTkButton(
            button_frame,
            text="Export Scene",
            command=self._export_scene,
            width=120
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            button_frame,
            text="Export Animation",
            command=self._export_animation,
            width=120
        ).pack(side=tk.LEFT, padx=2)

        # Open in Browser Button
        self.open_browser_btn = ctk.CTkButton(
            self.export_frame,
            text="Open in Browser",
            command=self._open_in_browser
        )
        self.open_browser_btn.pack(pady=5)

    def _create_scene_controls_ttk(self):
        """Create scene control panel with standard tkinter."""
        # Implementation similar to above but using ttk widgets
        pass

    def _create_camera_controls_ttk(self):
        """Create camera control panel with standard tkinter."""
        # Implementation similar to above but using ttk widgets
        pass

    def _create_animation_controls_ttk(self):
        """Create animation control panel with standard tkinter."""
        # Implementation similar to above but using ttk widgets
        pass

    def _create_export_controls_ttk(self):
        """Create export control panel with standard tkinter."""
        # Implementation similar to above but using ttk widgets
        pass

    def _create_3d_plot_area(self):
        """Create the 3D plot display area."""
        # Add title for the plot area
        plot_title = ctk.CTkLabel(
            self.viz_frame,
            text="3D Scene",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        plot_title.pack(pady=(10, 5))

        # Create a frame for the plotly figure
        self.plot_frame = ctk.CTkFrame(self.viz_frame)
        self.plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add a placeholder label initially
        self.placeholder_label = ctk.CTkLabel(
            self.plot_frame,
            text="3D visualization will appear here\nSelect 3D view mode to see terrain and tunnel data",
            justify=tk.CENTER
        )
        self.placeholder_label.pack(expand=True)

    def _setup_layout(self):
        """Setup widget layout."""
        # Layout is already set in the creation methods
        pass

    def _on_scene_options_changed(self):
        """Handle scene options change."""
        self._update_3d_scene()

    def _on_terrain_style_changed(self, selected_style):
        """Handle terrain style change."""
        # Update visualization service style
        self.viz_service.update_style_config({
            'terrain_colorscale': selected_style
        })
        self._update_3d_scene()

    def _on_camera_position_changed(self):
        """Handle camera position change."""
        self.camera_position = {
            'x': self.camera_x_var.get(),
            'y': self.camera_y_var.get(),
            'z': self.camera_z_var.get()
        }
        self._update_camera()

    def _on_zoom_changed(self):
        """Handle zoom change."""
        self.zoom_level = self.zoom_var.get()
        self._update_camera()

    def _on_animation_speed_changed(self):
        """Handle animation speed change."""
        # Update animation service if available
        speed_multiplier = self.animation_speed_var.get()
        self.animation_service.config['speed_multiplier'] = speed_multiplier

    def _on_car_speed_changed(self):
        """Handle car speed change."""
        car_speed = self.car_speed_var.get()
        # Update animation service
        self.animation_service.config['car_speed'] = car_speed

    def _on_camera_follow_changed(self):
        """Handle camera follow mode change."""
        follow_mode = self.camera_follow_var.get()
        # Update animation service
        self.animation_service.config['camera_follow'] = follow_mode

    def _set_camera_preset(self, x: float, y: float, z: float):
        """Set camera to preset position."""
        self.camera_x_var.set(x)
        self.camera_y_var.set(y)
        self.camera_z_var.set(z)
        self._on_camera_position_changed()

    def _update_3d_scene(self):
        """Update the 3D scene visualization."""
        try:
            if not self.terrain_mesh:
                self.logger.warning("No terrain mesh available for 3D scene")
                return

            # Remove placeholder if it exists
            if hasattr(self, 'placeholder_label') and self.placeholder_label:
                self.placeholder_label.pack_forget()

            # Debug: Log terrain mesh info
            self.logger.info(f"Creating 3D scene with terrain mesh: {self.terrain_mesh.vertex_count} vertices, {self.terrain_mesh.triangle_count} triangles")
            if hasattr(self.terrain_mesh, 'vertices') and len(self.terrain_mesh.vertices) > 0:
                min_z = np.min(self.terrain_mesh.vertices[:, 2])
                max_z = np.max(self.terrain_mesh.vertices[:, 2])
                self.logger.info(f"Terrain elevation range: {min_z:.1f} to {max_z:.1f} meters")

            # Create integrated scene with current settings
            fig = self.viz_service.create_integrated_scene(
                terrain_mesh=self.terrain_mesh,
                tunnel_geometry=self.tunnel_geometry,
                title="3D Terrain and Tunnel Visualization"
            )

            # Apply wireframe if requested
            if hasattr(self, 'show_wireframe_var') and self.show_wireframe_var.get():
                # Add wireframe to existing scene
                wireframe_trace = self.viz_service._create_wireframe_trace(
                    self.terrain_mesh.vertices,
                    self.terrain_mesh.triangles
                )
                fig.add_trace(wireframe_trace)

            # Apply camera settings
            fig.update_layout(
                scene=dict(
                    camera=dict(
                        eye=dict(
                            x=self.camera_position['x'] * self.zoom_level,
                            y=self.camera_position['y'] * self.zoom_level,
                            z=self.camera_position['z'] * self.zoom_level
                        ),
                        center=self.camera_center
                    )
                )
            )

            self.current_figure = fig

            # Display the figure in the plot frame
            self._display_plotly_figure(fig)

            # Notify parent of scene update
            if self.on_scene_update:
                self.on_scene_update(fig)

        except Exception as e:
            self._show_error(f"Failed to update 3D scene: {e}")

    def _display_plotly_figure(self, fig):
        """Display a plotly figure in the tkinter frame."""
        try:
            # Clear the plot frame
            for widget in self.plot_frame.winfo_children():
                widget.destroy()

            # Create an HTML file with the plot
            import tempfile
            import webbrowser
            import os

            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                fig.write_html(tmp_file.name, include_plotlyjs='cdn')
                tmp_file_path = tmp_file.name

            # Create a simple web browser view using tkinter's built-in HTML viewer
            # For now, we'll create a simple text display with a button to open in browser
            info_label = ctk.CTkLabel(
                self.plot_frame,
                text="3D Scene Created Successfully!\n\nClick below to open in browser for interactive view",
                justify=tk.CENTER
            )
            info_label.pack(pady=20)

            open_browser_btn = ctk.CTkButton(
                self.plot_frame,
                text="Open 3D View in Browser",
                command=lambda: webbrowser.open(f'file://{tmp_file_path}')
            )
            open_browser_btn.pack(pady=10)

            # Store temp file path for cleanup
            if hasattr(self, 'temp_html_file'):
                try:
                    os.unlink(self.temp_html_file)
                except:
                    pass
            self.temp_html_file = tmp_file_path

        except Exception as e:
            self.logger.error(f"Failed to display plotly figure: {e}")
            # Fallback to simple text display
            error_label = ctk.CTkLabel(
                self.plot_frame,
                text=f"3D scene created but display failed\n\nError: {str(e)}\n\nTry opening in browser",
                justify=tk.CENTER
            )
            error_label.pack(pady=20)

    def _update_camera(self):
        """Update camera position in current figure."""
        if self.current_figure:
            try:
                self.current_figure.update_layout(
                    scene=dict(
                        camera=dict(
                            eye=dict(
                                x=self.camera_position['x'] * self.zoom_level,
                                y=self.camera_position['y'] * self.zoom_level,
                                z=self.camera_position['z'] * self.zoom_level
                            ),
                            center=self.camera_center
                        )
                    )
                )

                # Notify parent of scene update
                if self.on_scene_update:
                    self.on_scene_update(self.current_figure)

            except Exception as e:
                self._show_error(f"Failed to update camera: {e}")

    def _create_animation(self):
        """Create integrated HTML animation and open in browser."""
        try:
            if not self.terrain_mesh or not self.tunnel_geometry:
                messagebox.showwarning(
                    "Animation Error",
                    "Both terrain and tunnel geometry are required for animation."
                )
                return

            # Set busy cursor to indicate processing
            if hasattr(self, 'create_animation_btn'):
                self.create_animation_btn.configure(state='disabled')

            # Set wait cursor for the entire window
            if hasattr(self, 'winfo_toplevel'):
                top_level = self.winfo_toplevel()
                top_level.config(cursor='watch')
                top_level.update_idletasks()

            # Create integrated HTML animation in data directory to avoid git conflicts
            import os
            data_dir = os.path.join(os.getcwd(), 'data', 'animations')
            os.makedirs(data_dir, exist_ok=True)
            animation_filename = f"tunnel_animation_{int(time.time())}.html"
            animation_filepath = os.path.join(data_dir, animation_filename)

            animation_file = self.animation_service.create_integrated_animation_html(
                terrain_mesh=self.terrain_mesh,
                tunnel_geometry=self.tunnel_geometry,
                duration=10.0,  # 10 second animation for better visibility
                filename=animation_filepath
            )

            # Get absolute path
            abs_path = os.path.abspath(animation_file)
            file_url = f"file:///{abs_path.replace(os.sep, '/')}"

            # Open in browser safely in a separate thread to avoid GIL issues
            self._open_browser_safely(file_url)

            # Reset cursor and button
            if hasattr(self, 'winfo_toplevel'):
                top_level = self.winfo_toplevel()
                top_level.config(cursor='')
                top_level.update_idletasks()

            if hasattr(self, 'create_animation_btn'):
                self.create_animation_btn.configure(state='normal')

            messagebox.showinfo("Animation Created",
                f"Integrated animation created successfully!\n\n"
                f"Animation file: {abs_path}\n"
                f"Opened in default browser.\n\n"
                f"Features:\n"
                f"• Integrated animation controls\n"
                f"• Speed adjustment (0.1x - 3.0x)\n"
                f"• Progress bar and frame slider\n"
                f"• Camera preset views (Top, Side, Isometric)\n"
                f"• Real-time 3D interaction\n"
                f"• Responsive design for all devices")

        except Exception as e:
            # Reset cursor and button on error
            if hasattr(self, 'winfo_toplevel'):
                top_level = self.winfo_toplevel()
                top_level.config(cursor='')
                top_level.update_idletasks()

            if hasattr(self, 'create_animation_btn'):
                self.create_animation_btn.configure(state='normal')

            self._show_error(f"Failed to create integrated animation: {e}")

    def _open_browser_safely(self, url: str):
        """
        Safely open browser in a separate thread to avoid GIL issues in Python 3.13.

        Args:
            url: URL to open in browser
        """
        def open_in_thread():
            try:
                # Small delay to ensure GUI is responsive
                time.sleep(0.1)
                webbrowser.open(url)
            except Exception as e:
                # Log error but don't crash the application
                print(f"Failed to open browser: {e}")

        # Start browser opening in a separate thread
        thread = threading.Thread(target=open_in_thread, daemon=True)
        thread.start()

    def _export_scene(self):
        """Export current scene to selected format."""
        if not self.current_figure:
            messagebox.showwarning("Export Error", "No scene to export.")
            return

        try:
            format_type = self.export_format_var.get().lower()
            filename = filedialog.asksaveasfilename(
                title=f"Export Scene as {format_type.upper()}",
                defaultextension=f".{format_type}",
                filetypes=[
                    (f"{format_type.upper()} files", f"*.{format_type}"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                if format_type == "html":
                    html_content = self.viz_service.export_scene_to_html(
                        self.current_figure,
                        include_plotlyjs=True
                    )
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                else:
                    # Use plotly's write_image for other formats
                    self.viz_service.export_scene_to_image(
                        self.current_figure,
                        filename
                    )

                messagebox.showinfo("Success", f"Scene exported to {filename}")

        except Exception as e:
            self._show_error(f"Failed to export scene: {e}")

    def _export_animation(self):
        """Export current animation."""
        if not self.current_figure or not hasattr(self.current_figure, 'frames'):
            messagebox.showwarning("Export Error", "No animation to export.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                title="Export Animation as HTML",
                defaultextension=".html",
                filetypes=[
                    ("HTML files", "*.html"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                # Export animation as HTML
                html_content = self.animation_service.export_animation_html(
                    self.current_figure,
                    filename=filename
                )

                messagebox.showinfo("Success", f"Animation exported to {filename}")

        except Exception as e:
            self._show_error(f"Failed to export animation: {e}")

    def _open_in_browser(self):
        """Open current scene in web browser."""
        if not self.current_figure:
            messagebox.showwarning("Browser Error", "No scene to display.")
            return

        try:
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                html_content = self.viz_service.export_scene_to_html(
                    self.current_figure,
                    include_plotlyjs=True
                )
                tmp_file.write(html_content)
                tmp_file_path = tmp_file.name

            # Open in browser
            webbrowser.open(f'file://{tmp_file_path}')

        except Exception as e:
            self._show_error(f"Failed to open in browser: {e}")

    def _show_error(self, message: str):
        """Show error message to user."""
        self.logger.error(message)
        if ctk:
            messagebox.showerror("Error", message)
        else:
            messagebox.showerror("Error", message)

    # Public API methods
    def set_terrain_mesh(self, terrain_mesh: TerrainMesh):
        """Set terrain mesh for visualization."""
        self.terrain_mesh = terrain_mesh
        self._update_3d_scene()

    def set_tunnel_geometry(self, tunnel_geometry: TunnelGeometry):
        """Set tunnel geometry for visualization."""
        self.tunnel_geometry = tunnel_geometry
        self._update_3d_scene()

    def get_current_figure(self) -> Optional[go.Figure]:
        """Get current plotly figure."""
        return self.current_figure

    def update_camera_position(self, x: float, y: float, z: float):
        """Update camera position programmatically."""
        self.camera_x_var.set(x)
        self.camera_y_var.set(y)
        self.camera_z_var.set(z)
        self._on_camera_position_changed()

    def set_terrain_style(self, style: str):
        """Set terrain visualization style."""
        self.terrain_style_var.set(style)
        self._on_terrain_style_changed(style)

    def reset_view(self):
        """Reset view to default settings."""
        self._set_camera_preset(1.5, 1.5, 1.5)
        self.zoom_var.set(1.0)
        self.terrain_style_var.set("Earth")
        self._update_3d_scene()