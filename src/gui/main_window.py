"""
Main application window for Terrain Tunneling Calculator.

This module provides the main GUI interface that integrates all components
including contour visualization, tunnel planning controls, and menu system.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any
import logging

try:
    import customtkinter as ctk
except ImportError:
    # Fallback to standard tkinter if customtkinter not available
    ctk = None

from models.contour_data import ContourData
from models.tunnel_geometry import TunnelGeometry
from models.visualization_state import VisualizationState, ViewMode, InteractionMode
from services.contour_parser import ContourParser
from services.triangulation import TriangulationService
from services.tunnel_geometry_service import TunnelGeometryService
from gui.contour_view import ContourView
from gui.tunnel_controls import TunnelControls
from gui.analysis_panel import AnalysisPanel
from utils.config import ConfigManager
from services.visualization_3d import Visualization3DService


class MainWindow:
    """Main application window."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize main window.

        Args:
            config_manager: Application configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # Data state
        self.contour_data: Optional[ContourData] = None
        self.current_tunnel: Optional[TunnelGeometry] = None

        # Services
        self.contour_parser = ContourParser()
        self.triangulation_service = TriangulationService()
        self.tunnel_service = TunnelGeometryService()

        # Visualization state
        self.visualization_state = VisualizationState()

        # Initialize GUI
        self._setup_gui()
        self._setup_menu()
        self._setup_status_bar()

        # Load demo data on startup
        self._load_demo_data()

        self.logger.info("Main window initialized successfully")

    def _setup_gui(self):
        """Set up the main GUI layout with high DPI support."""
        if ctk:
            # Use customtkinter if available
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")

            # Enable high DPI awareness for customtkinter
            ctk.set_window_scaling(2.5)  # Scale for 250% DPI

            self.root = ctk.CTk()
            self.root.title("Terrain Tunneling Calculator")

            # Set larger window size for high DPI
            self.root.geometry("2400x1600")  # Scaled up for 250% DPI

            # Configure customtkinter DPI settings
            self.root.grid_columnconfigure(0, weight=1)
            self.root.grid_rowconfigure(0, weight=1)  # Main content gets maximum space
            self.root.grid_rowconfigure(1, weight=0)  # Status bar gets minimum space

            # Create main container with customtkinter
            self.main_container = ctk.CTkFrame(self.root)
            self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

            # Create custom paned window layout
            self._setup_customtkinter_layout()
        else:
            # Fallback to standard tkinter with DPI awareness
            self.root = tk.Tk()
            self.root.title("Terrain Tunneling Calculator")
            self.root.geometry("2400x1600")  # Scaled up for high DPI

            # Enable DPI awareness for standard tkinter
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass

            # Configure grid weights
            self.root.grid_rowconfigure(0, weight=1)  # Main content gets maximum space
            self.root.grid_rowconfigure(1, weight=0)  # Status bar gets minimum space
            self.root.grid_columnconfigure(0, weight=1)

            # Create main paned window with standard tkinter
            self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
            self.main_paned.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

            # Left panel - Tunnel controls
            self.left_frame = ttk.Frame(self.main_paned)
            self.main_paned.add(self.left_frame, weight=1)

            # Right panel - Visualization
            self.right_frame = ttk.Frame(self.main_paned)
            self.main_paned.add(self.right_frame, weight=5)

            # Setup with standard tkinter
            self._setup_standard_tkinter_layout()

    def _setup_customtkinter_layout(self):
        """Setup layout using customtkinter components with draggable splitter."""
        # Create horizontal paned window equivalent using frames
        self.paned_frame = ctk.CTkFrame(self.main_container)
        self.paned_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid for paned frame
        self.paned_frame.grid_columnconfigure(0, weight=1)  # Left panel
        self.paned_frame.grid_columnconfigure(1, weight=0)  # Splitter (fixed width)
        self.paned_frame.grid_columnconfigure(2, weight=5)  # Right panel
        self.paned_frame.grid_rowconfigure(0, weight=1)

        # Left panel - Tunnel controls (using customtkinter)
        self.left_frame = ctk.CTkFrame(self.paned_frame)
        self.left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0))

        # Create draggable splitter
        self._create_draggable_splitter()

        # Right panel - Visualization (using customtkinter)
        self.right_frame = ctk.CTkFrame(self.paned_frame)
        self.right_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0))

        # Initialize splitter state
        self._splitter_dragging = False
        self._splitter_start_x = 0
        self._left_weight_start = 1
        self._right_weight_start = 5

        # Setup panels with customtkinter
        self._setup_ctk_control_panel()
        self._setup_ctk_visualization_panel()

    def _create_draggable_splitter(self):
        """Create a draggable splitter between left and right panels."""
        # Get DPI scaling factor for splitter width
        scale_factor = self._get_scale_factor()
        splitter_width = max(int(6 * scale_factor), 8)  # Min 8px, scaled for DPI

        # Create splitter frame
        self.splitter_frame = ctk.CTkFrame(self.paned_frame, width=splitter_width)
        self.splitter_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Make splitter non-resizable
        self.splitter_frame.grid_propagate(False)

        # Set splitter appearance - matches CustomTkinter theme
        self.splitter_frame.configure(
            fg_color=("gray70", "gray40"),  # Lighter in light mode, darker in dark mode
            corner_radius=0,
            border_width=0
        )

        # Bind mouse events for drag functionality
        self.splitter_frame.bind("<Button-1>", self._on_splitter_press)
        self.splitter_frame.bind("<B1-Motion>", self._on_splitter_drag)
        self.splitter_frame.bind("<ButtonRelease-1>", self._on_splitter_release)
        self.splitter_frame.bind("<Enter>", self._on_splitter_enter)
        self.splitter_frame.bind("<Leave>", self._on_splitter_leave)

        # Add visual indicator - a small groove or highlight line
        indicator_width = max(int(2 * scale_factor), 2)  # Min 2px, scaled for DPI
        self.splitter_indicator = ctk.CTkFrame(self.splitter_frame, width=indicator_width)
        self.splitter_indicator.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relheight=0.4)
        self.splitter_indicator.configure(
            fg_color=("gray50", "gray30"),
            corner_radius=max(int(1 * scale_factor), 1)
        )

        # Store hover state for visual feedback
        self._splitter_hovering = False

        self.logger.debug(f"Created draggable splitter with width: {splitter_width}px (scale: {scale_factor:.2f})")

    def _on_splitter_press(self, event):
        """Handle mouse press on splitter."""
        self._splitter_dragging = True
        self._splitter_start_x = event.x_root

        # Get current column weights
        self._left_weight_start = self.paned_frame.grid_columnconfigure(0, "weight")
        self._right_weight_start = self.paned_frame.grid_columnconfigure(2, "weight")

        # Initialize debounce/throttling variables
        self._last_update_time = 0
        self._update_interval = 16  # ~60 FPS for smooth updates (milliseconds)
        self._last_drag_x = 0

        # Change cursor to indicate dragging
        self.splitter_frame.configure(cursor="sb_h_double_arrow")

        # Focus splitter frame for better event handling
        self.splitter_frame.focus_set()

        self.logger.debug(f"Splitter drag started at x={event.x_root}, left_weight={self._left_weight_start}, right_weight={self._right_weight_start}")

    def _on_splitter_drag(self, event):
        """Handle mouse drag on splitter with improved responsiveness and debouncing."""
        if not self._splitter_dragging:
            return

        try:
            import time

            # Check if enough time has passed since last update (throttling)
            current_time = time.time() * 1000  # Convert to milliseconds
            if current_time - self._last_update_time < self._update_interval:
                return  # Skip this update to improve responsiveness

            # Calculate drag distance (positive = right, negative = left)
            delta_x = event.x_root - self._splitter_start_x

            # Skip tiny movements to improve responsiveness
            if abs(delta_x - self._last_drag_x) < 2:  # Minimum 2 pixel movement
                return

            self._last_drag_x = delta_x
            self._last_update_time = current_time

            # Get the total width of the paned frame
            paned_width = self.paned_frame.winfo_width()
            if paned_width <= 1:  # Frame not yet rendered
                return

            # Use a larger base weight for smoother, more granular control
            base_total_weight = 100  # Larger value for finer granularity

            # Scale the start weights to our base system
            scale_factor = base_total_weight / (self._left_weight_start + self._right_weight_start)
            scaled_left_start = int(self._left_weight_start * scale_factor)
            scaled_right_start = int(self._right_weight_start * scale_factor)

            # Calculate the pixel equivalent of one weight unit
            pixels_per_weight = paned_width / base_total_weight

            # Calculate weight change based on drag distance
            # Positive delta_x = drag right = increase left weight, decrease right weight
            # Negative delta_x = drag left = decrease left weight, increase right weight
            weight_change = delta_x / pixels_per_weight

            # Calculate new weights with reasonable minimum bounds (5% of total each)
            min_weight = max(5, int(base_total_weight * 0.05))  # At least 5% each side

            new_left_weight = max(min_weight, int(scaled_left_start + weight_change))
            new_right_weight = max(min_weight, int(scaled_right_start - weight_change))

            # Ensure we don't exceed the total weight significantly
            total_new_weight = new_left_weight + new_right_weight
            if total_new_weight > base_total_weight * 1.5:  # Allow 50% flexibility
                # Scale back proportionally
                scale_back = base_total_weight / total_new_weight
                new_left_weight = int(new_left_weight * scale_back)
                new_right_weight = int(new_right_weight * scale_back)

            # Apply new weights (tkinter requires integers)
            self.paned_frame.grid_columnconfigure(0, weight=new_left_weight)
            self.paned_frame.grid_columnconfigure(2, weight=new_right_weight)

            # Use update_idletasks() instead of update() to avoid blocking
            self.paned_frame.update_idletasks()

            # Update status bar with current ratio (less frequently)
            total_weight = new_left_weight + new_right_weight
            if total_weight > 0:
                current_ratio = new_left_weight / total_weight
                # Update status every few pixels to avoid spamming
                if int(event.x_root) % 50 == 0:
                    self.status_var.set(f"Splitter: {current_ratio:.0%} left / {1-current_ratio:.0%} right")

            self.logger.debug(f"Splitter drag: delta_x={delta_x:.1f}, new_left_weight={new_left_weight}, new_right_weight={new_right_weight}")

        except Exception as e:
            self.logger.error(f"Error during splitter drag: {e}")
            # Reset dragging state on error
            self._splitter_dragging = False
            if hasattr(self, 'splitter_frame'):
                self.splitter_frame.grab_release()
            self.splitter_frame.configure(cursor="")

    def _on_splitter_release(self, event):
        """Handle mouse release on splitter with proper cleanup."""
        if not self._splitter_dragging:
            return

        try:
            self._splitter_dragging = False

            # Release any grab that might have been set (but we don't use grab_set anymore)
            # Instead, we properly handle focus and cursor

            # Restore cursor properly
            if hasattr(self, 'splitter_frame'):
                if self._splitter_hovering:
                    # If mouse is still hovering, keep the resize cursor
                    self.splitter_frame.configure(cursor="sb_h_double_arrow")
                else:
                    # Otherwise reset to default cursor
                    self.splitter_frame.configure(cursor="")

            # Ensure the main window regains focus properly
            self.root.focus_set()

            # Final layout update to ensure everything is properly positioned
            self.paned_frame.update_idletasks()

            # Log final weights for debugging
            if hasattr(self, 'paned_frame'):
                final_left_weight = self.paned_frame.grid_columnconfigure(0, "weight")
                final_right_weight = self.paned_frame.grid_columnconfigure(2, "weight")

                # Show final ratio in status bar
                final_ratio = final_left_weight / (final_left_weight + final_right_weight)
                self.status_var.set(f"✅ Splitter set: {final_ratio:.0%} left / {1-final_ratio:.0%} right")

                self.logger.debug(f"Splitter drag ended: final_left_weight={final_left_weight:.2f}, final_right_weight={final_right_weight:.2f}")

            # Clean up debounce variables
            if hasattr(self, '_last_update_time'):
                delattr(self, '_last_update_time')
            if hasattr(self, '_last_drag_x'):
                delattr(self, '_last_drag_x')

        except Exception as e:
            self.logger.error(f"Error during splitter release: {e}")
            # Ensure cleanup on error
            self._splitter_dragging = False
            if hasattr(self, 'splitter_frame'):
                try:
                    self.splitter_frame.configure(cursor="")
                except:
                    pass
            # Ensure main window focus
            try:
                self.root.focus_set()
            except:
                pass

    def _on_splitter_enter(self, event):
        """Handle mouse enter on splitter."""
        self._splitter_hovering = True

        # Only change cursor if not currently dragging
        if not self._splitter_dragging:
            self.splitter_frame.configure(cursor="sb_h_double_arrow")

        # Visual feedback - slightly brighter on hover
        if hasattr(self.splitter_frame, 'configure'):
            try:
                self.splitter_frame.configure(fg_color=("gray60", "gray35"))
            except:
                pass  # Ignore if hover color not supported

    def _on_splitter_leave(self, event):
        """Handle mouse leave on splitter."""
        self._splitter_hovering = False

        # Don't change cursor if actively dragging
        if not self._splitter_dragging:
            self.splitter_frame.configure(cursor="")

            # Restore normal color
            if hasattr(self.splitter_frame, 'configure'):
                try:
                    self.splitter_frame.configure(fg_color=("gray70", "gray40"))
                except:
                    pass  # Ignore if color change fails

    def _reset_splitter_position(self):
        """Reset splitter to default position (1:5 ratio)."""
        if hasattr(self, 'paned_frame'):
            self.paned_frame.grid_columnconfigure(0, weight=1)  # Left panel
            self.paned_frame.grid_columnconfigure(2, weight=5)  # Right panel
            self.paned_frame.update_idletasks()
            self.logger.debug("Splitter reset to default position (1:5 ratio)")

    def _get_splitter_position(self):
        """Get current splitter position as a ratio (left_weight / total_weight)."""
        if not hasattr(self, 'paned_frame'):
            return 0.167  # Default ratio (1 out of 6 ≈ 16.7%)

        left_weight = self.paned_frame.grid_columnconfigure(0, "weight")
        right_weight = self.paned_frame.grid_columnconfigure(2, "weight")
        total_weight = left_weight + right_weight

        if total_weight > 0:
            return left_weight / total_weight
        return 0.25

    def _set_splitter_position(self, ratio):
        """Set splitter position based on ratio (0.0 to 1.0)."""
        if not hasattr(self, 'paned_frame') or ratio <= 0 or ratio >= 1:
            return

        # Convert ratio to integer weights (tkinter requires integers)
        total_weight = 40  # Use larger total for more granular control
        left_weight = int(total_weight * ratio)
        right_weight = total_weight - left_weight

        # Ensure minimum weights to prevent collapse
        left_weight = max(5, left_weight)  # Minimum 5
        right_weight = max(5, right_weight)  # Minimum 5

        self.paned_frame.grid_columnconfigure(0, weight=left_weight)
        self.paned_frame.grid_columnconfigure(2, weight=right_weight)
        self.paned_frame.update_idletasks()

        self.logger.debug(f"Splitter set to position: {ratio:.2f} (left: {left_weight}, right: {right_weight})")

    def _adjust_splitter_left(self):
        """Move splitter to the left (decrease left panel size)."""
        current_ratio = self._get_splitter_position()
        new_ratio = max(0.1, current_ratio - 0.05)  # Move 5% left, minimum 10%
        self._set_splitter_position(new_ratio)
        self.status_var.set(f"Splitter moved left: {new_ratio:.0%}")

    def _adjust_splitter_right(self):
        """Move splitter to the right (increase left panel size)."""
        current_ratio = self._get_splitter_position()
        new_ratio = min(0.9, current_ratio + 0.05)  # Move 5% right, maximum 90%
        self._set_splitter_position(new_ratio)
        self.status_var.set(f"Splitter moved right: {new_ratio:.0%}")

    def _setup_standard_tkinter_layout(self):
        """Setup layout using standard tkinter components."""
        # Setup left panel (controls)
        self._setup_control_panel()

        # Setup right panel (visualization)
        self._setup_visualization_panel()

    def _setup_ctk_control_panel(self):
        """Set up the left control panel using customtkinter."""
        # Create notebook equivalent using customtkinter tabview
        self.control_tabview = ctk.CTkTabview(self.left_frame)
        self.control_tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure tabview for consistent width across all tabs
        self.control_tabview.configure(width=400)  # Fixed width for consistency

        # Add tabs - removed "Analysis" tab to save space
        self.control_tabview.add("File")
        self.control_tabview.add("Tunnel")
        self.control_tabview.add("View")

        # Setup each tab with customtkinter components
        self._setup_ctk_file_tab()
        self._setup_ctk_tunnel_tab()
        self._setup_ctk_view_tab()
        # Analysis panel removed, functionality moved to Tools menu
  
  
    def _setup_ctk_file_tab(self):
        """Set up file operations tab using customtkinter with scrolling."""
        file_tab = self.control_tabview.tab("File")

        # Create scrollable frame for file operations
        file_scrollable = ctk.CTkScrollableFrame(file_tab, fg_color="transparent")
        file_scrollable.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure scrollbar
        file_scrollable._scrollbar.configure(width=20)

        # File operations frame
        file_ops_frame = ctk.CTkFrame(file_scrollable)
        file_ops_frame.pack(fill=tk.X, padx=5, pady=5)

        # Title
        ctk.CTkLabel(
            file_ops_frame,
            text="File Operations",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 20))

        # Buttons with larger font and size
        button_config = {
            "font": ctk.CTkFont(size=14),
            "height": 40,
            "corner_radius": 8
        }

        ctk.CTkButton(
            file_ops_frame,
            text="📁 Load Contour File",
            command=self._load_contour_file,
            **button_config
        ).pack(fill=tk.X, pady=5, padx=10)

        ctk.CTkButton(
            file_ops_frame,
            text="💾 Save Project",
            command=self._save_project,
            **button_config
        ).pack(fill=tk.X, pady=5, padx=10)

        ctk.CTkButton(
            file_ops_frame,
            text="📂 Load Project",
            command=self._load_project,
            **button_config
        ).pack(fill=tk.X, pady=5, padx=10)

        # Export section
        ctk.CTkLabel(
            file_ops_frame,
            text="Export Options",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))

        ctk.CTkButton(
            file_ops_frame,
            text="📊 Export 2D Plot",
            command=self._export_2d_plot,
            **button_config
        ).pack(fill=tk.X, pady=5, padx=10)

        ctk.CTkButton(
            file_ops_frame,
            text="🎯 Export 3D View",
            command=self._export_3d_view,
            **button_config
        ).pack(fill=tk.X, pady=5, padx=10)

        ctk.CTkButton(
            file_ops_frame,
            text="📋 Export Tunnel Data",
            command=self._export_tunnel_data,
            **button_config
        ).pack(fill=tk.X, pady=5, padx=10)

        # Demo data
        ctk.CTkButton(
            file_ops_frame,
            text="🎲 Load Demo Data",
            command=self._load_demo_data,
            **button_config
        ).pack(fill=tk.X, pady=(20, 10), padx=10)

    def _setup_ctk_tunnel_tab(self):
        """Set up tunnel planning tab using customtkinter with scrolling."""
        tunnel_tab = self.control_tabview.tab("Tunnel")

        # Create scrollable frame for tunnel controls
        tunnel_scrollable = ctk.CTkScrollableFrame(tunnel_tab, fg_color="transparent")
        tunnel_scrollable.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure scrollbar
        tunnel_scrollable._scrollbar.configure(width=20)

        # Use standard tunnel controls directly in scrollable frame - avoid double scrollbar issue
        # Create tunnel controls (original) - directly in scrollable frame
        self.tunnel_controls = TunnelControls(
            tunnel_scrollable,
            tunnel_service=self.tunnel_service,
            visualization_state=self.visualization_state,
            on_tunnel_created=self._on_tunnel_created,
            on_selection_changed=self._on_selection_changed
        )
        self.tunnel_controls.pack(fill=tk.BOTH, expand=True)

    def _setup_ctk_view_tab(self):
        """Set up view options tab using customtkinter with scrolling - unified layout like File tab."""
        view_tab = self.control_tabview.tab("View")

        # Create scrollable frame for all view options - like File tab
        view_scrollable = ctk.CTkScrollableFrame(view_tab, fg_color="transparent")
        view_scrollable.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure scrollbar
        view_scrollable._scrollbar.configure(width=20)

        # Main view options frame - unified like File operations frame
        view_ops_frame = ctk.CTkFrame(view_scrollable)
        view_ops_frame.pack(fill=tk.X, padx=5, pady=5)

        # Title
        ctk.CTkLabel(
            view_ops_frame,
            text="View & Display Options",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 20))

        # View Mode Section
        mode_section_frame = ctk.CTkFrame(view_ops_frame)
        mode_section_frame.pack(fill=tk.X, pady=(0, 10))

        ctk.CTkLabel(
            mode_section_frame,
            text="👁️ View Mode",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 10))

        self.view_mode_var = tk.StringVar(value="contour_2d")

        # View mode radio buttons with consistent styling
        radio_config = {
            "font": ctk.CTkFont(size=12),
            "text_color": ("gray10", "gray90")
        }

        ctk.CTkRadioButton(
            mode_section_frame, text="2D Contours", variable=self.view_mode_var,
            value="contour_2d", command=self._on_view_mode_changed,
            **radio_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        ctk.CTkRadioButton(
            mode_section_frame, text="2D Tunnel Plan", variable=self.view_mode_var,
            value="tunnel_2d", command=self._on_view_mode_changed,
            **radio_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        ctk.CTkRadioButton(
            mode_section_frame, text="3D Terrain", variable=self.view_mode_var,
            value="terrain_3d", command=self._on_view_mode_changed,
            **radio_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        ctk.CTkRadioButton(
            mode_section_frame, text="3D Tunnel", variable=self.view_mode_var,
            value="tunnel_3d", command=self._on_view_mode_changed,
            **radio_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        # Display Options Section
        display_section_frame = ctk.CTkFrame(view_ops_frame)
        display_section_frame.pack(fill=tk.X, pady=(0, 10))

        ctk.CTkLabel(
            display_section_frame,
            text="⚙️ Display Options",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 10))

        # Checkboxes with consistent styling
        checkbox_config = {
            "font": ctk.CTkFont(size=12),
            "text_color": ("gray10", "gray90")
        }

        self.show_contours_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            display_section_frame, text="📍 Show Contours",
            variable=self.show_contours_var,
            command=self._update_display_options,
            **checkbox_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        self.show_tunnel_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            display_section_frame, text="🚇 Show Tunnel",
            variable=self.show_tunnel_var,
            command=self._update_display_options,
            **checkbox_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        self.show_grid_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            display_section_frame, text="🔲 Show Grid",
            variable=self.show_grid_var,
            command=self._update_display_options,
            **checkbox_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        self.show_labels_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            display_section_frame, text="🏷️ Show Elevation Labels",
            variable=self.show_labels_var,
            command=self._update_display_options,
            **checkbox_config
        ).pack(anchor=tk.W, pady=4, padx=15)

        # View Controls Section
        control_section_frame = ctk.CTkFrame(view_ops_frame)
        control_section_frame.pack(fill=tk.X, pady=(0, 10))

        ctk.CTkLabel(
            control_section_frame,
            text="🎮 View Controls",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 10))

        # Control buttons with consistent styling
        button_config = {
            "font": ctk.CTkFont(size=12),
            "height": 35,
            "corner_radius": 8
        }

        ctk.CTkButton(
            control_section_frame, text="🔍 Zoom to Fit",
            command=self._zoom_to_fit,
            **button_config
        ).pack(fill=tk.X, pady=4, padx=15)

        ctk.CTkButton(
            control_section_frame, text="🔄 Reset View",
            command=self._reset_view,
            **button_config
        ).pack(fill=tk.X, pady=4, padx=15)

    # Analysis tab and statistics display removed - now in status bar for space efficiency

    def _setup_ctk_visualization_panel(self):
        """Set up the right visualization panel using customtkinter."""
        # Create contour view (2D) with DPI scaling
        scale_factor = self._get_scale_factor()
        self.contour_view = ContourView(
            self.right_frame,
            visualization_state=self.visualization_state,
            on_point_selected=self._on_point_selected,
            on_waypoint_selected=self._on_waypoint_selected,
            scale_factor=scale_factor
        )
        self.contour_view.pack(fill=tk.BOTH, expand=True)

        
        # Create 3D visualization panel (initially hidden)
        try:
            from gui.visualization_3d_panel import Visualization3DPanel
            self.visualization_3d_panel = Visualization3DPanel(
                self.right_frame,
                on_scene_update=self._on_3d_scene_update
            )
            # Don't pack initially, will be shown when 3D mode is selected
            self.current_view_widget = self.contour_view
            self.is_3d_mode = False
        except ImportError as e:
            self.logger.warning(f"3D visualization not available: {e}")
            self.visualization_3d_panel = None
            self.current_view_widget = self.contour_view
            self.is_3d_mode = False

        # Set up event handlers
        self._setup_event_handlers()

    def _setup_control_panel(self):
        """Set up the left control panel."""
        # Create notebook for tabbed controls
        self.control_notebook = ttk.Notebook(self.left_frame)
        self.control_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # File operations tab
        self.file_frame = ttk.Frame(self.control_notebook)
        self.control_notebook.add(self.file_frame, text="File")
        self._setup_file_tab()

        # Tunnel planning tab
        self.tunnel_frame = ttk.Frame(self.control_notebook)
        self.control_notebook.add(self.tunnel_frame, text="Tunnel")
        self._setup_tunnel_tab()

        # View options tab
        self.view_frame = ttk.Frame(self.control_notebook)
        self.control_notebook.add(self.view_frame, text="View")
        self._setup_view_tab()

        # Removed Analysis tab - statistics now in status bar

    def _setup_file_tab(self):
        """Set up file operations tab."""
        # File operations frame
        file_ops_frame = ttk.LabelFrame(self.file_frame, text="File Operations", padding="10")
        file_ops_frame.pack(fill=tk.X, padx=5, pady=5)

        # Load contour file button
        ttk.Button(
            file_ops_frame, text="Load Contour File",
            command=self._load_contour_file
        ).pack(fill=tk.X, pady=2)

        # Save project button
        ttk.Button(
            file_ops_frame, text="Save Project",
            command=self._save_project
        ).pack(fill=tk.X, pady=2)

        # Load project button
        ttk.Button(
            file_ops_frame, text="Load Project",
            command=self._load_project
        ).pack(fill=tk.X, pady=2)

        # Export buttons
        ttk.Separator(file_ops_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(file_ops_frame, text="Export:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)

        ttk.Button(
            file_ops_frame, text="Export 2D Plot",
            command=self._export_2d_plot
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            file_ops_frame, text="Export 3D View",
            command=self._export_3d_view
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            file_ops_frame, text="Export Tunnel Data",
            command=self._export_tunnel_data
        ).pack(fill=tk.X, pady=2)

        # Demo data
        ttk.Separator(file_ops_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Button(
            file_ops_frame, text="Load Demo Data",
            command=self._load_demo_data
        ).pack(fill=tk.X, pady=2)

    def _setup_tunnel_tab(self):
        """Set up tunnel planning tab."""
        # Create tunnel controls
        self.tunnel_controls = TunnelControls(
            self.tunnel_frame,
            tunnel_service=self.tunnel_service,
            visualization_state=self.visualization_state,
            on_tunnel_created=self._on_tunnel_created,
            on_selection_changed=self._on_selection_changed
        )
        self.tunnel_controls.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Enable point selection mode by default
        self.tunnel_controls.enable_point_selection_mode()

    def _setup_view_tab(self):
        """Set up view options tab."""
        # View mode
        view_mode_frame = ttk.LabelFrame(self.view_frame, text="View Mode", padding="10")
        view_mode_frame.pack(fill=tk.X, padx=5, pady=5)

        self.view_mode_var = tk.StringVar(value="contour_2d")
        ttk.Radiobutton(
            view_mode_frame, text="2D Contours", variable=self.view_mode_var,
            value="contour_2d", command=self._on_view_mode_changed
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            view_mode_frame, text="2D Tunnel Plan", variable=self.view_mode_var,
            value="tunnel_2d", command=self._on_view_mode_changed
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            view_mode_frame, text="3D Terrain", variable=self.view_mode_var,
            value="terrain_3d", command=self._on_view_mode_changed
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            view_mode_frame, text="3D Tunnel", variable=self.view_mode_var,
            value="tunnel_3d", command=self._on_view_mode_changed
        ).pack(anchor=tk.W)

        # Display options
        display_frame = ttk.LabelFrame(self.view_frame, text="Display Options", padding="10")
        display_frame.pack(fill=tk.X, padx=5, pady=5)

        self.show_contours_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            display_frame, text="Show Contours",
            variable=self.show_contours_var,
            command=self._update_display_options
        ).pack(anchor=tk.W)

        self.show_tunnel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            display_frame, text="Show Tunnel",
            variable=self.show_tunnel_var,
            command=self._update_display_options
        ).pack(anchor=tk.W)

        self.show_grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            display_frame, text="Show Grid",
            variable=self.show_grid_var,
            command=self._update_display_options
        ).pack(anchor=tk.W)

        self.show_labels_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            display_frame, text="Show Elevation Labels",
            variable=self.show_labels_var,
            command=self._update_display_options
        ).pack(anchor=tk.W)

        # View controls
        view_controls_frame = ttk.LabelFrame(self.view_frame, text="View Controls", padding="10")
        view_controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            view_controls_frame, text="Zoom to Fit",
            command=self._zoom_to_fit
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            view_controls_frame, text="Reset View",
            command=self._reset_view
        ).pack(fill=tk.X, pady=2)

  # Analysis tab and statistics display removed - now in status bar for space efficiency

    def _setup_visualization_panel(self):
        """Set up the right visualization panel."""
        # Create contour view (2D) with DPI scaling
        scale_factor = self._get_scale_factor()
        self.contour_view = ContourView(
            self.right_frame,
            visualization_state=self.visualization_state,
            on_point_selected=self._on_point_selected,
            on_waypoint_selected=self._on_waypoint_selected,
            scale_factor=scale_factor
        )
        self.contour_view.pack(fill=tk.BOTH, expand=True)

        
        # Create 3D visualization panel (initially hidden)
        try:
            from gui.visualization_3d_panel import Visualization3DPanel
            self.visualization_3d_panel = Visualization3DPanel(
                self.right_frame,
                on_scene_update=self._on_3d_scene_update
            )
            # Don't pack initially, will be shown when 3D mode is selected
            self.current_view_widget = self.contour_view
            self.is_3d_mode = False
        except ImportError as e:
            self.logger.warning(f"3D visualization not available: {e}")
            self.visualization_3d_panel = None
            self.current_view_widget = self.contour_view
            self.is_3d_mode = False

    def _get_scale_factor(self):
        """Get the system DPI scaling factor for font sizing."""
        if not ctk:
            return 1.0

        try:
            # Method 1: Try to get window scaling from system
            import os
            import platform

            scale_factor = 1.0

            # Get screen dimensions for fallback detection
            screen_width = self.root.winfo_screenwidth()

            if platform.system() == "Windows":
                try:
                    import ctypes
                    # Get Windows display scaling
                    user32 = ctypes.windll.user32
                    user32.SetProcessDPIAware()
                    dpi = user32.GetDpiForWindow(user32.GetActiveWindow())
                    scale_factor = dpi / 96.0
                except:
                    # Fallback to registry check
                    try:
                        import winreg
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Control Panel\Desktop\WindowMetrics") as key:
                            scale_factor = int(winreg.QueryValueEx(key, "AppliedDPI")[0]) / 96.0
                    except:
                        # Final fallback - use screen size detection
                        if screen_width >= 3840:  # 4K or higher
                            scale_factor = 2.0  # Reasonable assumption for 4K
                        elif screen_width >= 2560:  # 2K or higher
                            scale_factor = 1.5
                        else:
                            scale_factor = 1.0
            else:
                # For non-Windows, try to detect from screen dimensions
                if screen_width >= 3840:  # 4K or higher
                    scale_factor = 2.0  # Reasonable assumption for 4K
                elif screen_width >= 2560:  # 2K or higher
                    scale_factor = 1.5

            # Override with known good value for 2.5x scaling
            # This should be made configurable in the future
            if scale_factor < 1.5:
                scale_factor = 2.5  # Force to 2.5 for known 4K scaling case

            print(f"DEBUG: Screen width: {screen_width}, Scale factor: {scale_factor:.2f}")
            return scale_factor

        except Exception as e:
            print(f"DEBUG: DPI detection failed: {e}")
            return 2.5  # Fallback to current setting

    def _setup_menu(self):
        """Set up application menu bar with high DPI support."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Get DPI scaling factor and calculate appropriate font sizes
        if ctk:
            scale_factor = self._get_scale_factor()

            # Calculate scaled font sizes with reasonable limits
            base_main_size = 12
            base_submenu_size = 11

            main_menu_size = min(max(int(base_main_size * scale_factor), 16), 32)  # Min 16, Max 32
            submenu_size = min(max(int(base_submenu_size * scale_factor), 14), 30)   # Min 14, Max 30

            print(f"DEBUG: Menu font sizes - Main: {main_menu_size}, Submenu: {submenu_size}")

            main_menu_font = ("Arial", main_menu_size, "bold")
            submenu_font = ("Arial", submenu_size)
        else:
            main_menu_font = ("Arial", 11, "bold")
            submenu_font = ("Arial", 10)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, font=submenu_font)
        menubar.add_cascade(label="📁 File", menu=file_menu, font=main_menu_font)
        file_menu.add_command(label="📁 Load Contour File...", command=self._load_contour_file, font=submenu_font)
        file_menu.add_command(label="🎲 Load Demo Data", command=self._load_demo_data, font=submenu_font)
        file_menu.add_separator()
        file_menu.add_command(label="💾 Save Project...", command=self._save_project, font=submenu_font)
        file_menu.add_command(label="📂 Load Project...", command=self._load_project, font=submenu_font)
        file_menu.add_separator()
        file_menu.add_command(label="📊 Export 2D Plot...", command=self._export_2d_plot, font=submenu_font)
        file_menu.add_command(label="🎯 Export 3D View...", command=self._export_3d_view, font=submenu_font)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self._on_exit, font=submenu_font)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0, font=submenu_font)
        menubar.add_cascade(label="👁️ View", menu=view_menu, font=main_menu_font)
        view_menu.add_command(label="🔍 Zoom to Fit", command=self._zoom_to_fit, font=submenu_font)
        view_menu.add_command(label="🔄 Reset View", command=self._reset_view, font=submenu_font)
        view_menu.add_separator()
        view_menu.add_command(label="📈 2D Contours", command=lambda: self._set_view_mode("contour_2d"), font=submenu_font)
        view_menu.add_command(label="🛣️ 2D Tunnel Plan", command=lambda: self._set_view_mode("tunnel_2d"), font=submenu_font)
        view_menu.add_command(label="🏔️ 3D Terrain", command=lambda: self._set_view_mode("terrain_3d"), font=submenu_font)
        view_menu.add_command(label="🚇 3D Tunnel", command=lambda: self._set_view_mode("tunnel_3d"), font=submenu_font)

        # Tools menu - moved Analysis functionality here
        tools_menu = tk.Menu(menubar, tearoff=0, font=submenu_font)
        menubar.add_cascade(label="🔧 Tools", menu=tools_menu, font=main_menu_font)
        tools_menu.add_command(label="📏 Calculate Volume", command=self._calculate_volume, font=submenu_font)
        tools_menu.add_command(label="📐 Gradient Analysis", command=self._gradient_analysis, font=submenu_font)
        tools_menu.add_separator()
        tools_menu.add_command(label="🗑️ Clear Tunnel", command=self._clear_tunnel, font=submenu_font)
        tools_menu.add_command(label="❌ Clear Selection", command=self._clear_selection, font=submenu_font)

        # Analysis menu - moved from tab to menu
        analysis_menu = tk.Menu(menubar, tearoff=0, font=submenu_font)
        menubar.add_cascade(label="📊 Analysis", menu=analysis_menu, font=main_menu_font)
        analysis_menu.add_command(label="📈 Cross-section Analysis", command=self._structural_analysis, font=submenu_font)
        analysis_menu.add_command(label="🔍 Geological Analysis", command=self._geological_analysis, font=submenu_font)
        analysis_menu.add_command(label="📋 Detailed Statistics", command=self._show_detailed_statistics, font=submenu_font)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, font=submenu_font)
        menubar.add_cascade(label="❓ Help", menu=help_menu, font=main_menu_font)
        help_menu.add_command(label="ℹ️ About", command=self._show_about, font=submenu_font)
        help_menu.add_command(label="📖 User Guide", command=self._show_user_guide, font=submenu_font)

    def _setup_status_bar(self):
        """Set up minimal status bar at bottom of window - single line display."""
        # Get DPI scaling factor
        scale_factor = self._get_scale_factor()

        if ctk:
            # Use customtkinter for minimal status bar - just one line of text
            self.status_frame = ctk.CTkFrame(self.root, height=16)  # Minimized to 16 pixels - just enough for one line
            self.status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=2, pady=1)

            # Status label - the only thing displayed
            self.status_var = tk.StringVar(value="🟢 Ready")

            # Calculate DPI-scaled font size for customtkinter with moderate scaling
            # Use smaller base size and more conservative scaling for better readability
            status_font_size = max(int(6 * scale_factor), 10)

            self.status_label = ctk.CTkLabel(
                self.status_frame,
                textvariable=self.status_var,
                font=ctk.CTkFont(size=status_font_size),  # DPI-scaled font
                text_color=("gray10", "gray90")
            )
            self.status_label.pack(side=tk.LEFT, padx=8, pady=2)

        else:
            # Fallback to standard tkinter - minimal single line
            self.status_frame = ttk.Frame(self.root, height=16)  # Same minimal height
            self.status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=2, pady=1)

            # Status label - only display
            self.status_var = tk.StringVar(value="Ready")

            # Calculate DPI-scaled font size for standard tkinter with moderate scaling
            # Use smaller base size and more conservative scaling for better readability
            status_font_size = max(int(5 * scale_factor), 9)

            self.status_label = ttk.Label(
                self.status_frame,
                textvariable=self.status_var,
                font=("Arial", status_font_size)  # DPI-scaled font
            )
            self.status_label.pack(side=tk.LEFT, padx=8, pady=2)

    def _setup_event_handlers(self):
        """Set up application event handlers."""
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self._load_contour_file())
        self.root.bind('<Control-s>', lambda e: self._save_project())
        self.root.bind('<Control-l>', lambda e: self._load_project())
        self.root.bind('<Escape>', lambda e: self._clear_selection())
        self.root.bind('<F1>', lambda e: self._show_user_guide())

        # Splitter keyboard shortcuts (only if using customtkinter with splitter)
        if ctk and hasattr(self, 'splitter_frame'):
            self.root.bind('<Control-r>', lambda e: self._reset_splitter_position())
            self.root.bind('<Control-Left>', lambda e: self._adjust_splitter_left())
            self.root.bind('<Control-Right>', lambda e: self._adjust_splitter_right())
            self.root.bind('<Control-0>', lambda e: self._set_splitter_position(0.5))  # Equal split

    
    def _load_contour_file(self):
        """Load contour data from file."""
        filename = filedialog.askopenfilename(
            title="Load Contour File",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                self.status_var.set("Loading contour file...")
                self.root.update()

                self.contour_data = self.contour_parser.parse_file(filename)
                self.contour_view.set_contour_data(self.contour_data)
                # Analysis panel removed - statistics now in status bar
                self.tunnel_controls.set_contour_data(self.contour_data)  # Pass contour data to tunnel controls

                self.status_var.set(f"Loaded contour file: {filename}")
                
                self.logger.info(f"Loaded contour file: {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load contour file:\n{str(e)}")
                self.status_var.set("Error loading file")
                self.logger.error(f"Error loading contour file: {e}")

    def _load_demo_data(self):
        """Load demo contour data."""
        try:
            self.status_var.set("Loading demo data...")
            self.root.update()

            # Generate demo data
            from utils.demo_data import DemoDataGenerator
            demo_generator = DemoDataGenerator()
            self.contour_data = demo_generator.generate_hill_terrain()

            # Update visualization
            self.contour_view.set_contour_data(self.contour_data)
            # Analysis panel removed - statistics now in status bar
            self.tunnel_controls.set_contour_data(self.contour_data)  # CRITICAL: Pass contour data to tunnel controls

            self.status_var.set("🟢 Demo data loaded successfully")
            
            self.logger.info("Demo data loaded successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load demo data:\n{str(e)}")
            self.status_var.set("Error loading demo data")
            self.logger.error(f"Error loading demo data: {e}")

    def _save_project(self):
        """Save current project to file."""
        filename = filedialog.asksaveasfilename(
            title="Save Project",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                # Create project data structure
                project_data = {
                    "contour_data": self.contour_data.to_dict() if self.contour_data else None,
                    "tunnel_geometry": self.current_tunnel.to_dict() if self.current_tunnel else None,
                    "visualization_state": self.visualization_state.to_dict()
                }

                import json
                with open(filename, 'w') as f:
                    json.dump(project_data, f, indent=2, default=str)

                self.status_var.set(f"Project saved: {filename}")
                self.logger.info(f"Project saved to: {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project:\n{str(e)}")
                self.status_var.set("Error saving project")
                self.logger.error(f"Error saving project: {e}")

    def _load_project(self):
        """Load project from file."""
        filename = filedialog.askopenfilename(
            title="Load Project",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    project_data = json.load(f)

                # Load contour data
                if project_data.get("contour_data"):
                    self.contour_data = ContourData.from_dict(project_data["contour_data"])
                    self.contour_view.set_contour_data(self.contour_data)
                    # Analysis panel removed - statistics now in status bar
                    self.tunnel_controls.set_contour_data(self.contour_data)  # Pass contour data to tunnel controls

                # Load tunnel geometry
                if project_data.get("tunnel_geometry"):
                    self.current_tunnel = TunnelGeometry.from_dict(project_data["tunnel_geometry"])
                    self.contour_view.set_tunnel_geometry(self.current_tunnel)
                    # Analysis panel removed - tunnel stats now in status bar
                    self.tunnel_controls.current_tunnel = self.current_tunnel
                    
                # Load visualization state
                if project_data.get("visualization_state"):
                    self.visualization_state = VisualizationState.from_dict(project_data["visualization_state"])

                self.status_var.set(f"Project loaded: {filename}")
                
                self.logger.info(f"Project loaded from: {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load project:\n{str(e)}")
                self.status_var.set("Error loading project")
                self.logger.error(f"Error loading project: {e}")

    def _export_2d_plot(self):
        """Export 2D plot to file."""
        filename = filedialog.asksaveasfilename(
            title="Export 2D Plot",
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("PDF files", "*.pdf"),
                ("SVG files", "*.svg"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                self.contour_view.export_view(filename)
                self.status_var.set(f"2D plot exported: {filename}")
                self.logger.info(f"2D plot exported to: {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to export 2D plot:\n{str(e)}")
                self.logger.error(f"Error exporting 2D plot: {e}")

    def _export_3d_view(self):
        """Export 3D visualization."""
        if not self.contour_data:
            messagebox.showwarning("No Data", "Please load contour data first.")
            return

        filename = filedialog.asksaveasfilename(
            title="Export 3D View",
            defaultextension=".html",
            filetypes=[
                ("HTML files", "*.html"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                self.status_var.set("Generating 3D visualization...")
                self.root.update()

                # Create 3D visualization
                terrain_mesh = self.triangulation_service.triangulate_contours(self.contour_data)

                from services.visualization_3d import Visualization3DService
                viz_3d = Visualization3DService()
                fig_3d = viz_3d.create_terrain_plot(terrain_mesh)

                if self.current_tunnel:
                    # Add tunnel to 3D visualization
                    fig_3d = viz_3d.add_tunnel_to_plot(fig_3d, self.current_tunnel)

                viz_3d.save_plot(fig_3d, filename)

                self.status_var.set(f"3D view exported: {filename}")
                self.logger.info(f"3D view exported to: {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to export 3D view:\n{str(e)}")
                self.status_var.set("Error exporting 3D view")
                self.logger.error(f"Error exporting 3D view: {e}")

    def _export_tunnel_data(self):
        """Export tunnel geometry data."""
        if not self.current_tunnel:
            messagebox.showwarning("No Tunnel", "Please create a tunnel first.")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Tunnel Data",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                tunnel_data = self.tunnel_service.export_tunnel_geometry(self.current_tunnel)

                if filename.endswith('.csv'):
                    # Export as CSV
                    import pandas as pd
                    df = pd.DataFrame(tunnel_data)
                    df.to_csv(filename, index=False)
                else:
                    # Export as JSON
                    import json
                    with open(filename, 'w') as f:
                        json.dump(tunnel_data, f, indent=2, default=str)

                self.status_var.set(f"Tunnel data exported: {filename}")
                self.logger.info(f"Tunnel data exported to: {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to export tunnel data:\n{str(e)}")
                self.status_var.set("Error exporting tunnel data")
                self.logger.error(f"Error exporting tunnel data: {e}")

    def _on_view_mode_changed(self):
        """Handle view mode change."""
        mode = self.view_mode_var.get()
        self._set_view_mode(mode)

    def _set_view_mode(self, mode: str):
        """Set the current view mode."""
        self.view_mode_var.set(mode)

        if mode == "contour_2d":
            self.visualization_state.set_view_mode(ViewMode.CONTOUR_2D)
            self._switch_to_2d_view()
        elif mode == "tunnel_2d":
            self.visualization_state.set_view_mode(ViewMode.TUNNEL_2D)
            self._switch_to_2d_view()
        elif mode == "terrain_3d":
            self.visualization_state.set_view_mode(ViewMode.TERRAIN_3D)
            self._switch_to_3d_view(terrain_only=True)
        elif mode == "tunnel_3d":
            self.visualization_state.set_view_mode(ViewMode.TUNNEL_3D)
            self._switch_to_3d_view(terrain_only=False)

    def _switch_to_2d_view(self):
        """Switch to 2D contour view."""
        if self.is_3d_mode:
            # Hide 3D panel
            if self.visualization_3d_panel:
                self.visualization_3d_panel.pack_forget()
            # Show 2D panel
            self.contour_view.pack(fill=tk.BOTH, expand=True)
            self.current_view_widget = self.contour_view
            self.is_3d_mode = False

        # Update 2D display
        self.contour_view._update_display()

    def _switch_to_3d_view(self, terrain_only: bool = False):
        """Switch to 3D visualization view."""
        if not self.visualization_3d_panel:
            messagebox.showwarning(
                "3D Not Available",
                "3D visualization is not available. Please ensure plotly is installed."
            )
            # Switch back to 2D view
            self.view_mode_var.set("contour_2d")
            self._switch_to_2d_view()
            return

        if not self.is_3d_mode:
            # Hide 2D panel
            self.contour_view.pack_forget()
            # Show 3D panel
            self.visualization_3d_panel.pack(fill=tk.BOTH, expand=True)
            self.current_view_widget = self.visualization_3d_panel
            self.is_3d_mode = True

        # Update 3D visualization
        try:
            if terrain_only:
                self._show_3d_terrain()
            else:
                self._show_3d_tunnel()
        except Exception as e:
            self.logger.error(f"Error creating 3D visualization: {e}")
            messagebox.showerror("3D Error", f"Failed to create 3D visualization: {str(e)}")
            # Switch back to 2D view
            self.view_mode_var.set("contour_2d")
            self._switch_to_2d_view()

    def _show_3d_terrain(self):
        """Show 3D terrain visualization."""
        if not self.contour_data:
            messagebox.showinfo("No Data", "Please load contour data first.")
            return

        try:
            # Debug: Log contour data info
            self.logger.info(f"Creating 3D terrain from contour data: {len(self.contour_data.contours)} contours")
            if self.contour_data.contours:
                elevations = [contour.elevation for contour in self.contour_data.contours]
                self.logger.info(f"Contour elevation range: {min(elevations):.1f} to {max(elevations):.1f} meters")

            # Create terrain mesh
            terrain_mesh = self.triangulation_service.triangulate_contours(self.contour_data)

            # Debug: Log mesh info
            self.logger.info(f"Generated terrain mesh: {terrain_mesh.vertex_count} vertices, {terrain_mesh.triangle_count} triangles")

            # Create 3D visualization
            viz_3d = Visualization3DService()
            fig = viz_3d.create_terrain_plot(terrain_mesh)

            # Update 3D panel
            self.visualization_3d_panel.set_terrain_mesh(terrain_mesh)
            if hasattr(self.visualization_3d_panel, '_update_3d_scene'):
                self.visualization_3d_panel._update_3d_scene()

        except Exception as e:
            raise Exception(f"Failed to create 3D terrain: {str(e)}")

    def _show_3d_tunnel(self):
        """Show 3D tunnel visualization."""
        if not self.contour_data:
            messagebox.showinfo("No Data", "Please load contour data first.")
            return

        if not self.current_tunnel:
            messagebox.showinfo("No Tunnel", "Please create a tunnel first.")
            return

        try:
            # Create terrain mesh
            terrain_mesh = self.triangulation_service.triangulate_contours(self.contour_data)

            # Update 3D panel with terrain and tunnel
            self.visualization_3d_panel.set_terrain_mesh(terrain_mesh)
            self.visualization_3d_panel.set_tunnel_geometry(self.current_tunnel)
            if hasattr(self.visualization_3d_panel, '_update_3d_scene'):
                self.visualization_3d_panel._update_3d_scene()

        except Exception as e:
            raise Exception(f"Failed to create 3D tunnel: {str(e)}")

    def _on_3d_scene_update(self, fig):
        """Handle 3D scene update."""
        pass  # Placeholder for 3D scene updates

    def _on_3d_export_complete(self, filename: str):
        """Handle 3D export completion."""
        self.status_var.set(f"3D visualization exported: {filename}")
        self.logger.info(f"3D visualization exported to: {filename}")

    def _update_display_options(self):
        """Update display options."""
        self.visualization_state.display_options.show_contours = self.show_contours_var.get()
        self.visualization_state.display_options.show_tunnel = self.show_tunnel_var.get()
        self.visualization_state.display_options.show_grid = self.show_grid_var.get()
        self.visualization_state.display_options.show_elevation_labels = self.show_labels_var.get()

        self.contour_view._update_display()

    def _zoom_to_fit(self):
        """Zoom view to fit all content."""
        self.contour_view.zoom_to_fit()

    def _reset_view(self):
        """Reset view to default."""
        self.contour_view.reset_view()

    def _calculate_volume(self):
        """Calculate and display tunnel volume."""
        if not self.current_tunnel:
            messagebox.showwarning("No Tunnel", "Please create a tunnel first.")
            return

        try:
            self.logger.info(f"Calculating volume for tunnel: {self.current_tunnel}")
            stats = self.tunnel_service.calculate_tunnel_statistics(self.current_tunnel)
            self.logger.info(f"Calculated stats: {stats}")

            volume = stats.get('volume', 0)
            surface_area = stats.get('surface_area', 0)
            total_length = stats.get('total_length', 0)

            messagebox.showinfo(
                "Volume Calculation",
                f"Tunnel Volume: {volume:.2f} cubic meters\n"
                f"Surface Area: {surface_area:.2f} square meters\n"
                f"Length: {total_length:.2f} meters"
            )

        except Exception as e:
            self.logger.error(f"Error calculating volume: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to calculate volume:\n{str(e)}")

    def _gradient_analysis(self):
        """Perform gradient analysis."""
        if not self.current_tunnel:
            messagebox.showwarning("No Tunnel", "Please create a tunnel first.")
            return

        try:
            stats = self.tunnel_service.calculate_tunnel_statistics(self.current_tunnel)

            max_gradient = stats.get('max_gradient', 0)
            elevation_change = stats.get('elevation_change', 0)

            gradient_status = "Excellent" if max_gradient < 5 else "Good" if max_gradient < 10 else "Steep"

            messagebox.showinfo(
                "Gradient Analysis",
                f"Maximum Gradient: {max_gradient:.2f}%\n"
                f"Total Elevation Change: {elevation_change:.2f} m\n"
                f"Gradient Rating: {gradient_status}\n\n"
                f"Recommended maximum gradient for tunnels: 10-15%"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze gradient:\n{str(e)}")

    def _structural_analysis(self):
        """Perform structural analysis."""
        if not self.current_tunnel:
            messagebox.showwarning("No Tunnel", "Please create a tunnel first.")
            return

        try:
            # Placeholder for structural analysis
            messagebox.showinfo(
                "Structural Analysis",
                "Structural analysis features coming soon!\n\n"
                "This will include:\n"
                "• Rock mass rating\n"
                "• Support requirements\n"
                "• Stability factors\n"
                "• Recommended support systems"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to perform structural analysis:\n{str(e)}")

    def _clear_tunnel(self):
        """Clear current tunnel."""
        self.current_tunnel = None
        self.contour_view.set_tunnel_geometry(None)
        # Analysis panel removed - tunnel stats now in status bar
        self.tunnel_controls._clear_tunnel()
        self.status_var.set("Tunnel cleared")

    def _clear_selection(self):
        """Clear current selection."""
        self.contour_view.clear_selected_points()
        self.visualization_state.selection.clear_selection()
        self.status_var.set("Selection cleared")

    def _on_tunnel_created(self, tunnel_geometry: TunnelGeometry):
        """Handle tunnel creation."""
        self.current_tunnel = tunnel_geometry
        self.contour_view.set_tunnel_geometry(tunnel_geometry)
        # Analysis panel removed - show creation message in status bar
        self.status_var.set("✅ Tunnel created successfully")
        
    def _on_selection_changed(self, points: list):
        """Handle selection change."""
        self.contour_view.add_selected_points(points)

    def _on_analysis_complete(self, analysis_result):
        """Handle analysis completion."""
        self.status_var.set(f"Analysis completed: {analysis_result.tunnel_id}")
        self.logger.info(f"Analysis completed: {analysis_result.tunnel_id}")

    def _on_point_selected(self, x: float, y: float):
        """Handle point selection from contour view."""
        self.tunnel_controls.add_selected_point(x, y)

    def _on_waypoint_selected(self, waypoint_index: int):
        """Handle waypoint selection."""
        self.status_var.set(f"Selected waypoint {waypoint_index + 1}")

    
    def _show_about(self):
        """Show about dialog."""
        about_text = """Terrain Tunneling Calculator
Version 1.0.0

A comprehensive tool for tunnel planning and analysis
with terrain visualization and volume calculation.

© 2024 - All rights reserved

This software helps engineers and planners design
tunnels through challenging terrain with accurate
volume calculations and gradient analysis."""

        messagebox.showinfo("About", about_text)

    def _show_user_guide(self):
        """Show user guide."""
        guide_text = """User Guide - Quick Start

1. LOAD DATA
   • Click 'Load Demo Data' for quick start
   • Or load your own contour file (JSON format)

2. PLAN TUNNEL
   • Switch to 'Tunnel' tab
   • Click on map to select start/end points
   • Adjust tunnel radius and cross-section
   • Click 'Create Tunnel'

3. ANALYZE
   • Use Tools → Analysis menu for detailed statistics
   • Use volume and gradient analysis tools
   • Export results as needed

4. SAVE/EXPORT
   • Save projects for later use
   • Export 2D plots and 3D visualizations
   • Export tunnel data for further analysis

Keyboard Shortcuts:
• Ctrl+O: Open file
• Ctrl+S: Save project
• Escape: Clear selection
• F1: Show this help

5. SPLITTER CONTROL
   • Drag the gray divider between panels to resize them
   • Ctrl+R: Reset splitter to default position
   • Ctrl+Left/Right: Move splitter in small increments
   • Ctrl+0: Set equal split (50% each)

The splitter supports high DPI scaling and provides smooth
dragging with visual feedback."""

        messagebox.showinfo("User Guide", guide_text)

    def _show_detailed_statistics(self):
        """Show detailed statistics in a popup dialog."""
        if not self.contour_data and not self.current_tunnel:
            messagebox.showinfo("No Data", "Please load contour data and create a tunnel first.")
            return

        try:
            stats_text = "=== DETAILED STATISTICS ===\n\n"

            # Contour Data
            bounds = self.contour_data.get_bounds()
            area = (bounds.max_x - bounds.min_x) * (bounds.max_y - bounds.min_y)
            stats_text += f"TERRAIN AREA: {area:.1f} m²\n"
            stats_text += f"BOUNDS: X({bounds.min_x:.1f}, {bounds.max_x:.1f}) Y({bounds.min_y:.1f}, {bounds.max_y:.1f})\n"
            min_elev, max_elev = self.contour_data.get_elevation_range()
            stats_text += f"ELEVATION RANGE: {min_elev:.1f} - {max_elev:.1f} m\n"
            stats_text += f"CONTOURS: {len(self.contour_data.contours)}\n\n"

            # Tunnel Data
            if self.current_tunnel:
                tunnel_stats = self.tunnel_service.calculate_tunnel_statistics(self.current_tunnel)
                stats_text += "=== TUNNEL DATA ===\n"
                stats_text += f"LENGTH: {tunnel_stats.get('total_length', 0):.2f} m\n"
                stats_text += f"VOLUME: {tunnel_stats.get('volume', 0):.1f} m³\n"
                stats_text += f"MAX GRADIENT: {tunnel_stats.get('max_gradient', 0):.2f}%\n"
                stats_text += f"CROSS-SECTION: {tunnel_stats.get('cross_section_type', 'N/A')}\n"
                stats_text += f"WAYPOINTS: {tunnel_stats.get('waypoint_count', 0)}\n"

            # Show in scrollable dialog with DPI-aware font sizing
            from tkinter import scrolledtext
            dialog = tk.Toplevel(self.root)
            dialog.title("Detailed Statistics")

            # Get scale factor for DPI-aware sizing
            scale_factor = self._get_scale_factor()

            # Scale dialog size and font for high DPI
            dialog_width = int(800 * scale_factor)
            dialog_height = int(600 * scale_factor)
            dialog.geometry(f"{dialog_width}x{dialog_height}")

            # Scale text widget dimensions
            text_width = int(90 * scale_factor)
            text_height = int(30 * scale_factor)

            # Calculate DPI-aware font size
            font_size = min(max(int(11 * scale_factor), 14), 28)  # Min 14, Max 28

            # Scale padding for high DPI
            padx = int(10 * scale_factor)
            pady = int(10 * scale_factor)
            btn_pady = int(5 * scale_factor)

            text_widget = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=text_width, height=text_height)
            text_widget.pack(padx=padx, pady=pady, fill=tk.BOTH, expand=True)
            text_widget.insert(tk.END, stats_text)

            # Configure font after widget is created
            text_widget.config(state='disabled')
            try:
                text_widget.config(font=("Arial", font_size))
            except tk.TclError:
                # If font config fails, it's usually a theme/style issue
                print("DEBUG: Font configuration failed for ScrolledText, using default")
                pass

            # DPI-aware button
            button_font_size = min(max(int(10 * scale_factor), 12), 24)  # Min 12, Max 24

            # Create a frame for the button to apply font styling
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=btn_pady)

            try:
                # Try to create button with font
                close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)

                # Configure button style for larger font
                style = ttk.Style()
                style.configure('Large.TButton', font=("Arial", button_font_size))
                close_btn.configure(style='Large.TButton')

                close_btn.pack()
            except Exception as e:
                # Fallback if font styling fails
                print(f"DEBUG: Button font configuration failed: {e}")
                close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
                close_btn.pack()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to show detailed statistics: {str(e)}")

    def _geological_analysis(self):
        """Show geological analysis placeholder."""
        messagebox.showinfo(
            "Geological Analysis",
            "Geological analysis features coming soon!\n\n"
            "This will include:\n"
            "• Rock mass rating\n"
            "• Support requirements\n"
            "• Stability factors\n"
            "• Recommended support systems"
        )

    def _on_exit(self):
        """Handle application exit."""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.logger.info("Application closed by user")
            self.root.quit()

    def run(self):
        """Start the application main loop."""
        try:
            self.logger.info("Starting main application loop")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")
        finally:
            self.logger.info("Application shutdown complete")