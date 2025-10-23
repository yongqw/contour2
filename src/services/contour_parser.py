"""
Contour file parser service for Terrain Tunneling Calculator.

This service handles parsing and validation of contour files in JSON format,
including data integrity checks and error handling.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from utils.math_utils import BoundingBox
from utils.exceptions import InvalidContourFileError, ValidationError, FileOperationError
from utils.validation import ValidationFramework


class ContourParser:
    """Service for parsing and validating contour files."""

    def __init__(self, validation_framework: Optional[ValidationFramework] = None):
        """
        Initialize the contour parser.

        Args:
            validation_framework: Optional validation framework instance
        """
        self.validation_framework = validation_framework or ValidationFramework()

    def parse_file(self, file_path: Union[str, Path]) -> ContourData:
        """
        Parse a contour file and return ContourData object.

        Args:
            file_path: Path to the contour file

        Returns:
            ContourData object with parsed data

        Raises:
            InvalidContourFileError: If file format is invalid
            FileOperationError: If file cannot be read
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileOperationError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidContourFileError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise FileOperationError(f"Error reading file {file_path}: {e}")

        return self._parse_data(data, str(file_path))

    def _parse_data(self, data: Dict[str, Any], file_path: str) -> ContourData:
        """
        Parse contour data from dictionary.

        Args:
            data: Dictionary containing contour data
            file_path: Original file path for error reporting

        Returns:
            ContourData object

        Raises:
            InvalidContourFileError: If data format is invalid
        """
        # Validate required sections
        if 'metadata' not in data:
            raise InvalidContourFileError("metadata section is required")
        if 'contours' not in data:
            raise InvalidContourFileError("contours section is required")

        # Parse metadata
        metadata = self._parse_metadata(data['metadata'])

        # Parse contours
        contours = self._parse_contours(data['contours'])

        if not contours:
            raise InvalidContourFileError("At least one contour is required")

        # Create bounding box
        bounds = self._create_bounds_from_contours(contours)

        # Determine coordinate system
        coordinate_system = self._parse_coordinate_system(metadata.coordinate_system)

        # Create ContourData object
        contour_data = ContourData(
            metadata=metadata,
            contours=contours,
            bounds=bounds,
            coordinate_system=coordinate_system
        )

        # Validate contour data
        self.validate_contour_data(contour_data)

        return contour_data

    def _parse_metadata(self, metadata_data: Dict[str, Any]) -> ContourMetadata:
        """
        Parse metadata from dictionary.

        Args:
            metadata_data: Dictionary containing metadata

        Returns:
            ContourMetadata object

        Raises:
            InvalidContourFileError: If metadata is invalid
        """
        required_fields = ['name', 'units', 'coordinate_system']
        for field in required_fields:
            if field not in metadata_data:
                raise InvalidContourFileError(f"Missing required metadata field: {field}")

        # Parse coordinate system
        coordinate_system_str = metadata_data['coordinate_system'].lower()
        try:
            coordinate_system = CoordinateSystem(coordinate_system_str)
        except ValueError:
            raise InvalidContourFileError(f"Invalid coordinate system: {coordinate_system_str}")

        return ContourMetadata(
            name=metadata_data['name'],
            units=metadata_data['units'],
            coordinate_system=coordinate_system,
            created_date=metadata_data.get('created_date'),
            source=metadata_data.get('source', 'unknown'),
            description=metadata_data.get('description'),
            datum=metadata_data.get('datum', 'unknown')
        )

    def _parse_contours(self, contours_data: List[Dict[str, Any]]) -> List[ContourLine]:
        """
        Parse contour lines from list of dictionaries.

        Args:
            contours_data: List of contour dictionaries

        Returns:
            List of ContourLine objects

        Raises:
            InvalidContourFileError: If contour data is invalid
        """
        contours = []

        for i, contour_data in enumerate(contours_data):
            try:
                contour = self._parse_single_contour(contour_data)
                contours.append(contour)
            except Exception as e:
                raise InvalidContourFileError(f"Error parsing contour {i+1}: {e}")

        return contours

    def _parse_single_contour(self, contour_data: Dict[str, Any]) -> ContourLine:
        """
        Parse a single contour line from dictionary.

        Args:
            contour_data: Dictionary containing contour data

        Returns:
            ContourLine object

        Raises:
            InvalidContourFileError: If contour data is invalid
        """
        # Validate required fields
        required_fields = ['elevation', 'points', 'is_closed']
        for field in required_fields:
            if field not in contour_data:
                raise InvalidContourFileError(f"Missing required contour field: {field}")

        # Parse elevation
        elevation = contour_data['elevation']
        if not isinstance(elevation, (int, float)):
            raise InvalidContourFileError("Contour elevation must be a number")

        # Parse points
        points_data = contour_data['points']
        if not isinstance(points_data, list):
            raise InvalidContourFileError("Contour points must be a list")

        if len(points_data) < 3:
            raise InvalidContourFileError("Contour must have at least 3 points")

        # Convert points to numpy array and validate
        try:
            points = np.array(points_data, dtype=float)
        except (ValueError, TypeError):
            raise InvalidContourFileError("Point coordinates must be numbers")

        if points.shape[1] != 2:
            raise InvalidContourFileError("Each point must have exactly 2 coordinates")

        # Parse is_closed
        is_closed = contour_data['is_closed']
        if not isinstance(is_closed, bool):
            raise InvalidContourFileError("is_closed must be a boolean")

        return ContourLine(
            elevation=float(elevation),
            points=points,
            is_closed=is_closed
        )

    def _parse_coordinate_system(self, coordinate_system: CoordinateSystem) -> CoordinateSystem:
        """
        Parse and validate coordinate system.

        Args:
            coordinate_system: Coordinate system from metadata

        Returns:
            Validated coordinate system
        """
        return coordinate_system

    def _create_bounds_from_contours(self, contours: List[ContourLine], margin: float = 0.0) -> BoundingBox:
        """
        Create bounding box from contour points.

        Args:
            contours: List of contour lines
            margin: Optional margin to add around bounds

        Returns:
            BoundingBox object
        """
        if not contours:
            return BoundingBox(0, 0, 0, 0)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for contour in contours:
            points = contour.points
            if len(points) > 0:
                min_x = min(min_x, np.min(points[:, 0]))
                max_x = max(max_x, np.max(points[:, 0]))
                min_y = min(min_y, np.min(points[:, 1]))
                max_y = max(max_y, np.max(points[:, 1]))

        return BoundingBox(
            min_x=min_x - margin,
            max_x=max_x + margin,
            min_y=min_y - margin,
            max_y=max_y + margin
        )

    def validate_contour_data(self, contour_data: ContourData) -> None:
        """
        Validate contour data against business rules.

        Args:
            contour_data: ContourData object to validate

        Raises:
            ValidationError: If validation fails
        """
        # Use validation framework for comprehensive validation
        validation_result = self.validation_framework.validate_contour_data(contour_data)

        if not validation_result.is_valid:
            error_messages = [error.message for error in validation_result.errors]
            raise ValidationError(f"Validation failed: {'; '.join(error_messages)}")

    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of supported file extensions
        """
        return ['.json']

    def is_file_supported(self, file_path: Union[str, Path]) -> bool:
        """
        Check if file format is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if file format is supported
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.get_supported_extensions()

    def save_contour_data(self, contour_data: ContourData, file_path: Union[str, Path]) -> None:
        """
        Save contour data to JSON file.

        Args:
            contour_data: ContourData object to save
            file_path: Output file path

        Raises:
            FileOperationError: If save operation fails
        """
        file_path = Path(file_path)

        try:
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dictionary format
            data_dict = {
                'metadata': {
                    'name': contour_data.metadata.name,
                    'units': contour_data.metadata.units,
                    'coordinate_system': contour_data.metadata.coordinate_system.value,
                    'created_date': contour_data.metadata.created_date,
                    'source': contour_data.metadata.source,
                    'description': contour_data.metadata.description,
                    'datum': contour_data.metadata.datum
                },
                'contours': []
            }

            # Convert contours
            for contour in contour_data.contours:
                contour_dict = {
                    'elevation': contour.elevation,
                    'points': contour.points.tolist(),
                    'is_closed': contour.is_closed
                }
                data_dict['contours'].append(contour_dict)

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)

        except PermissionError:
            raise FileOperationError(f"Permission denied: {file_path}")
        except Exception as e:
            raise FileOperationError(f"Failed to save contour data to {file_path}: {e}")

    def validate_file_structure(self, file_path: Union[str, Path]) -> bool:
        """
        Validate file structure without fully parsing.

        Args:
            file_path: Path to the contour file

        Returns:
            True if file structure is valid
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return False

            if not self.is_file_supported(file_path):
                return False

            # Try to parse JSON structure
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check required top-level keys
            if not isinstance(data, dict):
                return False

            required_keys = ['metadata', 'contours']
            for key in required_keys:
                if key not in data:
                    return False

            # Basic structure validation
            if not isinstance(data['metadata'], dict):
                return False

            if not isinstance(data['contours'], list):
                return False

            return True

        except Exception:
            return False