"""
Main application entry point for Terrain Tunneling Calculator.

This module provides the main GUI application and command-line interface
for the terrain tunneling calculator.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import ConfigManager
from utils.demo_data import DemoDataGenerator
from services.contour_parser import ContourParser
from services.triangulation import TriangulationService
from services.visualization_2d import Visualization2DService
from services.visualization_3d import Visualization3DService
from utils.exceptions import ContourError


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / "contour2.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='a')
        ]
    )


def create_demo_data(config_manager: ConfigManager) -> None:
    """Create demo contour data files for testing."""
    try:
        print("Creating demo contour data...")
        demo_generator = DemoDataGenerator()
        demo_generator.generate_all_demo_files()
        print("Demo data created successfully!")
        print(f"Files saved to: {config_manager.get_data_directory()}")
    except Exception as e:
        print(f"Error creating demo data: {e}")
        sys.exit(1)


def load_contour_file(file_path: str) -> Optional[object]:
    """
    Load contour data from file.

    Args:
        file_path: Path to contour file

    Returns:
        ContourData object or None if loading fails
    """
    try:
        parser = ContourParser()
        contour_data = parser.parse_file(file_path)
        print(f"Successfully loaded contour data from {file_path}")
        print(f"  - Name: {contour_data.metadata.name}")
        print(f"  - Contours: {len(contour_data.contours)}")
        print(f"  - Elevation range: {contour_data.get_elevation_range()}")
        return contour_data
    except Exception as e:
        print(f"Error loading contour file: {e}")
        return None


def create_visualizations(contour_data, output_dir: Optional[str] = None) -> bool:
    """
    Create 2D and 3D visualizations of contour data.

    Args:
        contour_data: ContourData object
        output_dir: Optional output directory for visualizations

    Returns:
        True if successful, False otherwise
    """
    try:
        # Initialize services
        viz_2d = Visualization2DService()
        viz_3d = Visualization3DService()

        # Generate 2D visualization
        print("Creating 2D contour plot...")
        fig_2d = viz_2d.create_contour_plot(contour_data)

        # Generate 3D terrain mesh
        print("Triangulating terrain mesh...")
        triangulation_service = TriangulationService()
        terrain_mesh = triangulation_service.triangulate_contours(contour_data)

        print(f"Generated mesh with {terrain_mesh.vertex_count} vertices and {terrain_mesh.triangle_count} triangles")

        # Generate 3D visualization
        print("Creating 3D terrain plot...")
        fig_3d = viz_3d.create_terrain_plot(terrain_mesh)

        # Save visualizations
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save 2D plot
            plot_2d_path = output_path / "contour_plot_2d.png"
            viz_2d.save_plot(fig_2d, plot_2d_path)
            print(f"2D plot saved to: {plot_2d_path}")

            # Save 3D plot
            plot_3d_path = output_path / "terrain_plot_3d.html"
            viz_3d.save_plot(fig_3d, plot_3d_path)
            print(f"3D plot saved to: {plot_3d_path}")
        else:
            # Show plots interactively
            import matplotlib.pyplot as plt
            plt.show()

            # For 3D plot, show in browser
            fig_3d.show()

        return True

    except Exception as e:
        print(f"Error creating visualizations: {e}")
        return False


def start_gui_application(config_manager: ConfigManager) -> None:
    """Start the GUI application."""
    try:
        # Import GUI modules (only if available)
        try:
            import customtkinter as ctk
            from gui.main_window import MainWindow
        except ImportError as e:
            print(f"GUI dependencies not available: {e}")
            print("Please install customtkinter: pip install customtkinter")
            sys.exit(1)

        # Set up customtkinter theme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Create and run main window
        app = MainWindow(config_manager)
        app.run()

    except Exception as e:
        print(f"Error starting GUI application: {e}")
        sys.exit(1)


def run_cli_mode(args, config_manager: ConfigManager) -> None:
    """Run application in command-line mode."""
    if args.demo:
        create_demo_data(config_manager)
        return

    if args.file:
        contour_data = load_contour_file(args.file)
        if contour_data:
            output_dir = args.output or "visualizations"
            success = create_visualizations(contour_data, output_dir)
            if not success:
                sys.exit(1)
        else:
            sys.exit(1)
    else:
        print("No file specified. Use --file <path> or --demo to generate demo data.")
        sys.exit(1)


def main() -> None:
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Terrain Tunneling Calculator - Calculate excavation volumes through terrain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --demo                    # Generate demo data
  python main.py --file terrain.json      # Load and visualize terrain file
  python main.py --gui                     # Start GUI application
  python main.py --file terrain.json --output viz/  # Save visualizations to specific directory
        """
    )

    parser.add_argument("--demo", action="store_true",
                       help="Generate demo contour data files")
    parser.add_argument("--file", type=str,
                       help="Load contour data from file")
    parser.add_argument("--output", type=str,
                       help="Output directory for visualizations")
    parser.add_argument("--gui", action="store_true",
                       help="Start GUI application")
    parser.add_argument("--config", type=str,
                       help="Path to configuration file")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()

        logger.info(f"Starting {config.app.name} v{config.app.version}")
        logger.info(f"Debug mode: {config.app.debug}")

        # Ensure directories exist
        config_manager.ensure_directories_exist()

        # Start appropriate mode
        if args.gui:
            logger.info("Starting GUI application")
            start_gui_application(config_manager)
        else:
            logger.info("Running in command-line mode")
            run_cli_mode(args, config_manager)

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        if args.log_level == "DEBUG":
            import traceback
            traceback.print_exc()
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()