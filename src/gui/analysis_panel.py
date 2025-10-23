"""
Analysis panel GUI for Terrain Tunneling Calculator.

This module provides comprehensive analysis interface components including
volume calculation, cost estimation, structural analysis, risk assessment,
and environmental impact analysis with high DPI support.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any, List, Tuple, Callable
import logging
import numpy as np
from datetime import datetime

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from models.tunnel_geometry import TunnelGeometry
from models.contour_data import ContourData
from models.analysis_result import (
    AnalysisResult, AnalysisType, CostCategory, RiskLevel,
    CostEstimate, StructuralAnalysis, RiskAssessment, EnvironmentalImpact
)
from services.volume_calculator import VolumeCalculator
from models.volume_calculator import VolumeCalculationResult, CalculationMethod
from models.terrain_mesh import TerrainMesh
from services.triangulation import TriangulationService


class AnalysisPanel(ttk.Frame):
    """Comprehensive analysis panel for tunnel volume and engineering analysis with high DPI support."""

    def __init__(
        self,
        parent: tk.Widget,
        on_analysis_complete: Optional[Callable[[AnalysisResult], None]] = None
    ):
        """
        Initialize analysis panel.

        Args:
            parent: Parent widget
            on_analysis_complete: Callback when analysis is completed
        """
        super().__init__(parent)

        self.on_analysis_complete = on_analysis_complete
        self.logger = logging.getLogger(__name__)

        # Services
        self.volume_calculator = VolumeCalculator()
        self.triangulation_service = TriangulationService()

        # Data
        self.current_tunnel: Optional[TunnelGeometry] = None
        self.contour_data: Optional[ContourData] = None
        self.terrain_mesh: Optional[TerrainMesh] = None
        self.current_analysis: Optional[AnalysisResult] = None

        # Analysis state
        self.analysis_in_progress = False

        self._setup_ui()
        self._update_ui_state()

    def _setup_ui(self):
        """Set up the user interface with high DPI support."""
        # Determine font sizes based on DPI scaling
        if ctk:
            title_font = ctk.CTkFont(size=18, weight="bold")
            label_font = ctk.CTkFont(size=14, weight="bold")
            normal_font = ctk.CTkFont(size=12)
            button_font = ctk.CTkFont(size=12)
            # Create customtkinter frame
            main_frame = ctk.CTkFrame(self)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            use_ctk = True
        else:
            # Fallback to larger tkinter fonts for high DPI
            title_font = ("Arial", 16, "bold")
            label_font = ("Arial", 14, "bold")
            normal_font = ("Arial", 12)
            button_font = ("Arial", 11)
            main_frame = ttk.Frame(self, padding="15")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.columnconfigure(0, weight=1)
            self.rowconfigure(0, weight=1)
            use_ctk = False

        # Title
        if use_ctk:
            title_label = ctk.CTkLabel(
                main_frame,
                text="📊 Tunnel Analysis Tools",
                font=title_font
            )
            title_label.pack(pady=(15, 20))
        else:
            title_label = ttk.Label(
                main_frame,
                text="📊 Tunnel Analysis Tools",
                font=title_font
            )
            title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # Create sections based on whether we're using customtkinter or standard tkinter
        if use_ctk:
            self._create_ctk_volume_section(main_frame)
            self._create_ctk_analysis_options_section(main_frame)
            self._create_ctk_results_section(main_frame)
            self._create_ctk_export_section(main_frame)
        else:
            # Create ttk separators for standard tkinter
            ttk.Separator(main_frame, orient='horizontal').grid(
                row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
            )
            self._create_volume_calculation_section(main_frame)

            ttk.Separator(main_frame, orient='horizontal').grid(
                row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
            )
            self._create_analysis_options_section(main_frame)

            ttk.Separator(main_frame, orient='horizontal').grid(
                row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
            )
            self._create_results_section(main_frame)

            ttk.Separator(main_frame, orient='horizontal').grid(
                row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
            )
            self._create_export_section(main_frame)

    def _create_volume_calculation_section(self, parent):
        """Create volume calculation controls."""
        section_frame = ttk.LabelFrame(parent, text="Volume Calculation", padding="5")
        section_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Calculation method
        ttk.Label(section_frame, text="Method:").grid(row=0, column=0, sticky=tk.W)
        self.method_var = tk.StringVar(value="analytical")
        method_combo = ttk.Combobox(
            section_frame,
            textvariable=self.method_var,
            values=["analytical", "tetrahedral", "monte_carlo", "hybrid"],
            state="readonly",
            width=15
        )
        method_combo.grid(row=0, column=1, padx=(5, 0), sticky=(tk.W, tk.E))

        # Accuracy validation
        self.validate_accuracy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            section_frame,
            text="Validate Accuracy",
            variable=self.validate_accuracy_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # Calculate button
        self.calculate_btn = ttk.Button(
            section_frame,
            text="Calculate Volume",
            command=self._calculate_volume,
            style="Accent.TButton"
        )
        self.calculate_btn.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            section_frame,
            variable=self.progress_var,
            mode='indeterminate'
        )
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))

    def _create_analysis_options_section(self, parent):
        """Create comprehensive analysis options."""
        section_frame = ttk.LabelFrame(parent, text="Analysis Options", padding="5")
        section_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Analysis types
        ttk.Label(section_frame, text="Analysis Types:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )

        # Cost estimation
        self.cost_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            section_frame,
            text="Cost Estimation",
            variable=self.cost_analysis_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W)

        # Structural analysis
        self.structural_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            section_frame,
            text="Structural Analysis",
            variable=self.structural_analysis_var
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W)

        # Risk assessment
        self.risk_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            section_frame,
            text="Risk Assessment",
            variable=self.risk_analysis_var
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W)

        # Environmental impact
        self.environmental_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            section_frame,
            text="Environmental Impact",
            variable=self.environmental_analysis_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W)

        # Material properties
        ttk.Label(section_frame, text="Material Properties:", font=("Arial", 10, "bold")).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 5)
        )

        ttk.Label(section_frame, text="Rock Type:").grid(row=6, column=0, sticky=tk.W)
        self.rock_type_var = tk.StringVar(value="medium_rock")
        rock_combo = ttk.Combobox(
            section_frame,
            textvariable=self.rock_type_var,
            values=["soft_rock", "medium_rock", "hard_rock", "mixed_rock"],
            state="readonly",
            width=15
        )
        rock_combo.grid(row=6, column=1, padx=(5, 0), sticky=(tk.W, tk.E))

        ttk.Label(section_frame, text="Groundwater:").grid(row=7, column=0, sticky=tk.W, pady=(5, 0))
        self.groundwater_var = tk.StringVar(value="dry")
        groundwater_combo = ttk.Combobox(
            section_frame,
            textvariable=self.groundwater_var,
            values=["dry", "damp", "wet", "flowing"],
            state="readonly",
            width=15
        )
        groundwater_combo.grid(row=7, column=1, padx=(5, 0), sticky=(tk.W, tk.E), pady=(5, 0))

    def _create_results_section(self, parent):
        """Create results display area."""
        section_frame = ttk.LabelFrame(parent, text="Analysis Results", padding="5")
        section_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # Configure grid weights for the section
        section_frame.columnconfigure(0, weight=1)
        section_frame.rowconfigure(0, weight=1)

        # Create notebook for tabbed results
        self.results_notebook = ttk.Notebook(section_frame)
        self.results_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Volume results tab
        self.volume_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.volume_frame, text="Volume")
        self._create_volume_results_tab()

        # Cost results tab
        self.cost_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.cost_frame, text="Cost")
        self._create_cost_results_tab()

        # Structural results tab
        self.structural_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.structural_frame, text="Structural")
        self._create_structural_results_tab()

        # Risk results tab
        self.risk_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.risk_frame, text="Risk")
        self._create_risk_results_tab()

        # Environmental results tab
        self.environmental_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.environmental_frame, text="Environmental")
        self._create_environmental_results_tab()

    def _create_volume_results_tab(self):
        """Create volume results display tab."""
        # Create text widget with scrollbar
        text_frame = ttk.Frame(self.volume_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.volume_text = tk.Text(text_frame, height=15, width=40, wrap=tk.WORD, state='disabled')
        volume_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.volume_text.yview)
        self.volume_text.configure(yscrollcommand=volume_scrollbar.set)

        self.volume_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        volume_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

    def _create_cost_results_tab(self):
        """Create cost estimation results tab."""
        text_frame = ttk.Frame(self.cost_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.cost_text = tk.Text(text_frame, height=15, width=40, wrap=tk.WORD, state='disabled')
        cost_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.cost_text.yview)
        self.cost_text.configure(yscrollcommand=cost_scrollbar.set)

        self.cost_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        cost_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

    def _create_structural_results_tab(self):
        """Create structural analysis results tab."""
        text_frame = ttk.Frame(self.structural_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.structural_text = tk.Text(text_frame, height=15, width=40, wrap=tk.WORD, state='disabled')
        structural_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.structural_text.yview)
        self.structural_text.configure(yscrollcommand=structural_scrollbar.set)

        self.structural_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        structural_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

    def _create_risk_results_tab(self):
        """Create risk assessment results tab."""
        text_frame = ttk.Frame(self.risk_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.risk_text = tk.Text(text_frame, height=15, width=40, wrap=tk.WORD, state='disabled')
        risk_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.risk_text.yview)
        self.risk_text.configure(yscrollcommand=risk_scrollbar.set)

        self.risk_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        risk_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

    def _create_environmental_results_tab(self):
        """Create environmental impact results tab."""
        text_frame = ttk.Frame(self.environmental_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.environmental_text = tk.Text(text_frame, height=15, width=40, wrap=tk.WORD, state='disabled')
        environmental_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.environmental_text.yview)
        self.environmental_text.configure(yscrollcommand=environmental_scrollbar.set)

        self.environmental_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        environmental_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

    def _create_export_section(self, parent):
        """Create export actions section."""
        section_frame = ttk.LabelFrame(parent, text="Export Options", padding="5")
        section_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Export buttons
        self.export_csv_btn = ttk.Button(
            section_frame,
            text="Export CSV Report",
            command=self._export_csv,
            state='disabled'
        )
        self.export_csv_btn.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky=(tk.W, tk.E))

        self.export_json_btn = ttk.Button(
            section_frame,
            text="Export JSON Data",
            command=self._export_json,
            state='disabled'
        )
        self.export_json_btn.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky=(tk.W, tk.E))

        self.export_summary_btn = ttk.Button(
            section_frame,
            text="Generate Summary",
            command=self._generate_summary,
            state='disabled'
        )
        self.export_summary_btn.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=(tk.W, tk.E))

        section_frame.columnconfigure(0, weight=1)
        section_frame.columnconfigure(1, weight=1)

    def set_tunnel_geometry(self, tunnel_geometry: Optional[TunnelGeometry]):
        """Set the tunnel geometry for analysis."""
        self.current_tunnel = tunnel_geometry
        self._update_ui_state()

    def set_contour_data(self, contour_data: Optional[ContourData]):
        """Set the contour data for analysis."""
        self.contour_data = contour_data
        if contour_data:
            # Generate terrain mesh for volume calculations
            self.terrain_mesh = self.triangulation_service.triangulate_contours(contour_data)
        else:
            self.terrain_mesh = None
        self._update_ui_state()

    def _update_ui_state(self):
        """Update UI state based on available data."""
        has_tunnel = self.current_tunnel is not None
        has_contour = self.contour_data is not None

        # Enable/disable calculate button - handle both ttk and ctk
        button_state = 'normal' if has_tunnel else 'disabled'
        if hasattr(self.calculate_btn, 'configure'):
            # CustomTkinter widget
            self.calculate_btn.configure(state=button_state)
        else:
            # Standard tkinter widget
            self.calculate_btn.config(state=button_state)

        # Enable/disable export buttons - handle both ttk and ctk
        has_results = self.current_analysis is not None
        export_state = 'normal' if has_results else 'disabled'

        # Handle export buttons if they exist
        if hasattr(self, 'export_csv_btn'):
            if hasattr(self.export_csv_btn, 'configure'):
                self.export_csv_btn.configure(state=export_state)
            else:
                self.export_csv_btn.config(state=export_state)

        if hasattr(self, 'export_json_btn'):
            if hasattr(self.export_json_btn, 'configure'):
                self.export_json_btn.configure(state=export_state)
            else:
                self.export_json_btn.config(state=export_state)

        if hasattr(self, 'export_summary_btn'):
            if hasattr(self.export_summary_btn, 'configure'):
                self.export_summary_btn.configure(state=export_state)
            else:
                self.export_summary_btn.config(state=export_state)

    def _calculate_volume(self):
        """Perform comprehensive volume and analysis calculation."""
        if not self.current_tunnel:
            messagebox.showwarning("No Tunnel", "Please create a tunnel first.")
            return

        if self.analysis_in_progress:
            return

        try:
            self.analysis_in_progress = True
            self.progress_bar.start(10)
            self.calculate_btn.config(state='disabled')
            self._clear_results()

            # Get calculation method
            method_str = self.method_var.get()
            method_map = {
                "analytical": CalculationMethod.ANALYTICAL,
                "tetrahedral": CalculationMethod.TETRAHEDRAL,
                "monte_carlo": CalculationMethod.MONTE_CARLO,
                "hybrid": CalculationMethod.HYBRID
            }
            method = method_map.get(method_str, CalculationMethod.ANALYTICAL)

            # Perform volume calculation
            volume_result = self.volume_calculator.calculate_tunnel_volume(
                tunnel_geometry=self.current_tunnel,
                terrain_mesh=self.terrain_mesh,
                method=method,
                validate_accuracy=self.validate_accuracy_var.get(),
                generate_summary=True
            )

            # Create comprehensive analysis result
            analysis_result = AnalysisResult(
                tunnel_name=self.current_tunnel.path.name if self.current_tunnel.path.name else f"Tunnel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                analysis_date=datetime.now(),
                volume_calculation=volume_result
            )

            # Add cost estimation if selected
            if self.cost_analysis_var.get():
                cost_estimate = self._calculate_cost_estimation(volume_result)
                analysis_result.cost_estimate = cost_estimate

            # Add structural analysis if selected
            if self.structural_analysis_var.get():
                structural_analysis = self._calculate_structural_analysis(volume_result)
                analysis_result.structural_analysis = structural_analysis

            # Add risk assessment if selected
            if self.risk_analysis_var.get():
                risk_assessment = self._calculate_risk_assessment(volume_result)
                analysis_result.risk_assessment = risk_assessment

            # Add environmental impact if selected
            if self.environmental_analysis_var.get():
                environmental_impact = self._calculate_environmental_impact(volume_result)
                analysis_result.environmental_impact = environmental_impact

            # Store and display results
            self.current_analysis = analysis_result
            self._display_results(analysis_result)
            self._update_ui_state()

            # Notify completion
            if self.on_analysis_complete:
                self.on_analysis_complete(analysis_result)

            self.logger.info(f"Analysis completed: {analysis_result.tunnel_name}")

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            messagebox.showerror("Analysis Error", f"Failed to complete analysis:\n{str(e)}")
        finally:
            self.analysis_in_progress = False
            self.progress_bar.stop()
            self.calculate_btn.config(state='normal')

    def _calculate_cost_estimation(self, volume_result: VolumeCalculationResult) -> CostEstimate:
        """Calculate cost estimation based on volume and analysis parameters."""
        # Base rates (these would typically come from a database or configuration)
        base_rates = {
            "excavation": {
                "soft_rock": 50.0,   # $/m3
                "medium_rock": 80.0,
                "hard_rock": 120.0,
                "mixed_rock": 85.0
            },
            "support": {
                "soft_rock": 30.0,   # $/m3
                "medium_rock": 25.0,
                "hard_rock": 20.0,
                "mixed_rock": 25.0
            },
            "lining": {
                "soft_rock": 40.0,   # $/m3
                "medium_rock": 35.0,
                "hard_rock": 30.0,
                "mixed_rock": 35.0
            }
        }

        rock_type = self.rock_type_var.get().replace("_rock", "_rock")
        groundwater = self.groundwater_var.get()

        # Calculate base costs
        excavation_rate = base_rates["excavation"].get(rock_type, 80.0)
        support_rate = base_rates["support"].get(rock_type, 25.0)
        lining_rate = base_rates["lining"].get(rock_type, 35.0)

        # Groundwater multipliers
        groundwater_multipliers = {"dry": 1.0, "damp": 1.1, "wet": 1.2, "flowing": 1.3}
        groundwater_multiplier = groundwater_multipliers.get(groundwater, 1.0)

        volume = volume_result.total_volume
        excavation_cost = volume * excavation_rate * groundwater_multiplier
        support_cost = volume * support_rate
        lining_cost = volume * lining_rate

        # Additional costs
        design_cost = (excavation_cost + support_cost + lining_cost) * 0.05  # 5% of direct costs
        contingency_cost = (excavation_cost + support_cost + lining_cost) * 0.10  # 10% contingency

        total_cost = excavation_cost + support_cost + lining_cost + design_cost + contingency_cost

        return CostEstimate(
            excavation_cost=excavation_cost,
            support_cost=support_cost,
            lining_cost=lining_cost,
            total_cost=total_cost,
            cost_per_cubic_meter=total_cost / volume if volume > 0 else 0,
            currency="USD",
            calculation_date=datetime.now()
        )

    def _calculate_structural_analysis(self, volume_result: VolumeCalculationResult) -> StructuralAnalysis:
        """Calculate structural analysis based on tunnel and geological parameters."""
        rock_type = self.rock_type_var.get()
        groundwater = self.groundwater_var.get()

        # Simplified rock mass rating calculation
        rock_ratings = {"soft_rock": 40, "medium_rock": 60, "hard_rock": 80, "mixed_rock": 55}
        base_rmr = rock_ratings.get(rock_type, 55)

        # Groundwater adjustments
        groundwater_penalties = {"dry": 0, "damp": -5, "wet": -10, "flowing": -15}
        groundwater_penalty = groundwater_penalties.get(groundwater, 0)

        rock_mass_rating = max(20, base_rmr + groundwater_penalty)

        # Safety factor calculation (simplified)
        safety_factor = 1.5 + (rock_mass_rating / 100.0)

        # Support requirements
        support_levels = {
            "light": rock_mass_rating >= 70,
            "moderate": 50 <= rock_mass_rating < 70,
            "heavy": 30 <= rock_mass_rating < 50,
            "very_heavy": rock_mass_rating < 30
        }

        required_support = "moderate"  # Default
        for level, condition in support_levels.items():
            if condition:
                required_support = level
                break

        # Stability assessment
        stability_rating = "stable" if rock_mass_rating >= 50 else "potentially_unstable"

        return StructuralAnalysis(
            rock_mass_rating=rock_mass_rating,
            safety_factor=safety_factor,
            required_support=required_support,
            stability_rating=stability_rating,
            deformation_estimate=5.0 + (100 - rock_mass_rating) * 0.2,  # mm
            analysis_date=datetime.now()
        )

    def _calculate_risk_assessment(self, volume_result: VolumeCalculationResult) -> RiskAssessment:
        """Calculate comprehensive risk assessment."""
        rock_type = self.rock_type_var.get()
        groundwater = self.groundwater_var.get()
        volume = volume_result.total_volume

        # Risk factors (simplified)
        geological_risk = {"soft_rock": 0.7, "medium_rock": 0.5, "hard_rock": 0.3, "mixed_rock": 0.6}
        groundwater_risk = {"dry": 0.2, "damp": 0.4, "wet": 0.6, "flowing": 0.8}

        # Calculate overall risk score
        geology_score = geological_risk.get(rock_type, 0.5)
        water_score = groundwater_risk.get(groundwater, 0.4)
        volume_score = min(1.0, volume / 10000.0)  # Normalize by 10,000 m3

        overall_risk_score = (geology_score + water_score + volume_score) / 3.0

        # Determine risk level
        if overall_risk_score >= 0.7:
            risk_level = RiskLevel.HIGH
        elif overall_risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Risk mitigation strategies
        mitigation_strategies = []
        if geology_score > 0.6:
            mitigation_strategies.append("Enhanced ground support system")
        if water_score > 0.6:
            mitigation_strategies.append("Comprehensive dewatering measures")
        if volume_score > 0.7:
            mitigation_strategies.append("Phased excavation approach")

        if not mitigation_strategies:
            mitigation_strategies.append("Standard tunneling procedures")

        return RiskAssessment(
            overall_risk_level=risk_level,
            geological_risk_factor=geology_score,
            hydrological_risk_factor=water_score,
            construction_risk_factor=volume_score,
            mitigation_strategies=mitigation_strategies,
            assessment_date=datetime.now()
        )

    def _calculate_environmental_impact(self, volume_result: VolumeCalculationResult) -> EnvironmentalImpact:
        """Calculate environmental impact assessment."""
        volume = volume_result.total_volume
        surface_area = getattr(self.current_tunnel, 'surface_area', volume ** 0.67 * 10)  # Approximate

        # Impact calculations (simplified)
        excavation_volume = volume
        muck_generated = volume * 2.7  # tonnes (assuming rock density)
        estimated_trees_removed = int(surface_area / 100)  # Approximate
        water_bodies_affected = 0  # Would need terrain analysis

        return EnvironmentalImpact(
            surface_disturbance_area=surface_area,
            excavation_volume=excavation_volume,
            muck_generated=muck_generated,
            trees_removed=estimated_trees_removed,
            water_bodies_affected=water_bodies_affected,
            impact_date=datetime.now()
        )

    def _display_results(self, analysis_result: AnalysisResult):
        """Display analysis results in the appropriate tabs."""
        # Display volume results
        self._display_volume_results(analysis_result.volume_calculation)

        # Display cost results
        if analysis_result.cost_estimate:
            self._display_cost_results(analysis_result.cost_estimate)

        # Display structural results
        if analysis_result.structural_analysis:
            self._display_structural_results(analysis_result.structural_analysis)

        # Display risk results
        if analysis_result.risk_assessment:
            self._display_risk_results(analysis_result.risk_assessment)

        # Display environmental results
        if analysis_result.environmental_impact:
            self._display_environmental_results(analysis_result.environmental_impact)

    def _display_volume_results(self, volume_result: VolumeCalculationResult):
        """Display volume calculation results."""
        self.volume_text.config(state='normal')
        self.volume_text.delete('1.0', tk.END)

        results_text = "VOLUME CALCULATION RESULTS\n"
        results_text += "=" * 35 + "\n\n"

        # Main volume metrics
        results_text += f"Total Volume: {volume_result.total_volume:.2f} m³\n"
        results_text += f"Calculation Method: {volume_result.calculation_method.value}\n"
        results_text += f"Accuracy Estimate: {volume_result.accuracy_estimate:.4f}\n"
        results_text += f"Numerical Stability: {volume_result.numerical_stability}\n\n"

        # Excavation zones
        if volume_result.excavation_zones:
            results_text += f"Excavation Zones: {len(volume_result.excavation_zones)}\n"
            results_text += "-" * 25 + "\n"
            for i, zone in enumerate(volume_result.excavation_zones[:5]):  # Show first 5
                results_text += f"Zone {i+1}: {zone.volume:.2f} m³ ({zone.material_type.value})\n"
            if len(volume_result.excavation_zones) > 5:
                results_text += f"... and {len(volume_result.excavation_zones) - 5} more zones\n"
            results_text += "\n"

        # Material breakdown
        material_breakdown = volume_result.get_material_breakdown()
        if material_breakdown:
            results_text += "Material Breakdown:\n"
            results_text += "-" * 20 + "\n"
            for material, volume in material_breakdown.items():
                percentage = (volume / volume_result.total_volume) * 100
                results_text += f"{material}: {volume:.2f} m³ ({percentage:.1f}%)\n"
            results_text += "\n"

        # Accuracy metrics
        if volume_result.accuracy_metrics:
            accuracy = volume_result.accuracy_metrics
            results_text += "Accuracy Metrics:\n"
            results_text += "-" * 20 + "\n"
            results_text += f"Method: {accuracy.method_used.value}\n"
            results_text += f"Error Bounds: ±{accuracy.error_bounds[1]:.2f} m³\n"
            results_text += f"Confidence Level: {accuracy.confidence_level:.1%}\n"
            results_text += f"Acceptable: {accuracy.is_acceptable()}\n"

        self.volume_text.insert('1.0', results_text)
        self.volume_text.config(state='disabled')

    def _display_cost_results(self, cost_estimate: CostEstimate):
        """Display cost estimation results."""
        self.cost_text.config(state='normal')
        self.cost_text.delete('1.0', tk.END)

        results_text = "COST ESTIMATION RESULTS\n"
        results_text += "=" * 30 + "\n\n"

        # Cost breakdown
        results_text += f"Excavation: ${cost_estimate.excavation_cost:,.2f}\n"
        results_text += f"Support: ${cost_estimate.support_cost:,.2f}\n"
        results_text += f"Lining: ${cost_estimate.lining_cost:,.2f}\n"
        results_text += "-" * 25 + "\n"
        results_text += f"Total Cost: ${cost_estimate.total_cost:,.2f}\n\n"

        # Cost metrics
        results_text += f"Cost per m³: ${cost_estimate.cost_per_cubic_meter:.2f}\n"
        results_text += f"Currency: {cost_estimate.currency}\n"

        self.cost_text.insert('1.0', results_text)
        self.cost_text.config(state='disabled')

    def _display_structural_results(self, structural_analysis: StructuralAnalysis):
        """Display structural analysis results."""
        self.structural_text.config(state='normal')
        self.structural_text.delete('1.0', tk.END)

        results_text = "STRUCTURAL ANALYSIS RESULTS\n"
        results_text += "=" * 35 + "\n\n"

        results_text += f"Rock Mass Rating: {structural_analysis.rock_mass_rating}/100\n"
        results_text += f"Safety Factor: {structural_analysis.safety_factor:.2f}\n"
        results_text += f"Required Support: {structural_analysis.required_support.replace('_', ' ').title()}\n"
        results_text += f"Stability: {structural_analysis.stability_rating.replace('_', ' ').title()}\n"
        results_text += f"Estimated Deformation: {structural_analysis.deformation_estimate:.1f} mm\n"

        self.structural_text.insert('1.0', results_text)
        self.structural_text.config(state='disabled')

    def _display_risk_results(self, risk_assessment: RiskAssessment):
        """Display risk assessment results."""
        self.risk_text.config(state='normal')
        self.risk_text.delete('1.0', tk.END)

        results_text = "RISK ASSESSMENT RESULTS\n"
        results_text += "=" * 30 + "\n\n"

        results_text += f"Overall Risk Level: {risk_assessment.overall_risk_level.value.upper()}\n\n"

        results_text += "Risk Factors:\n"
        results_text += "-" * 15 + "\n"
        results_text += f"Geological: {risk_assessment.geological_risk_factor:.2f}\n"
        results_text += f"Hydrological: {risk_assessment.hydrological_risk_factor:.2f}\n"
        results_text += f"Construction: {risk_assessment.construction_risk_factor:.2f}\n\n"

        results_text += "Mitigation Strategies:\n"
        results_text += "-" * 20 + "\n"
        for strategy in risk_assessment.mitigation_strategies:
            results_text += f"• {strategy}\n"

        self.risk_text.insert('1.0', results_text)
        self.risk_text.config(state='disabled')

    def _display_environmental_results(self, environmental_impact: EnvironmentalImpact):
        """Display environmental impact results."""
        self.environmental_text.config(state='normal')
        self.environmental_text.delete('1.0', tk.END)

        results_text = "ENVIRONMENTAL IMPACT RESULTS\n"
        results_text += "=" * 35 + "\n\n"

        results_text += f"Surface Disturbance: {environmental_impact.surface_disturbance_area:.2f} m²\n"
        results_text += f"Excavation Volume: {environmental_impact.excavation_volume:.2f} m³\n"
        results_text += f"Muck Generated: {environmental_impact.muck_generated:.0f} tonnes\n"
        results_text += f"Trees Removed: {environmental_impact.trees_removed}\n"
        results_text += f"Water Bodies Affected: {environmental_impact.water_bodies_affected}\n"

        self.environmental_text.insert('1.0', results_text)
        self.environmental_text.config(state='disabled')

    def _clear_results(self):
        """Clear all results displays."""
        # Clear volume results
        self.volume_text.config(state='normal')
        self.volume_text.delete('1.0', tk.END)
        self.volume_text.config(state='disabled')

        # Clear cost results
        self.cost_text.config(state='normal')
        self.cost_text.delete('1.0', tk.END)
        self.cost_text.config(state='disabled')

        # Clear structural results
        self.structural_text.config(state='normal')
        self.structural_text.delete('1.0', tk.END)
        self.structural_text.config(state='disabled')

        # Clear risk results
        self.risk_text.config(state='normal')
        self.risk_text.delete('1.0', tk.END)
        self.risk_text.config(state='disabled')

        # Clear environmental results
        self.environmental_text.config(state='normal')
        self.environmental_text.delete('1.0', tk.END)
        self.environmental_text.config(state='disabled')

    def _export_csv(self):
        """Export analysis results to CSV format."""
        if not self.current_analysis:
            messagebox.showwarning("No Results", "Please perform analysis first.")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Analysis Results (CSV)",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                csv_data = self.current_analysis.to_csv()
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_data)

                messagebox.showinfo("Export Successful", f"Analysis results exported to:\n{filename}")
                self.logger.info(f"Analysis results exported to CSV: {filename}")

            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
                self.logger.error(f"CSV export failed: {e}")

    def _export_json(self):
        """Export analysis results to JSON format."""
        if not self.current_analysis:
            messagebox.showwarning("No Results", "Please perform analysis first.")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Analysis Results (JSON)",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                json_data = self.current_analysis.to_json()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data)

                messagebox.showinfo("Export Successful", f"Analysis results exported to:\n{filename}")
                self.logger.info(f"Analysis results exported to JSON: {filename}")

            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
                self.logger.error(f"JSON export failed: {e}")

    def _generate_summary(self):
        """Generate and display comprehensive analysis summary."""
        if not self.current_analysis:
            messagebox.showwarning("No Results", "Please perform analysis first.")
            return

        try:
            summary = self.current_analysis.generate_summary()

            # Create summary window
            summary_window = tk.Toplevel(self)
            summary_window.title("Analysis Summary")
            summary_window.geometry("600x500")

            # Create text widget with scrollbar
            text_frame = ttk.Frame(summary_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            summary_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
            scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=summary_text.yview)
            summary_text.configure(yscrollcommand=scrollbar.set)

            summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

            text_frame.columnconfigure(0, weight=1)
            text_frame.rowconfigure(0, weight=1)

            # Insert summary text
            summary_text.insert('1.0', summary)
            summary_text.config(state='disabled')

            # Add export button
            button_frame = ttk.Frame(summary_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            ttk.Button(
                button_frame,
                text="Save Summary",
                command=lambda: self._save_summary(summary)
            ).pack(side=tk.RIGHT)

        except Exception as e:
            messagebox.showerror("Summary Error", f"Failed to generate summary:\n{str(e)}")
            self.logger.error(f"Summary generation failed: {e}")

    def _save_summary(self, summary_text: str):
        """Save analysis summary to file."""
        filename = filedialog.asksaveasfilename(
            title="Save Analysis Summary",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(summary_text)

                messagebox.showinfo("Save Successful", f"Summary saved to:\n{filename}")

            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save summary:\n{str(e)}")

    def _create_ctk_volume_section(self, parent):
        """Create volume calculation section using CustomTkinter."""
        volume_frame = ctk.CTkFrame(parent)
        volume_frame.pack(fill=tk.X, pady=10)

        # Section title
        ctk.CTkLabel(
            volume_frame,
            text="📊 Volume Calculation",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 15))

        # Calculate button with larger size
        self.calculate_btn = ctk.CTkButton(
            volume_frame,
            text="📏 Calculate Volume",
            command=self._calculate_volume,
            font=ctk.CTkFont(size=12),
            height=40,
            corner_radius=8
        )
        self.calculate_btn.pack(pady=5, padx=10, fill=tk.X)

    def _create_ctk_analysis_options_section(self, parent):
        """Create analysis options section using CustomTkinter."""
        options_frame = ctk.CTkFrame(parent)
        options_frame.pack(fill=tk.X, pady=10)

        # Section title
        ctk.CTkLabel(
            options_frame,
            text="⚙️ Analysis Options",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 15))

        # Checkboxes with larger font
        checkbox_config = {
            "font": ctk.CTkFont(size=12),
            "text_color": ("gray10", "gray90")
        }

        self.ctk_include_structural_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame,
            text="🏗️ Include Structural Analysis",
            variable=self.ctk_include_structural_var,
            **checkbox_config
        ).pack(anchor=tk.W, pady=5, padx=10)

        self.ctk_include_risk_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame,
            text="⚠️ Include Risk Assessment",
            variable=self.ctk_include_risk_var,
            **checkbox_config
        ).pack(anchor=tk.W, pady=5, padx=10)

        self.ctk_include_environmental_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame,
            text="🌿 Include Environmental Impact",
            variable=self.ctk_include_environmental_var,
            **checkbox_config
        ).pack(anchor=tk.W, pady=5, padx=10)

    def _create_ctk_results_section(self, parent):
        """Create results display section using CustomTkinter."""
        results_frame = ctk.CTkFrame(parent)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Section title
        ctk.CTkLabel(
            results_frame,
            text="📋 Analysis Results",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 15))

        # Results display textbox
        self.ctk_results_textbox = ctk.CTkTextbox(
            results_frame,
            height=200,
            font=ctk.CTkFont(size=11)
        )
        self.ctk_results_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Make it read-only initially
        self.ctk_results_textbox.configure(state="disabled")

    def _create_ctk_export_section(self, parent):
        """Create export section using CustomTkinter."""
        export_frame = ctk.CTkFrame(parent)
        export_frame.pack(fill=tk.X, pady=10)

        # Section title
        ctk.CTkLabel(
            export_frame,
            text="💾 Export Results",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 15))

        # Export buttons with larger font and size
        button_config = {
            "font": ctk.CTkFont(size=11),
            "height": 35,
            "corner_radius": 6
        }

        # Button grid
        button_row = ctk.CTkFrame(export_frame)
        button_row.pack(pady=5, padx=10, fill=tk.X)

        ctk.CTkButton(
            button_row,
            text="📄 Export PDF",
            command=self._export_to_pdf,
            **button_config
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ctk.CTkButton(
            button_row,
            text="📊 Export Excel",
            command=self._export_to_excel,
            **button_config
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Second row of buttons
        button_row2 = ctk.CTkFrame(export_frame)
        button_row2.pack(pady=5, padx=10, fill=tk.X)

        ctk.CTkButton(
            button_row2,
            text="📄 Export JSON",
            command=self._export_to_json,
            **button_config
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ctk.CTkButton(
            button_row2,
            text="📝 Export Report",
            command=self._export_report,
            **button_config
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def _export_to_pdf(self):
        """Export analysis results to PDF format."""
        if not self.current_analysis:
            messagebox.showwarning("No Analysis", "Please run an analysis first.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                title="Export Analysis Results to PDF",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )

            if filename:
                # Placeholder for PDF export functionality
                messagebox.showinfo("PDF Export", f"PDF export functionality coming soon!\n\nSelected file: {filename}")
                self.logger.info(f"PDF export requested: {filename}")

        except Exception as e:
            messagebox.showerror("PDF Export Error", f"Failed to export to PDF:\n{str(e)}")
            self.logger.error(f"PDF export failed: {e}")

    def _export_to_excel(self):
        """Export analysis results to Excel format."""
        if not self.current_analysis:
            messagebox.showwarning("No Analysis", "Please run an analysis first.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                title="Export Analysis Results to Excel",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )

            if filename:
                # Placeholder for Excel export functionality
                messagebox.showinfo("Excel Export", f"Excel export functionality coming soon!\n\nSelected file: {filename}")
                self.logger.info(f"Excel export requested: {filename}")

        except Exception as e:
            messagebox.showerror("Excel Export Error", f"Failed to export to Excel:\n{str(e)}")
            self.logger.error(f"Excel export failed: {e}")

    def _export_to_json(self):
        """Export analysis results to JSON format."""
        if not self.current_analysis:
            messagebox.showwarning("No Analysis", "Please run an analysis first.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                title="Export Analysis Results to JSON",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )

            if filename:
                # Export the analysis results to JSON
                import json
                analysis_data = self.current_analysis.to_dict()

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)

                messagebox.showinfo("JSON Export Successful", f"Analysis results exported to:\n{filename}")
                self.logger.info(f"Analysis results exported to JSON: {filename}")

        except Exception as e:
            messagebox.showerror("JSON Export Error", f"Failed to export to JSON:\n{str(e)}")
            self.logger.error(f"JSON export failed: {e}")

    def _export_report(self):
        """Generate and export analysis report."""
        if not self.current_analysis:
            messagebox.showwarning("No Analysis", "Please run an analysis first.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                title="Export Analysis Report",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )

            if filename:
                # Generate report content
                report_content = self._generate_analysis_report()

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                messagebox.showinfo("Report Export Successful", f"Analysis report exported to:\n{filename}")
                self.logger.info(f"Analysis report exported: {filename}")

        except Exception as e:
            messagebox.showerror("Report Export Error", f"Failed to export report:\n{str(e)}")
            self.logger.error(f"Report export failed: {e}")

    def _generate_analysis_report(self) -> str:
        """Generate a formatted analysis report."""
        if not self.current_analysis:
            return "No analysis data available."

        report = []
        report.append("=" * 60)
        report.append("TUNNEL ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Analysis Type: {self.current_analysis.analysis_type}")
        report.append(f"Tunnel ID: {self.current_analysis.tunnel_id}")
        report.append("")

        # Add analysis results
        if hasattr(self.current_analysis, 'volume_estimate'):
            volume = self.current_analysis.volume_estimate
            report.append("VOLUME ESTIMATION")
            report.append("-" * 30)
            report.append(f"Calculated Volume: {volume.volume:.2f} cubic meters")
            report.append(f"Calculation Method: {volume.method}")
            report.append(f"Confidence Level: {volume.confidence_level:.2f}")
            report.append("")

        if hasattr(self.current_analysis, 'cost_estimate'):
            cost = self.current_analysis.cost_estimate
            report.append("COST ESTIMATION")
            report.append("-" * 30)
            report.append(f"Total Cost: ${cost.total_cost:,.2f}")
            for category, amount in cost.cost_breakdown.items():
                report.append(f"  {category}: ${amount:,.2f}")
            report.append("")

        # Add summary
        report.append("SUMMARY")
        report.append("-" * 30)
        report.append("This analysis provides comprehensive tunnel volume and")
        report.append("cost estimates for planning and budgeting purposes.")
        report.append("")
        report.append("For detailed analysis, please refer to the full")
        report.append("analysis results in the application.")

        return "\n".join(report)


# Import for callback type hint
from typing import Callable