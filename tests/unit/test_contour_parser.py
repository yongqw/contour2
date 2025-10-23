"""
Unit tests for contour file parser.

These tests validate the contour file parsing functionality,
including JSON format validation, data integrity checks, and error handling.
"""

import pytest
import numpy as np
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.services.contour_parser import ContourParser
from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.utils.exceptions import InvalidContourFileError, ValidationError, FileOperationError
from src.utils.math_utils import BoundingBox


class TestContourParser:
    """Test cases for ContourParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ContourParser()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_valid_contour_file(self, file_path: str) -> None:
        """Create a valid contour file for testing."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local",
                "created_date": "2025-10-20T12:00:00Z",
                "source": "test",
                "description": "Test contour data"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                    "is_closed": True
                },
                {
                    "elevation": 110.0,
                    "points": [[2.0, 2.0], [8.0, 2.0], [8.0, 8.0], [2.0, 8.0], [2.0, 2.0]],
                    "is_closed": True
                }
            ]
        }

        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

    def test_parse_valid_contour_file(self):
        """Test parsing a valid contour file."""
        file_path = os.path.join(self.temp_dir, "valid_contours.json")
        self.create_valid_contour_file(file_path)

        contour_data = self.parser.parse_file(file_path)

        assert isinstance(contour_data, ContourData)
        assert contour_data.metadata.name == "Test Terrain"
        assert contour_data.metadata.units == "meters"
        assert contour_data.coordinate_system == CoordinateSystem.LOCAL
        assert len(contour_data.contours) == 2

        # Check first contour
        contour1 = contour_data.contours[0]
        assert contour1.elevation == 100.0
        assert contour1.is_closed is True
        assert len(contour1.points) == 5
        assert contour1.points.shape == (5, 2)

    def test_parse_file_missing_metadata(self):
        """Test parsing file with missing metadata section."""
        contour_data = {
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "missing_metadata.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="metadata section is required"):
            self.parser.parse_file(file_path)

    def test_parse_file_missing_contours(self):
        """Test parsing file with missing contours section."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            }
        }

        file_path = os.path.join(self.temp_dir, "missing_contours.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="contours section is required"):
            self.parser.parse_file(file_path)

    def test_parse_file_invalid_json(self):
        """Test parsing file with invalid JSON."""
        file_path = os.path.join(self.temp_dir, "invalid.json")
        with open(file_path, 'w') as f:
            f.write("{ invalid json content")

        with pytest.raises(InvalidContourFileError, match="Invalid JSON format"):
            self.parser.parse_file(file_path)

    def test_parse_file_nonexistent_file(self):
        """Test parsing non-existent file."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.json")

        with pytest.raises(FileOperationError, match="File not found"):
            self.parser.parse_file(nonexistent_path)

    def test_parse_contour_invalid_elevation(self):
        """Test parsing contour with invalid elevation."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": "invalid",  # Should be a number
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "invalid_elevation.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="Contour elevation must be a number"):
            self.parser.parse_file(file_path)

    def test_parse_contour_invalid_points(self):
        """Test parsing contour with invalid points format."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": "invalid_points",  # Should be a list
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "invalid_points.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="Contour points must be a list"):
            self.parser.parse_file(file_path)

    def test_parse_contour_insufficient_points(self):
        """Test parsing contour with insufficient points."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0, 0.0], [1.0, 1.0]],  # Only 2 points
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "insufficient_points.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="Contour must have at least 3 points"):
            self.parser.parse_file(file_path)

    def test_parse_contour_invalid_point_format(self):
        """Test parsing contour with invalid point format."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0], [1.0, 1.0], [2.0, 2.0]],  # First point has only 1 coordinate
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "invalid_point_format.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="Each point must have exactly 2 coordinates"):
            self.parser.parse_file(file_path)

    def test_parse_contour_non_numeric_coordinates(self):
        """Test parsing contour with non-numeric coordinates."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [["invalid", 0.0], [1.0, 1.0], [2.0, 2.0]],
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "non_numeric_coords.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="Point coordinates must be numbers"):
            self.parser.parse_file(file_path)

    def test_parse_empty_contours_list(self):
        """Test parsing file with empty contours list."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": []
        }

        file_path = os.path.join(self.temp_dir, "empty_contours.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="At least one contour is required"):
            self.parser.parse_file(file_path)

    def test_parse_invalid_coordinate_system(self):
        """Test parsing file with invalid coordinate system."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "invalid_system"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "invalid_coordsys.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(InvalidContourFileError, match="Invalid coordinate system"):
            self.parser.parse_file(file_path)

    def test_validate_contour_data_success(self):
        """Test successful validation of contour data."""
        file_path = os.path.join(self.temp_dir, "valid_contours.json")
        self.create_valid_contour_file(file_path)

        contour_data = self.parser.parse_file(file_path)

        # Should not raise any exceptions
        self.parser.validate_contour_data(contour_data)

    def test_validate_contour_data_extreme_elevations(self):
        """Test validation failure with extreme elevations."""
        contour_data = {
            "metadata": {
                "name": "Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": 15000.0,  # Too high elevation
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "extreme_elevation.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        with pytest.raises(ValidationError, match="Elevation out of valid range"):
            self.parser.parse_file(file_path)

    def test_parse_large_file_performance(self):
        """Test parsing performance with large contour files."""
        import time

        # Create large contour file
        large_contour_data = {
            "metadata": {
                "name": "Large Test Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": []
        }

        # Generate many contours with many points
        for i in range(50):  # 50 contours
            elevation = 100.0 + i * 10.0
            points = []
            for j in range(200):  # 200 points per contour
                angle = 2 * np.pi * j / 200
                x = 50.0 * np.cos(angle) + i
                y = 50.0 * np.sin(angle) + i
                points.append([x, y])
            points.append(points[0])  # Close contour

            large_contour_data["contours"].append({
                "elevation": elevation,
                "points": points,
                "is_closed": True
            })

        file_path = os.path.join(self.temp_dir, "large_contours.json")
        with open(file_path, 'w') as f:
            json.dump(large_contour_data, f)

        # Test parsing performance
        start_time = time.time()
        contour_data = self.parser.parse_file(file_path)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 2.0  # Less than 2 seconds
        assert len(contour_data.contours) == 50
        assert len(contour_data.contours[0].points) == 201  # 200 + 1 closing point

    def test_get_supported_file_extensions(self):
        """Test getting supported file extensions."""
        extensions = self.parser.get_supported_extensions()
        assert isinstance(extensions, list)
        assert ".json" in extensions

    def test_is_file_supported(self):
        """Test checking if file format is supported."""
        assert self.parser.is_file_supported("test.json") is True
        assert self.parser.is_file_supported("test.txt") is False
        assert self.parser.is_file_supported("test.JSON") is True  # Case insensitive

    def test_save_contour_data(self):
        """Test saving contour data to file."""
        file_path = os.path.join(self.temp_dir, "valid_contours.json")
        self.create_valid_contour_file(file_path)

        # Load the contour data
        contour_data = self.parser.parse_file(file_path)

        # Save to a new file
        saved_path = os.path.join(self.temp_dir, "saved_contours.json")
        self.parser.save_contour_data(contour_data, saved_path)

        # Verify the file was created and can be parsed back
        assert os.path.exists(saved_path)

        # Parse the saved file and verify it matches original
        saved_data = self.parser.parse_file(saved_path)
        assert saved_data.metadata.name == contour_data.metadata.name
        assert len(saved_data.contours) == len(contour_data.contours)
        assert saved_data.contours[0].elevation == contour_data.contours[0].elevation

    def test_save_contour_data_creates_directory(self):
        """Test that save_contour_data creates directories if they don't exist."""
        file_path = os.path.join(self.temp_dir, "valid_contours.json")
        self.create_valid_contour_file(file_path)

        contour_data = self.parser.parse_file(file_path)

        # Save to a nested directory that doesn't exist
        nested_path = os.path.join(self.temp_dir, "nested", "dir", "saved_contours.json")
        self.parser.save_contour_data(contour_data, nested_path)

        # Verify the directory was created and file exists
        assert os.path.exists(nested_path)

    def test_save_contour_data_file_permission_error(self):
        """Test handling file permission errors during save."""
        file_path = os.path.join(self.temp_dir, "valid_contours.json")
        self.create_valid_contour_file(file_path)

        contour_data = self.parser.parse_file(file_path)

        # Try to save to a readonly location (simulate permission error)
        readonly_path = os.path.join(self.temp_dir, "readonly.json")

        # Create file and make it readonly
        with open(readonly_path, 'w') as f:
            f.write("{}")
        os.chmod(readonly_path, 0o444)  # Read-only

        with pytest.raises(FileOperationError, match="Permission denied"):
            self.parser.save_contour_data(contour_data, readonly_path)

        # Cleanup
        os.chmod(readonly_path, 0o644)

    def test_parse_with_missing_optional_fields(self):
        """Test parsing with optional metadata fields missing."""
        contour_data = {
            "metadata": {
                "name": "Minimal Terrain",
                "units": "meters",
                "coordinate_system": "local"
                # Missing created_date, source, description
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                    "is_closed": True
                }
            ]
        }

        file_path = os.path.join(self.temp_dir, "minimal_metadata.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        contour_data_parsed = self.parser.parse_file(file_path)

        assert contour_data_parsed.metadata.name == "Minimal Terrain"
        assert contour_data_parsed.metadata.created_date is None
        assert contour_data_parsed.metadata.source is None
        assert contour_data_parsed.metadata.description is None


if __name__ == "__main__":
    pytest.main([__file__])