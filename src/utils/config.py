"""
Configuration management for Terrain Tunneling Calculator.

This module handles application configuration, including loading from files,
environment variables, and providing default values.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
import logging

from .exceptions import ConfigurationError
from .file_utils import FileUtils


@dataclass
class AppConfiguration:
    """Application configuration settings."""
    name: str = "Terrain Tunneling Calculator"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"


@dataclass
class VisualizationConfiguration:
    """Visualization configuration settings."""
    default_elevation_colormap: str = "terrain"
    default_tunnel_color: str = "#FF6B6B"
    default_terrain_color: str = "#8B7355"
    animation_fps: int = 30
    show_coordinate_grid: bool = True
    color_scheme: str = "elevation"


@dataclass
class PerformanceConfiguration:
    """Performance configuration settings."""
    max_memory_mb: int = 500
    triangulation_timeout_seconds: float = 2.0
    max_triangles_for_interactive_rendering: int = 50000
    enable_gpu_acceleration: bool = True


@dataclass
class ValidationConfiguration:
    """Validation configuration settings."""
    min_elevation: float = -1000.0
    max_elevation: float = 10000.0
    min_tunnel_radius: float = 1.0
    max_tunnel_radius: float = 10.0
    max_tunnel_length: float = 1000.0
    strict_validation: bool = True


@dataclass
class PathsConfiguration:
    """File paths configuration."""
    data_dir: str = "data"
    exports_dir: str = "data/exports"
    cache_dir: str = "cache"
    log_dir: str = "logs"
    demo_file: str = "data/demo_contour.json"


@dataclass
class CompleteConfiguration:
    """Complete application configuration."""
    app: AppConfiguration = field(default_factory=AppConfiguration)
    visualization: VisualizationConfiguration = field(default_factory=VisualizationConfiguration)
    performance: PerformanceConfiguration = field(default_factory=PerformanceConfiguration)
    validation: ValidationConfiguration = field(default_factory=ValidationConfiguration)
    paths: PathsConfiguration = field(default_factory=PathsConfiguration)


class ConfigManager:
    """Configuration manager for the application."""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        self.config_file = config_file or "config.json"
        self.file_utils = FileUtils()
        self.logger = logging.getLogger(__name__)
        self._config: Optional[CompleteConfiguration] = None

    def load_config(self) -> CompleteConfiguration:
        """
        Load configuration from file or environment variables.

        Returns:
            Complete configuration object

        Raises:
            ConfigurationError: If configuration loading fails
        """
        if self._config is not None:
            return self._config

        config = CompleteConfiguration()

        # Load from config file if it exists
        if self.file_utils.file_exists(self.config_file):
            try:
                config_data = self.file_utils.read_json_file(self.config_file)
                config = self._update_config_from_dict(config, config_data)
                self.logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load config file {self.config_file}: {e}")

        # Override with environment variables
        config = self._update_config_from_environment(config)

        # Validate configuration
        self._validate_config(config)

        self._config = config
        return config

    def save_config(self, config: Optional[CompleteConfiguration] = None) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save (uses current config if None)

        Raises:
            ConfigurationError: If saving fails
        """
        if config is None:
            config = self._config

        if config is None:
            raise ConfigurationError("No configuration to save")

        try:
            config_dict = self._config_to_dict(config)
            self.file_utils.write_json_file(self.config_file, config_dict)
            self.logger.info(f"Saved configuration to {self.config_file}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def get_config(self) -> CompleteConfiguration:
        """Get the current configuration."""
        if self._config is None:
            self.load_config()
        return self._config

    def reload_config(self) -> CompleteConfiguration:
        """Reload configuration from file and environment."""
        self._config = None
        return self.load_config()

    def _update_config_from_dict(self, config: CompleteConfiguration,
                                  config_data: Dict[str, Any]) -> CompleteConfiguration:
        """Update configuration from dictionary data."""
        if 'app' in config_data:
            app_data = config_data['app']
            for key, value in app_data.items():
                if hasattr(config.app, key):
                    setattr(config.app, key, value)

        if 'visualization' in config_data:
            viz_data = config_data['visualization']
            for key, value in viz_data.items():
                if hasattr(config.visualization, key):
                    setattr(config.visualization, key, value)

        if 'performance' in config_data:
            perf_data = config_data['performance']
            for key, value in perf_data.items():
                if hasattr(config.performance, key):
                    setattr(config.performance, key, value)

        if 'validation' in config_data:
            val_data = config_data['validation']
            for key, value in val_data.items():
                if hasattr(config.validation, key):
                    setattr(config.validation, key, value)

        if 'paths' in config_data:
            path_data = config_data['paths']
            for key, value in path_data.items():
                if hasattr(config.paths, key):
                    setattr(config.paths, key, value)

        return config

    def _update_config_from_environment(self, config: CompleteConfiguration) -> CompleteConfiguration:
        """Update configuration from environment variables."""
        # App configuration
        if os.getenv('CONTOUR2_DEBUG'):
            config.app.debug = os.getenv('CONTOUR2_DEBUG').lower() in ['true', '1', 'yes']

        if os.getenv('CONTOUR2_LOG_LEVEL'):
            config.app.log_level = os.getenv('CONTOUR2_LOG_LEVEL')

        # Performance configuration
        if os.getenv('CONTOUR2_MAX_MEMORY_MB'):
            try:
                config.performance.max_memory_mb = int(os.getenv('CONTOUR2_MAX_MEMORY_MB'))
            except ValueError:
                self.logger.warning("Invalid CONTOUR2_MAX_MEMORY_MB value")

        if os.getenv('CONTOUR2_TRIANGULATION_TIMEOUT'):
            try:
                config.performance.triangulation_timeout_seconds = float(os.getenv('CONTOUR2_TRIANGULATION_TIMEOUT'))
            except ValueError:
                self.logger.warning("Invalid CONTOUR2_TRIANGULATION_TIMEOUT value")

        # Path configuration
        if os.getenv('CONTOUR2_DATA_DIR'):
            config.paths.data_dir = os.getenv('CONTOUR2_DATA_DIR')

        if os.getenv('CONTOUR2_EXPORTS_DIR'):
            config.paths.exports_dir = os.getenv('CONTOUR2_EXPORTS_DIR')

        return config

    def _validate_config(self, config: CompleteConfiguration) -> None:
        """Validate configuration values."""
        # Validate performance settings
        if config.performance.max_memory_mb <= 0:
            raise ConfigurationError("max_memory_mb must be positive")

        if config.performance.triangulation_timeout_seconds <= 0:
            raise ConfigurationError("triangulation_timeout_seconds must be positive")

        if config.performance.max_triangles_for_interactive_rendering <= 0:
            raise ConfigurationError("max_triangles_for_interactive_rendering must be positive")

        # Validate validation settings
        if config.validation.min_elevation >= config.validation.max_elevation:
            raise ConfigurationError("min_elevation must be less than max_elevation")

        if config.validation.min_tunnel_radius >= config.validation.max_tunnel_radius:
            raise ConfigurationError("min_tunnel_radius must be less than max_tunnel_radius")

        if config.validation.max_tunnel_length <= 0:
            raise ConfigurationError("max_tunnel_length must be positive")

        # Validate paths
        for path_attr in ['data_dir', 'exports_dir', 'cache_dir', 'log_dir']:
            path_value = getattr(config.paths, path_attr)
            if not path_value or len(path_value.strip()) == 0:
                raise ConfigurationError(f"{path_attr} cannot be empty")

    def _config_to_dict(self, config: CompleteConfiguration) -> Dict[str, Any]:
        """Convert configuration object to dictionary."""
        return {
            'app': {
                'name': config.app.name,
                'version': config.app.version,
                'debug': config.app.debug,
                'log_level': config.app.log_level
            },
            'visualization': {
                'default_elevation_colormap': config.visualization.default_elevation_colormap,
                'default_tunnel_color': config.visualization.default_tunnel_color,
                'default_terrain_color': config.visualization.default_terrain_color,
                'animation_fps': config.visualization.animation_fps,
                'show_coordinate_grid': config.visualization.show_coordinate_grid,
                'color_scheme': config.visualization.color_scheme
            },
            'performance': {
                'max_memory_mb': config.performance.max_memory_mb,
                'triangulation_timeout_seconds': config.performance.triangulation_timeout_seconds,
                'max_triangles_for_interactive_rendering': config.performance.max_triangles_for_interactive_rendering,
                'enable_gpu_acceleration': config.performance.enable_gpu_acceleration
            },
            'validation': {
                'min_elevation': config.validation.min_elevation,
                'max_elevation': config.validation.max_elevation,
                'min_tunnel_radius': config.validation.min_tunnel_radius,
                'max_tunnel_radius': config.validation.max_tunnel_radius,
                'max_tunnel_length': config.validation.max_tunnel_length,
                'strict_validation': config.validation.strict_validation
            },
            'paths': {
                'data_dir': config.paths.data_dir,
                'exports_dir': config.paths.exports_dir,
                'cache_dir': config.paths.cache_dir,
                'log_dir': config.paths.log_dir,
                'demo_file': config.paths.demo_file
            }
        }

    def get_app_name(self) -> str:
        """Get application name."""
        return self.get_config().app.name

    def get_version(self) -> str:
        """Get application version."""
        return self.get_config().app.version

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_config().app.debug

    def get_log_level(self) -> str:
        """Get log level."""
        return self.get_config().app.log_level

    def get_data_directory(self) -> Path:
        """Get data directory path."""
        return Path(self.get_config().paths.data_dir)

    def get_exports_directory(self) -> Path:
        """Get exports directory path."""
        return Path(self.get_config().paths.exports_dir)

    def get_demo_file_path(self) -> Path:
        """Get demo file path."""
        return Path(self.get_config().paths.demo_file)

    def ensure_directories_exist(self) -> None:
        """Ensure all configured directories exist."""
        config = self.get_config()
        directories = [
            config.paths.data_dir,
            config.paths.exports_dir,
            config.paths.cache_dir,
            config.paths.log_dir
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")