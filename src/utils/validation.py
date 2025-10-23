"""
Validation framework for Terrain Tunneling Calculator.

This module provides validation utilities, result classes, and constants
for ensuring data integrity and business rule compliance.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    message: str
    severity: ValidationSeverity
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, message: str, severity: ValidationSeverity,
                  field: Optional[str] = None, value: Optional[Any] = None,
                  suggestion: Optional[str] = None) -> None:
        """Add a validation issue."""
        issue = ValidationIssue(
            message=message,
            severity=severity,
            field=field,
            value=value,
            suggestion=suggestion
        )
        self.issues.append(issue)

        # Update validity based on severity
        if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False

    def get_errors(self) -> List[ValidationIssue]:
        """Get only error and critical issues."""
        return [issue for issue in self.issues
                if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get only warning issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]

    def get_info(self) -> List[ValidationIssue]:
        """Get only info issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.INFO]

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.get_errors()) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.get_warnings()) > 0

    def get_summary(self) -> str:
        """Get a summary of validation results."""
        error_count = len(self.get_errors())
        warning_count = len(self.get_warnings())
        info_count = len(self.get_info())

        if error_count > 0:
            return f"❌ Validation failed: {error_count} error(s), {warning_count} warning(s)"
        elif warning_count > 0:
            return f"⚠️ Validation passed with warnings: {warning_count} warning(s)"
        else:
            return f"✅ Validation passed: {info_count} info message(s)"


class ValidationConstants:
    """Constants for validation rules."""

    # Elevation limits (meters)
    MIN_ELEVATION = -1000.0
    MAX_ELEVATION = 10000.0

    # Tunnel constraints (meters)
    MIN_TUNNEL_RADIUS = 1.0
    MAX_TUNNEL_RADIUS = 10.0
    MIN_TUNNEL_LENGTH = 0.1
    MAX_TUNNEL_LENGTH = 1000.0

    # Contour constraints
    MIN_CONTOUR_POINTS = 3
    MAX_CONTOUR_POINTS = 10000

    # Coordinate limits (reasonable bounds)
    MIN_COORDINATE = -1_000_000.0
    MAX_COORDINATE = 1_000_000.0

    # Performance limits
    MAX_MEMORY_USAGE_MB = 500
    MAX_TRIANGLES_FOR_INTERACTIVE_RENDERING = 50000
    TRIANGULATION_TIMEOUT_SECONDS = 2.0

    # File size limits
    MAX_CONTOUR_FILE_SIZE_MB = 100
    MAX_EXPORT_FILE_SIZE_MB = 50


class ValidationRule:
    """A single validation rule."""

    def __init__(self, name: str, condition: Callable[[Any], bool],
                 error_message: str, severity: ValidationSeverity = ValidationSeverity.ERROR,
                 suggestion: Optional[str] = None):
        self.name = name
        self.condition = condition
        self.error_message = error_message
        self.severity = severity
        self.suggestion = suggestion

    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> Optional[ValidationIssue]:
        """Validate a value against this rule."""
        try:
            if not self.condition(value):
                return ValidationIssue(
                    message=self.error_message,
                    severity=self.severity,
                    value=value,
                    suggestion=self.suggestion
                )
        except Exception as e:
            return ValidationIssue(
                message=f"Validation error: {str(e)}",
                severity=ValidationSeverity.ERROR,
                value=value
            )

        return None


class ValidationFramework:
    """Main validation framework for coordinating validation rules."""

    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {}

    def add_rule(self, category: str, rule: ValidationRule) -> None:
        """Add a validation rule to a category."""
        if category not in self.rules:
            self.rules[category] = []
        self.rules[category].append(rule)

    def add_rules(self, category: str, rules: List[ValidationRule]) -> None:
        """Add multiple validation rules to a category."""
        if category not in self.rules:
            self.rules[category] = []
        self.rules[category].extend(rules)

    def validate_entity(self, entity: Any, entity_type: str,
                        context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate an entity against all applicable rules."""
        result = ValidationResult(is_valid=True, context=context or {})

        if entity_type not in self.rules:
            result.add_issue(
                message=f"No validation rules found for entity type: {entity_type}",
                severity=ValidationSeverity.WARNING
            )
            return result

        for rule in self.rules[entity_type]:
            issue = rule.validate(entity, context)
            if issue:
                result.add_issue(
                    message=issue.message,
                    severity=issue.severity,
                    suggestion=issue.suggestion
                )

        return result

    def validate_contour_data(self, contour_data) -> ValidationResult:
        """Validate ContourData object."""
        result = ValidationResult(is_valid=True)

        # Use the contour data's built-in validation
        try:
            is_valid = contour_data.validate()
            if not is_valid:
                result.add_issue(
                    message="Contour data validation failed",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Check contour data structure and values"
                )
        except Exception as e:
            result.add_issue(
                message=f"Validation error: {str(e)}",
                severity=ValidationSeverity.ERROR,
                suggestion="Check contour data for consistency"
            )

        return result

    def validate_field(self, value: Any, field_name: str,
                       entity_type: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate a single field against applicable rules."""
        result = ValidationResult(is_valid=True, context=context or {})

        if entity_type not in self.rules:
            result.add_issue(
                message=f"No validation rules found for entity type: {entity_type}",
                severity=ValidationSeverity.WARNING
            )
            return result

        for rule in self.rules[entity_type]:
            issue = rule.validate(value, context)
            if issue:
                result.add_issue(
                    message=issue.message,
                    severity=issue.severity,
                    field=field_name,
                    value=value,
                    suggestion=issue.suggestion
                )

        return result


# Built-in validation rules for common use cases
class CommonValidationRules:
    """Common validation rules for terrain tunneling calculator."""

    @staticmethod
    def elevation_rule() -> ValidationRule:
        """Rule for validating elevation values."""
        return ValidationRule(
            name="elevation_range",
            condition=lambda x: isinstance(x, (int, float)) and ValidationConstants.MIN_ELEVATION <= x <= ValidationConstants.MAX_ELEVATION,
            error_message=f"Elevation must be between {ValidationConstants.MIN_ELEVATION} and {ValidationConstants.MAX_ELEVATION} meters",
            suggestion="Check the elevation units and values in your contour data"
        )

    @staticmethod
    def coordinate_rule() -> ValidationRule:
        """Rule for validating coordinate values."""
        return ValidationRule(
            name="coordinate_range",
            condition=lambda x: isinstance(x, (int, float)) and ValidationConstants.MIN_COORDINATE <= x <= ValidationConstants.MAX_COORDINATE,
            error_message=f"Coordinate values must be reasonable",
            suggestion="Check the coordinate system and projection in your data"
        )

    @staticmethod
    def tunnel_radius_rule() -> ValidationRule:
        """Rule for validating tunnel radius."""
        return ValidationRule(
            name="tunnel_radius",
            condition=lambda x: isinstance(x, (int, float)) and ValidationConstants.MIN_TUNNEL_RADIUS <= x <= ValidationConstants.MAX_TUNNEL_RADIUS,
            error_message=f"Tunnel radius must be between {ValidationConstants.MIN_TUNNEL_RADIUS} and {ValidationConstants.MAX_TUNNEL_RADIUS} meters",
            suggestion="Ensure the tunnel radius is appropriate for vehicle passage"
        )

    @staticmethod
    def non_empty_string_rule() -> ValidationRule:
        """Rule for validating non-empty strings."""
        return ValidationRule(
            name="non_empty_string",
            condition=lambda x: isinstance(x, str) and len(x.strip()) > 0,
            error_message="Value cannot be empty",
            suggestion="Provide a valid string value"
        )

    @staticmethod
    def positive_number_rule() -> ValidationRule:
        """Rule for validating positive numbers."""
        return ValidationRule(
            name="positive_number",
            condition=lambda x: isinstance(x, (int, float)) and x > 0,
            error_message="Value must be a positive number",
            suggestion="Check the input value and ensure it's greater than zero"
        )

    @staticmethod
    def array_shape_rule(min_length: int = 1, expected_shape: Optional[tuple] = None) -> ValidationRule:
        """Rule for validating numpy array shapes."""
        def condition(arr):
            if not isinstance(arr, np.ndarray):
                return False
            if len(arr.shape) < min_length:
                return False
            if expected_shape and len(arr.shape) != len(expected_shape):
                return False
            if expected_shape:
                for i, expected_dim in enumerate(expected_shape):
                    if expected_dim != -1 and arr.shape[i] != expected_dim:
                        return False
            return True

        return ValidationRule(
            name="array_shape",
            condition=condition,
            error_message=f"Array must have correct shape (min {min_length} dimensions" +
                       (f", expected: {expected_shape}" if expected_shape else ")"),
            suggestion="Ensure the array has the correct number of dimensions and size"
        )