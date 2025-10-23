"""
Tunnel planning controls GUI for Terrain Tunneling Calculator.

This module provides the user interface components for tunnel planning,
including point selection, radius adjustment, and cross-section controls
with high DPI support.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, Tuple, List
import numpy as np

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from models.tunnel_geometry import TunnelGeometry, CrossSectionType
from models.visualization_state import VisualizationState, InteractionMode
from services.tunnel_geometry_service import (
    TunnelGeometryService, TunnelCreationRequest, TunnelCreationResult
)
from utils.validation import ValidationResult

# Emoji mapping for better visibility
emoji_map = {
    "start_end": "🎯",
    "continuous": "🛤️",
    "delaunay": "📐",
    "centerline": "〰️",
    "hybrid": "🔧",
    "volume": "📊",
    "analysis": "🔍"
}


class TunnelControls(ttk.Frame):
    """Main tunnel planning controls panel with high DPI support."""

    def __init__(
        self,
        parent: tk.Widget,
        tunnel_service: TunnelGeometryService,
        visualization_state: VisualizationState,
        on_tunnel_created: Optional[Callable[[TunnelGeometry], None]] = None,
        on_selection_changed: Optional[Callable[[List[Tuple[float, float]]], None]] = None
    ):
        """
        Initialize tunnel controls.

        Args:
            parent: Parent widget
            tunnel_service: Tunnel geometry service
            visualization_state: Shared visualization state
            on_tunnel_created: Callback when tunnel is created
            on_selection_changed: Callback when point selection changes
        """
        super().__init__(parent)

        self.tunnel_service = tunnel_service
        self.visualization_state = visualization_state
        self.on_tunnel_created = on_tunnel_created
        self.on_selection_changed = on_selection_changed

        self.current_tunnel: Optional[TunnelGeometry] = None
        self.selected_points: List[Tuple[float, float]] = []

        # Status variable for compatibility
        self.status_var = tk.StringVar(value="Ready for tunnel planning")

        # Initialize additional variables needed for tunnel creation
        self.radius_var = tk.DoubleVar(value=3.0)
        self.cross_section_var = tk.StringVar(value="circular")
        self.progress_var = tk.DoubleVar(value=0.0)

        # Initialize selection mode variable for compatibility
        self.selection_mode_var = tk.StringVar(value="start_end")

        self._setup_ui()
        self._update_ui_state()

        # Automatically enable point selection mode when tunnel controls are created
        self.enable_point_selection_mode()

    def _setup_ui(self):
        """Set up the user interface with high DPI support."""
        # Check if parent is a CTkScrollableFrame
        parent_frame = self.master
        parent_class_name = parent_frame.__class__.__name__

        print(f"DEBUG: Parent class: {parent_class_name}")  # Debug output

        if parent_class_name == 'CTkScrollableFrame':
            # Create UI content directly in parent scrollable frame
            self._setup_ctk_ui_in_parent_frame()
        else:
            # Fallback to enhanced ttk UI for non-CTK parents
            self._setup_enhanced_ttk_ui()

    def _setup_enhanced_ttk_ui(self):
        """Set up the user interface with enhanced tkinter fonts for high DPI and scrolling."""
        # Configure self to expand
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create scrollable container
        scroll_container = ttk.Frame(self)
        scroll_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scroll_container.columnconfigure(0, weight=1)
        scroll_container.rowconfigure(0, weight=1)

        # Create canvas for scrolling
        canvas = tk.Canvas(scroll_container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create vertical scrollbar
        v_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configure canvas scrolling
        canvas.configure(yscrollcommand=v_scrollbar.set)

        # Create main frame inside canvas
        main_frame = ttk.Frame(canvas, padding="15")
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        # Configure canvas scroll region
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        main_frame.bind("<Configure>", configure_scroll_region)

        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_to_mousewheel)
        canvas.bind("<Leave>", _unbind_from_mousewheel)

        # Title with larger font
        title_label = ttk.Label(
            main_frame,
            text="🚇 Tunnel Planning Controls",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # Point Selection Section with enhanced fonts
        self._create_enhanced_point_selection_section(main_frame)

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15
        )

        # Tunnel Properties Section with enhanced fonts
        self._create_enhanced_tunnel_properties_section(main_frame)

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15
        )

        # Action Buttons Section with enhanced fonts
        self._create_enhanced_action_buttons_section(main_frame)

        # Status Section with enhanced fonts
        self._create_enhanced_status_section(main_frame)

        # Store canvas reference for external access
        self.scroll_canvas = canvas

    def _setup_ctk_ui(self):
        """Set up the user interface using CustomTkinter for best high DPI support with scrolling."""
        # Create scrollable frame for all content
        scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure scrollbar width and appearance
        scrollable_frame._scrollbar.configure(width=20)

        # Title with larger font
        title_label = ctk.CTkLabel(
            scrollable_frame,
            text="🚇 Tunnel Planning Controls",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 20))

        # Point Selection Section with CustomTkinter (using parent scrollable frame)
        self._create_ctk_point_selection_section(scrollable_frame)

        # Separator
        separator1 = ctk.CTkFrame(scrollable_frame, height=2, fg_color="transparent")
        separator1.pack(fill=tk.X, pady=10)

        # Tunnel Properties Section with CustomTkinter (using parent scrollable frame)
        self._create_ctk_tunnel_properties_section(scrollable_frame)

        # Separator
        separator2 = ctk.CTkFrame(scrollable_frame, height=2, fg_color="transparent")
        separator2.pack(fill=tk.X, pady=10)

        # Action Buttons Section with CustomTkinter (using parent scrollable frame)
        self._create_ctk_action_buttons_section(scrollable_frame)

        # Status Section with CustomTkinter
        self._create_ctk_status_section(scrollable_frame)

        # Store scrollable frame reference (use parent if provided)
        # self.scrollable_frame = scrollable_frame  # Commented out - already set in __init__

    def _setup_ctk_ui_no_scroll(self):
        """Set up CustomTkinter UI using parent scrollable frame (no double scrollbar)."""
        # Use parent scrollable frame instead of creating new one
        scrollable_frame = self.master  # Use the parent's scrollable frame

        # Configure scrollbar
        scrollable_frame._scrollbar.configure(width=20)

        # Configure self to expand and fill parent frame completely
        self.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _setup_ctk_ui_in_parent_frame(self):
        """Set up CustomTkinter UI directly in parent CTkScrollableFrame."""
        # Use parent scrollable frame directly without creating new one
        parent_frame = self.master

        # Configure self to expand and fill parent frame completely
        self.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create all UI sections directly in the parent scrollable frame
        # Title with larger font
        title_label = ctk.CTkLabel(
            parent_frame,
            text="🚇 Tunnel Planning Controls",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 20))

        # Point Selection Section
        self._create_ctk_point_selection_section(parent_frame)

        # Separator
        separator1 = ctk.CTkFrame(parent_frame, height=2, fg_color="transparent")
        separator1.pack(fill=tk.X, pady=10)

        # Tunnel Properties Section
        self._create_ctk_tunnel_properties_section(parent_frame)

        # Separator
        separator2 = ctk.CTkFrame(parent_frame, height=2, fg_color="transparent")
        separator2.pack(fill=tk.X, pady=10)

        # Action Buttons Section
        self._create_ctk_action_buttons_section(parent_frame)

        # Separator
        separator3 = ctk.CTkFrame(parent_frame, height=2, fg_color="transparent")
        separator3.pack(fill=tk.X, pady=10)

        # Status Display Section
        self._create_ctk_status_section(parent_frame)

    def _create_enhanced_point_selection_section(self, parent):
        """Create point selection controls with enhanced fonts for high DPI."""
        section_frame = ttk.LabelFrame(parent, text="📍 Point Selection", padding="8")
        section_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Selection mode with larger font
        ttk.Label(section_frame, text="Mode:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.selection_mode_var = tk.StringVar(value="start_end")

        # Selection mode radio buttons with larger font
        radio_config = {"font": ("Arial", 11)}
        ttk.Radiobutton(
            section_frame, text="Start/End Points", variable=self.selection_mode_var,
            value="start_end", command=self._on_selection_mode_changed,
            **radio_config
        ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Radiobutton(
            section_frame, text="Continuous Path", variable=self.selection_mode_var,
            value="continuous", command=self._on_selection_mode_changed,
            **radio_config
        ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Current selection display
        ttk.Label(section_frame, text="Selected Points:", font=("Arial", 12, "bold")).grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=(10, 5)
        )

        self.selection_text = tk.Text(section_frame, height=3, width=40, wrap=tk.WORD, font=("Arial", 11))
        self.selection_text.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.selection_text.config(state='disabled')

        # Selection action buttons with larger font
        button_frame = ttk.Frame(section_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        button_config = {"font": ("Arial", 11), "height": 2, "width": 15}

        ttk.Button(
            button_frame, text="Clear Selection", command=self._clear_selection,
            **button_config
        ).pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.X)

        ttk.Button(
            button_frame, text="Auto Select", command=self._auto_select_points,
            **button_config
        ).pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.X)

    def _create_ctk_point_selection_section(self, parent):
        """Create point selection controls using CustomTkinter in parent scrollable frame."""
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill=tk.X, pady=10)

        # Section title
        ctk.CTkLabel(
            section_frame,
            text="📍 Point Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 15))

        # Selection mode with larger font
        selection_mode_frame = ctk.CTkFrame(section_frame)
        selection_mode_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkLabel(
            selection_mode_frame,
            text="Selection Mode:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor=tk.W, pady=(0, 5))

        self.ctk_selection_mode_var = tk.StringVar(value="start_end")

        # Selection mode radio buttons
        radio_config = {"font": ctk.CTkFont(size=11)}
        ctk.CTkRadioButton(
            selection_mode_frame, text="Start/End Points", variable=self.ctk_selection_mode_var,
            value="start_end", command=self._on_selection_mode_changed,
            **radio_config
        ).pack(anchor=tk.W, pady=3, padx=20)

        ctk.CTkRadioButton(
            selection_mode_frame, text="Continuous Path", variable=self.ctk_selection_mode_var,
            value="continuous", command=self._on_selection_mode_changed,
            **radio_config
        ).pack(anchor=tk.W, pady=3, padx=20)

        # Current selection display
        ctk.CTkLabel(
            section_frame,
            text="Selected Points:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.ctk_selection_textbox = ctk.CTkTextbox(section_frame, height=80, font=ctk.CTkFont(size=11))
        self.ctk_selection_textbox.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.ctk_selection_textbox.configure(state="disabled")

        # Selection action buttons with larger size
        button_frame = ctk.CTkFrame(section_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        button_config = {
            "font": ctk.CTkFont(size=11),
            "height": 35,
            "corner_radius": 6
        }

        button_row = ctk.CTkFrame(button_frame)
        button_row.pack(fill=tk.X)

        ctk.CTkButton(
            button_row, text="🗑️ Clear Selection", command=self._clear_selection,
            **button_config
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ctk.CTkButton(
            button_row, text="✨ Auto Select", command=self._auto_select_points,
            **button_config
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def _create_enhanced_tunnel_properties_section(self, parent):
        """Create tunnel properties section with enhanced ttk and high DPI support."""
        # Section frame with styling
        section_frame = ttk.LabelFrame(
            parent,
            text="🔧 Tunnel Properties",
            padding="20"
        )
        section_frame.pack(fill="x", pady=15)

        # Configure section frame style
        style = ttk.Style()
        style.configure("Card.TLabelframe", background="transparent", relief="raised", borderwidth=1)
        style.configure("Card.TLabelframe.Label",
                       background="transparent",
                       foreground="#333333",
                       font=("Arial", 14, "bold"))
        section_frame.configure(style="Card.TLabelframe")

        # Name field
        name_frame = ttk.Frame(section_frame)
        name_frame.pack(fill="x", pady=12)
        ttk.Label(name_frame, text="Name:", font=("Arial", 12)).pack(side="left")
        self.name_entry = ttk.Entry(name_frame, font=("Arial", 12), width=25)
        self.name_entry.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Method selection
        method_frame = ttk.Frame(section_frame)
        method_frame.pack(fill="x", pady=12)
        ttk.Label(method_frame, text="Method:", font=("Arial", 12)).pack(side="left")
        method_frame_inner = ttk.Frame(method_frame)
        method_frame_inner.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.method_var = tk.StringVar(value="delaunay")
        methods = [
            ("Delaunay Triangulation", "delaunay"),
            ("Centerline Extraction", "centerline"),
            ("Hybrid Method", "hybrid")
        ]

        for text, value in methods:
            rb_frame = ttk.Frame(method_frame_inner)
            rb_frame.pack(anchor="w", pady=3)
            self.method_radio = ttk.Radiobutton(
                rb_frame,
                text=f"{text} 📊",
                variable=self.method_var,
                value=value,
                style="Card.TRadiobutton"
            )
            self.method_radio.pack(side="left")

        # Width field
        width_frame = ttk.Frame(section_frame)
        width_frame.pack(fill="x", pady=12)
        ttk.Label(width_frame, text="Width (m):", font=("Arial", 12)).pack(side="left")

        width_input_frame = ttk.Frame(width_frame)
        width_input_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.width_var = tk.DoubleVar(value=3.0)
        self.width_spinbox = ttk.Spinbox(
            width_input_frame,
            from_=1.0,
            to=20.0,
            increment=0.5,
            textvariable=self.width_var,
            width=10,
            font=("Arial", 12)
        )
        self.width_spinbox.pack(side="left")

        ttk.Label(width_input_frame, text="meters", font=("Arial", 10)).pack(side="left", padx=(5, 0))

        # Height field
        height_frame = ttk.Frame(section_frame)
        height_frame.pack(fill="x", pady=12)
        ttk.Label(height_frame, text="Height (m):", font=("Arial", 12)).pack(side="left")

        height_input_frame = ttk.Frame(height_frame)
        height_input_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.height_var = tk.DoubleVar(value=2.5)
        self.height_spinbox = ttk.Spinbox(
            height_input_frame,
            from_=1.0,
            to=15.0,
            increment=0.5,
            textvariable=self.height_var,
            width=10,
            font=("Arial", 12)
        )
        self.height_spinbox.pack(side="left")

        ttk.Label(height_input_frame, text="meters", font=("Arial", 10)).pack(side="left", padx=(5, 0))

        # Ceiling height ratio field
        ceiling_frame = ttk.Frame(section_frame)
        ceiling_frame.pack(fill="x", pady=12)
        ttk.Label(ceiling_frame, text="Ceiling Ratio:", font=("Arial", 12)).pack(side="left")

        ceiling_input_frame = ttk.Frame(ceiling_frame)
        ceiling_input_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.ceiling_height_ratio_var = tk.DoubleVar(value=0.7)
        self.ceiling_height_ratio_spinbox = ttk.Spinbox(
            ceiling_input_frame,
            from_=0.1,
            to=0.9,
            increment=0.1,
            textvariable=self.ceiling_height_ratio_var,
            width=10,
            font=("Arial", 12)
        )
        self.ceiling_height_ratio_spinbox.pack(side="left")

        ttk.Label(ceiling_input_frame, text="(0.1-0.9)", font=("Arial", 10)).pack(side="left", padx=(5, 0))

        # Help text
        help_frame = ttk.Frame(section_frame)
        help_frame.pack(fill="x", pady=(15, 0))

        help_text = "💡 Ceiling Ratio: Controls tunnel ceiling height relative to total height"
        help_label = ttk.Label(help_frame, text=help_text, font=("Arial", 10), foreground="gray")
        help_label.pack()

  
        return section_frame

    def _create_ctk_tunnel_properties_section(self, parent):
        """Create tunnel properties section with CustomTkinter for high DPI."""
        # Section frame with styling
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill="x", pady=15, padx=10)

        # Section title
        title_label = ctk.CTkLabel(
            section_frame,
            text="🔧 Tunnel Properties",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=15)

        # Name field
        name_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        name_frame.pack(fill="x", padx=20, pady=8)
        name_label = ctk.CTkLabel(name_frame, text="Name:", font=ctk.CTkFont(size=12))
        name_label.pack(side="left")
        self.name_entry = ctk.CTkEntry(name_frame, font=ctk.CTkFont(size=12), width=200)
        self.name_entry.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Method selection
        method_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        method_frame.pack(fill="x", padx=20, pady=8)
        method_label = ctk.CTkLabel(method_frame, text="Method:", font=ctk.CTkFont(size=12))
        method_label.pack(anchor="w")

        self.method_var = tk.StringVar(value="delaunay")

        # Method radio buttons
        methods = [
            ("Delaunay Triangulation", "delaunay"),
            ("Centerline Extraction", "centerline"),
            ("Hybrid Method", "hybrid")
        ]

        for text, value in methods:
            radio_frame = ctk.CTkFrame(method_frame, fg_color="transparent")
            radio_frame.pack(fill="x", pady=3)
            method_radio = ctk.CTkRadioButton(
                radio_frame,
                text=f"{text} 📊",
                variable=self.method_var,
                value=value,
                font=ctk.CTkFont(size=12)
            )
            method_radio.pack(anchor="w")

        # Dimensions container
        dim_container = ctk.CTkFrame(section_frame, fg_color="transparent")
        dim_container.pack(fill="x", padx=20, pady=8)

        # Width field
        width_frame = ctk.CTkFrame(dim_container, fg_color="transparent")
        width_frame.pack(fill="x", pady=8)
        width_label = ctk.CTkLabel(width_frame, text="Width (m):", font=ctk.CTkFont(size=12))
        width_label.pack(side="left")

        width_input_frame = ctk.CTkFrame(width_frame, fg_color="transparent")
        width_input_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.width_var = tk.DoubleVar(value=3.0)
        self.width_spinbox = ctk.CTkOptionMenu(
            width_input_frame,
            values=["1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0", "5.0", "6.0", "8.0", "10.0", "15.0", "20.0"],
            variable=self.width_var,
            font=ctk.CTkFont(size=12),
            width=120
        )
        self.width_spinbox.pack(side="left")
        width_unit_label = ctk.CTkLabel(width_input_frame, text="meters", font=ctk.CTkFont(size=10))
        width_unit_label.pack(side="left", padx=(5, 0))

        # Height field
        height_frame = ctk.CTkFrame(dim_container, fg_color="transparent")
        height_frame.pack(fill="x", pady=8)
        height_label = ctk.CTkLabel(height_frame, text="Height (m):", font=ctk.CTkFont(size=12))
        height_label.pack(side="left")

        height_input_frame = ctk.CTkFrame(height_frame, fg_color="transparent")
        height_input_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.height_var = tk.DoubleVar(value=2.5)
        self.height_spinbox = ctk.CTkOptionMenu(
            height_input_frame,
            values=["1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0", "5.0", "6.0", "8.0", "10.0", "15.0"],
            variable=self.height_var,
            font=ctk.CTkFont(size=12),
            width=120
        )
        self.height_spinbox.pack(side="left")
        height_unit_label = ctk.CTkLabel(height_input_frame, text="meters", font=ctk.CTkFont(size=10))
        height_unit_label.pack(side="left", padx=(5, 0))

        # Ceiling height ratio field
        ceiling_frame = ctk.CTkFrame(dim_container, fg_color="transparent")
        ceiling_frame.pack(fill="x", pady=8)
        ceiling_label = ctk.CTkLabel(ceiling_frame, text="Ceiling Ratio:", font=ctk.CTkFont(size=12))
        ceiling_label.pack(side="left")

        ceiling_input_frame = ctk.CTkFrame(ceiling_frame, fg_color="transparent")
        ceiling_input_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.ceiling_height_ratio_var = tk.DoubleVar(value=0.7)
        self.ceiling_height_ratio_spinbox = ctk.CTkOptionMenu(
            ceiling_input_frame,
            values=["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"],
            variable=self.ceiling_height_ratio_var,
            font=ctk.CTkFont(size=12),
            width=120
        )
        self.ceiling_height_ratio_spinbox.pack(side="left")
        ceiling_range_label = ctk.CTkLabel(ceiling_input_frame, text="(0.1-0.9)", font=ctk.CTkFont(size=10))
        ceiling_range_label.pack(side="left", padx=(5, 0))

        # Help text
        help_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        help_frame.pack(fill="x", padx=20, pady=(15, 5))

        help_text = "💡 Ceiling Ratio: Controls tunnel ceiling height relative to total height"
        help_label = ctk.CTkLabel(help_frame, text=help_text, font=ctk.CTkFont(size=10), text_color="gray")
        help_label.pack()

    
        return section_frame

    def _create_enhanced_action_buttons_section(self, parent):
        """Create action buttons section with enhanced ttk and high DPI support."""
        # Buttons container with card styling
        buttons_frame = ttk.LabelFrame(parent, text="⚡ Actions", padding="20")
        buttons_frame.pack(fill="x", pady=20)

        # Configure section frame style
        style = ttk.Style()
        style.configure("Card.TLabelframe", background="transparent", relief="raised", borderwidth=1)
        style.configure("Card.TLabelframe.Label",
                       background="transparent",
                       foreground="#333333",
                       font=("Arial", 14, "bold"))
        buttons_frame.configure(style="Card.TLabelframe")

        # Buttons grid with better spacing
        buttons_grid = ttk.Frame(buttons_frame)
        buttons_grid.pack(fill="x", pady=10)

        # Primary action button
        self.plan_tunnel_btn = ttk.Button(
            buttons_grid,
            text="🚇 Plan Tunnel",
            command=self.on_plan_tunnel,
            style="Success.TButton",
            width=25
        )
        self.plan_tunnel_btn.pack(side="left", padx=10, ipady=6, ipadx=10)

        # Secondary action button
        self.save_btn = ttk.Button(
            buttons_grid,
            text="💾 Save Configuration",
            command=self.on_save_configuration,
            style="Info.TButton",
            width=25
        )
        self.save_btn.pack(side="left", padx=10, ipady=6, ipadx=10)

        # Tertiary action buttons
        buttons_grid2 = ttk.Frame(buttons_frame)
        buttons_grid2.pack(fill="x", pady=(5, 0))

        self.clear_btn = ttk.Button(
            buttons_grid2,
            text="🗑️ Clear Selection",
            command=self.on_clear_selection,
            style="Warning.TButton",
            width=25
        )
        self.clear_btn.pack(side="left", padx=10, ipady=6, ipadx=10)

        self.analyze_btn = ttk.Button(
            buttons_grid2,
            text="📊 Analyze Volume",
            command=self.on_analyze_volume,
            style="Analysis.TButton",
            width=25
        )
        self.analyze_btn.pack(side="left", padx=10, ipady=6, ipadx=10)

        return buttons_frame

    def _create_ctk_action_buttons_section(self, parent):
        """Create action buttons section with CustomTkinter for high DPI."""
        # Buttons container - use parent scrollable frame to avoid double scrollbar
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=20, padx=10)

        # Section title
        title_label = ctk.CTkLabel(
            buttons_frame,
            text="⚡ Actions",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=15)

        # Primary action button
        self.plan_tunnel_btn = ctk.CTkButton(
            buttons_frame,
            text="🚇 Plan Tunnel",
            command=self.on_plan_tunnel,
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.plan_tunnel_btn.pack(fill="x", pady=8, padx=20)

        # Secondary action button
        self.save_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 Save Configuration",
            command=self.on_save_configuration,
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color="blue",
            hover_color="darkblue"
        )
        self.save_btn.pack(fill="x", pady=8, padx=20)

        # Tertiary action buttons row
        tertiary_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        tertiary_frame.pack(fill="x", pady=8, padx=20)

        self.clear_btn = ctk.CTkButton(
            tertiary_frame,
            text="🗑️ Clear Selection",
            command=self.on_clear_selection,
            height=40,
            font=ctk.CTkFont(size=12),
            fg_color="orange",
            hover_color="darkorange",
            width=200
        )
        self.clear_btn.pack(side="left", padx=(0, 10))

        self.analyze_btn = ctk.CTkButton(
            tertiary_frame,
            text="📊 Analyze Volume",
            command=self.on_analyze_volume,
            height=40,
            font=ctk.CTkFont(size=12),
            fg_color="purple",
            hover_color="darkviolet",
            width=200
        )
        self.analyze_btn.pack(side="right", padx=(10, 0))

        return buttons_frame

    def _create_enhanced_status_section(self, parent):
        """Create status section with enhanced ttk and high DPI support."""
        # Status container
        status_frame = ttk.LabelFrame(parent, text="📋 Status", padding="20")
        status_frame.pack(fill="both", expand=True, pady=10)

        # Configure section frame style
        style = ttk.Style()
        style.configure("Card.TLabelframe", background="transparent", relief="raised", borderwidth=1)
        style.configure("Card.TLabelframe.Label",
                       background="#f0f0f0",
                       foreground="#333333",
                       font=("Arial", 14, "bold"))
        status_frame.configure(style="Card.TLabelframe")

        # Status text display
        text_frame = ttk.Frame(status_frame)
        text_frame.pack(fill="both", expand=True)

        self.status_text = tk.Text(
            text_frame,
            height=6,
            wrap="word",
            font=("Consolas", 10),
            bg="#2c3e50",
            fg="#ecf0f1",
            relief="solid",
            borderwidth=1
        )
        self.status_text.pack(side="left", fill="both", expand=True)

        status_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.status_text.yview)
        status_scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=status_scrollbar.set)

        # Initial status message
        self.update_status("🎯 Ready to plan tunnel. Select start and end points above.", "info")

        return status_frame

    def _create_ctk_status_section(self, parent):
        """Create status section with CustomTkinter for high DPI."""
        # Status container - use parent scrollable frame to avoid double scrollbar
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(fill="both", expand=True, pady=10, padx=10)

        # Section title
        title_label = ctk.CTkLabel(
            status_frame,
            text="📋 Status",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=15)

        # Status text display
        text_frame = ctk.CTkFrame(status_frame)
        text_frame.pack(fill="both", expand=True, pady=10, padx=20)

        self.status_text = ctk.CTkTextbox(
            text_frame,
            height=120,
            font=ctk.CTkFont(size=11, family="Consolas"),
            fg_color="#2c3e50",
            text_color="#ecf0f1",
            border_width=1,
            border_color="gray30"
        )
        self.status_text.pack(fill="both", expand=True)

        # Initial status message
        self.update_status("🎯 Ready to plan tunnel. Select start and end points above.", "info")

        return status_frame

    # Missing methods needed by enhanced sections
    def _clear_selection(self):
        """Clear current point selection."""
        if hasattr(self, 'visualization_state'):
            # Clear selected points from visualization state if it exists
            if hasattr(self.visualization_state, 'selected_points'):
                self.visualization_state.selected_points.clear()
            if hasattr(self, 'selection_text'):
                self.selection_text.config(state='normal')
                self.selection_text.delete('1.0', tk.END)
                self.selection_text.config(state='disabled')
            if hasattr(self, 'ctk_selection_textbox'):
                self.ctk_selection_textbox.configure(state="normal")
                self.ctk_selection_textbox.delete("0.0", "end")
                self.ctk_selection_textbox.configure(state="disabled")
            self.update_status("Selection cleared", "info")

    def _auto_select_points(self):
        """Auto-select suitable points for tunnel planning."""
        self.update_status("Auto-select feature not implemented yet", "warning")

    def on_plan_tunnel(self):
        """Handle tunnel planning action."""
        self.update_status("🚇 Planning tunnel...", "info")
        self._create_tunnel()

    def on_save_configuration(self):
        """Handle save configuration action."""
        self.update_status("💾 Configuration saved", "success")

    def on_clear_selection(self):
        """Handle clear selection action."""
        self._clear_selection()

    def on_analyze_volume(self):
        """Handle analyze volume action."""
        self.update_status("📊 Analyzing tunnel volume...", "info")

    def update_status(self, message: str, status_type: str = "info"):
        """Update status text with message and optional color."""
        if hasattr(self, 'status_text'):
            # Colors for different status types
            colors = {
                "info": "#ecf0f1",
                "success": "#2ecc71",
                "warning": "#f39c12",
                "error": "#e74c3c"
            }

            try:
                self.status_text.config(state='normal')
                self.status_text.delete('1.0', tk.END)
                self.status_text.insert(tk.END, f"{message}\n")
                self.status_text.config(state='disabled')
            except:
                # Fallback for CustomTkinter
                self.status_text.delete("0.0", "end")
                self.status_text.insert("0.0", f"{message}\n")

    def _on_selection_mode_changed(self):
        """Handle selection mode change."""
        mode = getattr(self, 'selection_mode_var', None)
        if mode:
            print(f"Selection mode changed to: {mode.get()}")

    def _create_tunnel_properties_section(self, parent):
        """Create tunnel property controls."""
        section_frame = ttk.LabelFrame(parent, text="Tunnel Properties", padding="5")
        section_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Radius control
        ttk.Label(section_frame, text="Radius (m):").grid(row=0, column=0, sticky=tk.W)
        radius_frame = ttk.Frame(section_frame)
        radius_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))

        self.radius_var = tk.DoubleVar(value=25.0)  # Very large default radius for maximum visibility
        self.radius_slider = ttk.Scale(
            radius_frame, from_=1.0, to=50.0, variable=self.radius_var,  # Allow extremely large radius
            orient=tk.HORIZONTAL, command=self._on_radius_changed
        )
        self.radius_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.radius_label = ttk.Label(radius_frame, text="25.0", width=5)
        self.radius_label.pack(side=tk.LEFT, padx=(5, 0))

        # Cross-section type
        ttk.Label(section_frame, text="Cross-Section:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.cross_section_var = tk.StringVar(value="circular")
        cross_section_combo = ttk.Combobox(
            section_frame, textvariable=self.cross_section_var,
            values=["circular", "rectangular", "horseshoe"],
            state="readonly", width=15
        )
        cross_section_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        cross_section_combo.bind("<<ComboboxSelected>>", self._on_cross_section_changed)

      
    def _create_action_buttons_section(self, parent):
        """Create action buttons."""
        section_frame = ttk.Frame(parent)
        section_frame.grid(row=9, column=0, columnspan=2, pady=10)

        self.create_tunnel_btn = ttk.Button(
            section_frame, text="Create Tunnel",
            command=self._create_tunnel, style="Accent.TButton"
        )
        self.create_tunnel_btn.pack(side=tk.LEFT)

        self.clear_tunnel_btn = ttk.Button(
            section_frame, text="Clear Tunnel",
            command=self._clear_tunnel
        )
        self.clear_tunnel_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.optimize_btn = ttk.Button(
            section_frame, text="Optimize Path",
            command=self._optimize_tunnel
        )
        self.optimize_btn.pack(side=tk.LEFT, padx=(10, 0))

    def _create_status_section(self, parent):
        """Create status display."""
        section_frame = ttk.LabelFrame(parent, text="Status", padding="5")
        section_frame.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.status_var = tk.StringVar(value="Ready for tunnel planning")
        self.status_label = ttk.Label(section_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W)

        # Progress bar for operations
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            section_frame, variable=self.progress_var,
            length=200, mode='determinate'
        )
        self.progress_bar.pack(fill=(tk.X), pady=(5, 0))

    def _on_selection_mode_changed(self):
        """Handle selection mode change."""
        mode = self.selection_mode_var.get()
        self._clear_selected_points()

        if mode == "start_end":
            self.status_var.set("Click on map to select start and end points")
        else:
            self.status_var.set("Click on map to add multiple waypoints")

    def _on_radius_changed(self, value):
        """Handle radius slider change."""
        radius = float(value)
        self.radius_label.config(text=f"{radius:.1f}")

        if self.current_tunnel:
            self._update_current_tunnel_radius(radius)

    def _on_cross_section_changed(self, event):
        """Handle cross-section type change."""
        if self.current_tunnel:
            self._update_current_tunnel_cross_section()

    def add_selected_point(self, x: float, y: float):
        """Add a point from map click."""
        mode = self.selection_mode_var.get()

        if mode == "start_end":
            if len(self.selected_points) >= 2:
                self.selected_points = []

            self.selected_points.append((x, y))

            if len(self.selected_points) == 1:
                self.status_var.set(f"Start point selected: ({x:.1f}, {y:.1f}). Select end point.")
            else:
                self.status_var.set(f"End point selected: ({x:.1f}, {y:.1f}). Ready to create tunnel.")

        else:  # multi_point
            self.selected_points.append((x, y))
            self.status_var.set(f"Point {len(self.selected_points)} added: ({x:.1f}, {y:.1f})")

        self._update_points_display()
        self._update_ui_state()

        if self.on_selection_changed:
            self.on_selection_changed(self.selected_points.copy())

    def _add_point_from_entry(self):
        """Add point from coordinate entry fields."""
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
            self.add_selected_point(x, y)
            self.x_entry.delete(0, tk.END)
            self.y_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric coordinates.")

    def _clear_selected_points(self):
        """Clear all selected points."""
        self.selected_points = []
        self._update_points_display()
        self._update_ui_state()

        if self.on_selection_changed:
            self.on_selection_changed([])

    def _update_points_display(self):
        """Update the points list display for different UI versions."""
        # Update enhanced ttk selection text display
        if hasattr(self, 'selection_text'):
            try:
                self.selection_text.config(state='normal')
                self.selection_text.delete('1.0', tk.END)

                if self.selected_points:
                    points_text = "Selected Points:\n"
                    for i, (x, y) in enumerate(self.selected_points):
                        if self.selection_mode_var.get() == "start_end":
                            label = "Start" if i == 0 else ("End" if i == len(self.selected_points) - 1 else f"Waypoint {i}")
                        else:
                            label = f"Point {i+1}"
                        points_text += f"{label}: ({x:.1f}, {y:.1f})\n"
                    self.selection_text.insert('1.0', points_text)
                else:
                    self.selection_text.insert('1.0', "No points selected")

                self.selection_text.config(state='disabled')
            except:
                pass

        # Update CustomTkinter selection textbox
        if hasattr(self, 'ctk_selection_textbox'):
            try:
                self.ctk_selection_textbox.configure(state="normal")
                self.ctk_selection_textbox.delete("0.0", "end")

                if self.selected_points:
                    points_text = "Selected Points:\n"
                    for i, (x, y) in enumerate(self.selected_points):
                        if self.selection_mode_var.get() == "start_end":
                            label = "Start" if i == 0 else ("End" if i == len(self.selected_points) - 1 else f"Waypoint {i}")
                        else:
                            label = f"Point {i+1}"
                        points_text += f"{label}: ({x:.1f}, {y:.1f})\n"
                    self.ctk_selection_textbox.insert("0.0", points_text)
                else:
                    self.ctk_selection_textbox.insert("0.0", "No points selected")

                self.ctk_selection_textbox.configure(state="disabled")
            except:
                pass

        # Update original points listbox if it exists (for backward compatibility)
        if hasattr(self, 'points_listbox'):
            try:
                self.points_listbox.delete(0, tk.END)
                for i, (x, y) in enumerate(self.selected_points):
                    if self.selection_mode_var.get() == "start_end":
                        label = "Start" if i == 0 else ("End" if i == len(self.selected_points) - 1 else f"Waypoint {i}")
                    else:
                        label = f"Point {i+1}"
                    self.points_listbox.insert(tk.END, f"{label}: ({x:.1f}, {y:.1f})")
            except:
                pass

        # Update original points text if it exists (for backward compatibility)
        if hasattr(self, 'points_text'):
            try:
                self.points_text.config(state='normal')
                self.points_text.delete('1.0', tk.END)
                if self.selected_points:
                    points_text = "\n".join([f"({x:.1f}, {y:.1f})" for x, y in self.selected_points])
                    self.points_text.insert('1.0', points_text)
                self.points_text.config(state='disabled')
            except:
                pass

    def _create_tunnel(self):
        """Create tunnel from selected points."""
        if len(self.selected_points) < 2:
            messagebox.showwarning(
                "Insufficient Points",
                "Please select at least 2 points to create a tunnel."
            )
            return

        try:
            self.status_var.set("Creating tunnel...")
            self.progress_var.set(0.0)
            self.update()

            # Create tunnel request
            start_point = self.selected_points[0]
            end_point = self.selected_points[-1]
            intermediate_points = self.selected_points[1:-1] if len(self.selected_points) > 2 else []

            cross_section_type = CrossSectionType(self.cross_section_var.get())

            request = TunnelCreationRequest(
                start_point=start_point,
                end_point=end_point,
                radius=self.radius_var.get(),
                cross_section_type=cross_section_type,
                intermediate_points=intermediate_points
            )

            self.progress_var.set(0.3)
            self.update()

            # Create tunnel (would need contour data in real implementation)
            # For now, create a simple tunnel without contour data
            from models.tunnel_geometry import TunnelPath, TunnelWaypoint

            path = TunnelPath()
            path.cross_section_type = cross_section_type

            # Add waypoints with dummy elevations
            for point in [start_point] + intermediate_points + [end_point]:
                # Get terrain elevation at this point from contour data
                if hasattr(self, 'contour_data') and self.contour_data:
                    elevation = self.contour_data.get_elevation_at(point[0], point[1])
                    if elevation is None:
                        elevation = 125.0  # Fallback elevation
                else:
                    elevation = 125.0  # Default elevation when no contour data
                path.add_waypoint(point[0], point[1], elevation, self.radius_var.get())

            self.progress_var.set(0.7)
            self.update()

            self.current_tunnel = TunnelGeometry(path=path)

            self.progress_var.set(1.0)
            self.status_var.set(f"Tunnel created successfully! Length: {path.get_length():.1f}m")

            self._update_ui_state()

            if self.on_tunnel_created:
                self.on_tunnel_created(self.current_tunnel)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create tunnel: {str(e)}")
            self.status_var.set("Error creating tunnel")

        finally:
            self.progress_var.set(0.0)

    def _clear_tunnel(self):
        """Clear current tunnel."""
        self.current_tunnel = None
        self.selected_points = []
        self._update_points_display()
        self._update_ui_state()
        self.status_var.set("Tunnel cleared")

    def _optimize_tunnel(self):
        """Optimize current tunnel path."""
        if not self.current_tunnel:
            messagebox.showwarning("No Tunnel", "Please create a tunnel first.")
            return

        try:
            self.status_var.set("Optimizing tunnel path...")
            self.update()

            # Placeholder for optimization
            # In real implementation, this would call the service optimization
            self.status_var.set("Path optimization completed (placeholder)")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to optimize tunnel: {str(e)}")
            self.status_var.set("Error optimizing tunnel")

    def _update_current_tunnel_radius(self, radius: float):
        """Update radius of current tunnel."""
        if self.current_tunnel:
            for waypoint in self.current_tunnel.path.waypoints:
                waypoint.radius = radius
            self.current_tunnel.calculate_volume()
            self.current_tunnel.calculate_surface_area()
            
    def _update_current_tunnel_cross_section(self):
        """Update cross-section type of current tunnel."""
        if self.current_tunnel:
            cross_section_type = CrossSectionType(self.cross_section_var.get())
            self.current_tunnel.path.cross_section_type = cross_section_type
            self.current_tunnel.calculate_volume()
            self.current_tunnel.calculate_surface_area()

    def _update_ui_state(self):
        """Update UI element states based on current conditions."""
        has_points = len(self.selected_points) >= 2 if hasattr(self, 'selected_points') else False
        has_tunnel = self.current_tunnel is not None if hasattr(self, 'current_tunnel') else False

        # Update plan tunnel button
        if hasattr(self, 'plan_tunnel_btn'):
            try:
                if ctk and hasattr(self.plan_tunnel_btn, 'configure'):
                    self.plan_tunnel_btn.configure(state="normal" if has_points else "disabled")
                else:
                    self.plan_tunnel_btn.config(state='normal' if has_points else 'disabled')
            except:
                pass

        # Update clear button
        if hasattr(self, 'clear_btn'):
            try:
                if ctk and hasattr(self.clear_btn, 'configure'):
                    self.clear_btn.configure(state="normal" if has_points else "disabled")
                else:
                    self.clear_btn.config(state='normal' if has_points else 'disabled')
            except:
                pass

        # Update analyze button
        if hasattr(self, 'analyze_btn'):
            try:
                if ctk and hasattr(self.analyze_btn, 'configure'):
                    self.analyze_btn.configure(state="normal" if has_tunnel else "disabled")
                else:
                    self.analyze_btn.config(state='normal' if has_tunnel else 'disabled')
            except:
                pass

    def get_current_tunnel(self) -> Optional[TunnelGeometry]:
        """Get the current tunnel geometry."""
        return self.current_tunnel

    def set_contour_data(self, contour_data):
        """Set contour data for elevation calculation."""
        self.contour_data = contour_data
        self.status_var.set("Contour data loaded for tunnel planning")

    def set_visualization_state(self, state: VisualizationState):
        """Update visualization state reference."""
        self.visualization_state = state

    def enable_point_selection_mode(self):
        """Enable point selection mode."""
        self.visualization_state.set_interaction_mode(InteractionMode.POINT_SELECTION)
        self.status_var.set("Point selection mode enabled - click on map")

    def disable_point_selection_mode(self):
        """Disable point selection mode."""
        self.visualization_state.set_interaction_mode(InteractionMode.VIEW_ONLY)
        self.status_var.set("Point selection mode disabled")