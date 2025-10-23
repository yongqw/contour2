# Data Model: Terrain Tunneling Calculator

**Purpose**: Define data structures and relationships for terrain tunneling application
**Created**: 2025-10-20
**Feature**: Terrain Tunneling Calculator

## Core Entities

### ContourData

Represents terrain elevation data from contour files.

**Fields**:
```python
@dataclass
class ContourData:
    metadata: ContourMetadata
    contours: List[ContourLine]
    bounds: BoundingBox
    coordinate_system: CoordinateSystem

    def validate(self) -> bool: ...
    def get_elevation_at(self, x: float, y: float) -> float: ...
    def get_bounds(self) -> BoundingBox: ...
```

**Validation Rules**:
- Elevation values must be numeric and within reasonable ranges (-1000m to 10000m)
- Contour lines must be closed (start point equals end point)
- Points must have at least 3 coordinates per contour line
- No self-intersecting contour lines allowed

**State Transitions**:
- `Raw` → `Validated` → `Triangulated` → `Visualized`

### ContourLine

Single elevation contour with coordinate points.

**Fields**:
```python
@dataclass
class ContourLine:
    elevation: float
    points: np.ndarray  # Shape: (n, 2) for [x, y] coordinates
    is_closed: bool = True

    def get_length(self) -> float: ...
    def get_area(self) -> float: ...
    def contains_point(self, x: float, y: float) -> bool: ...
```

**Validation Rules**:
- Minimum 3 points for valid closed contour
- Elevation must be consistent across all points
- Points must be ordered (clockwise or counter-clockwise)

### TerrainMesh

Triangulated 3D surface generated from contour data.

**Fields**:
```python
@dataclass
class TerrainMesh:
    vertices: np.ndarray      # Shape: (n, 3) for [x, y, z]
    triangles: np.ndarray     # Shape: (m, 3) for vertex indices
    elevation_data: np.ndarray # Shape: (n,) for z values
    bounds: BoundingBox

    def calculate_volume(self) -> float: ...
    def get_surface_area(self) -> float: ...
    def interpolate_at(self, x: float, y: float) -> float: ...
```

**Validation Rules**:
- Vertices must be within original contour bounds
- Triangles must not be degenerate (area > 0)
- Mesh must be watertight (no holes)
- Triangle quality metrics must meet minimum standards

### TunnelGeometry

Represents tunnel path and cross-section geometry.

**Fields**:
```python
@dataclass
class TunnelGeometry:
    start_point: np.ndarray   # Shape: (2,) for [x, y]
    end_point: np.ndarray     # Shape: (2,) for [x, y]
    radius: float
    cross_section_type: CrossSectionType
    path_points: np.ndarray   # Interpolated path points

    def get_length(self) -> float: ...
    def get_volume(self, terrain_mesh: TerrainMesh) -> float: ...
    def get_cross_section_area(self) -> float: ...
```

**Validation Rules**:
- Radius must be positive and reasonable for drivable tunnel (1m to 10m)
- Start and end points must be within terrain bounds
- Tunnel path must not exceed maximum reasonable length (1000m)
- Cross-section must be semi-circular as specified

### TunnelPath

Linear path definition for tunnel routing.

**Fields**:
```python
@dataclass
class TunnelPath:
    waypoints: List[np.ndarray]  # List of [x, y] coordinates
    interpolated_points: np.ndarray
    total_length: float

    def add_waypoint(self, point: np.ndarray) -> None: ...
    def interpolate(self, resolution: float = 1.0) -> np.ndarray: ...
    def get_elevation_profile(self, terrain_mesh: TerrainMesh) -> np.ndarray: ...
```

**Validation Rules**:
- Minimum 2 waypoints (start and end)
- Waypoints must be within terrain bounds
- Path must not self-intersect
- Minimum segment length to avoid numerical issues

### VolumeCalculation

Excavation volume calculation results.

**Fields**:
```python
@dataclass
class VolumeCalculation:
    total_volume: float
    tunnel_volume: float
    excavation_zones: List[ExcavationZone]
    accuracy_estimate: float
    calculation_method: str

    def get_summary(self) -> dict: ...
    def export_to_csv(self, filename: str) -> None: ...
```

**Validation Rules**:
- Volume must be positive and reasonable (>0 cubic meters)
- Accuracy estimate must be within 1% requirement
- Calculation method must be documented
- Results must be reproducible

## Supporting Data Structures

### BoundingBox

Geographic bounds for spatial operations.

```python
@dataclass
class BoundingBox:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float = -np.inf
    max_z: float = np.inf

    def contains_point(self, point: np.ndarray) -> bool: ...
    def get_area(self) -> float: ...
    def expand(self, margin: float) -> 'BoundingBox': ...
```

### ContourMetadata

Metadata for contour files.

```python
@dataclass
class ContourMetadata:
    name: str
    units: str = "meters"
    coordinate_system: str = "local"
    datum: str = "unknown"
    created_date: Optional[datetime] = None
    source: str = "generated"

    def validate(self) -> bool: ...
```

### VisualizationState

3D view and animation state management.

```python
@dataclass
class VisualizationState:
    camera_position: np.ndarray
    camera_target: np.ndarray
    zoom_level: float
    rotation_angles: np.ndarray
    show_tunnel: bool = True
    show_terrain: bool = True
    animation_progress: float = 0.0

    def reset_view(self) -> None: ...
    def set_camera_view(self, view_type: str) -> None: ...
```

### ExcavationZone

Geographic zone with volume calculation details.

```python
@dataclass
class ExcavationZone:
    bounds: BoundingBox
    volume: float
    rock_type: str = "unknown"
    density: float = 2000.0  # kg/m³ default

    def get_mass(self) -> float: ...
    def get_cost_estimate(self, unit_cost: float) -> float: ...
```

## Enums and Constants

### CrossSectionType

```python
class CrossSectionType(Enum):
    SEMICIRCULAR = "semicircular"
    CIRCULAR = "circular"
    HORSESHOE = "horseshoe"
    RECTANGULAR = "rectangular"
```

### CoordinateSystem

```python
class CoordinateSystem(Enum):
    LOCAL = "local"
    UTM = "utm"
    LAT_LON = "lat_lon"
    STATE_PLANE = "state_plane"
```

### Validation Constants

```python
class ValidationConstants:
    MIN_ELEVATION = -1000.0  # meters
    MAX_ELEVATION = 10000.0  # meters
    MIN_TUNNEL_RADIUS = 1.0  # meters
    MAX_TUNNEL_RADIUS = 10.0  # meters
    MAX_TUNNEL_LENGTH = 1000.0  # meters
    MIN_CONTOUR_POINTS = 3
    MAX_MEMORY_USAGE = 500 * 1024 * 1024  # 500MB in bytes
    TRIANGULATION_TIMEOUT = 2.0  # seconds
```

## Data Relationships

### Entity Relationship Diagram

```
ContourData (1) -----> (N) ContourLine
    |
    v
TerrainMesh (1) -----> (N) Triangle
    |
    +----> (1) VolumeCalculation
    |
    v
TunnelGeometry (1) -----> (1) TunnelPath
    |
    +----> (N) ExcavationZone
```

### Key Relationships

1. **ContourData → TerrainMesh**: One-to-one relationship through triangulation
2. **TunnelGeometry → TerrainMesh**: Many-to-one for volume calculations
3. **VolumeCalculation → ExcavationZone**: One-to-many for zoned analysis
4. **TunnelGeometry → TunnelPath**: One-to-one composition

## Data Validation Framework

### Validation Interface

```python
class Validatable:
    def validate(self) -> ValidationResult: ...

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def raise_if_invalid(self) -> None: ...
```

### Validation Rules Engine

```python
class ValidationRule:
    def __init__(self, name: str, condition: Callable[[Any], bool], error_message: str):
        self.name = name
        self.condition = condition
        self.error_message = error_message

    def apply(self, entity: Any) -> Optional[str]: ...

class ValidationEngine:
    def __init__(self):
        self.rules: Dict[type, List[ValidationRule]] = {}

    def add_rule(self, entity_type: type, rule: ValidationRule) -> None: ...
    def validate_entity(self, entity: Any) -> ValidationResult: ...
```

## Serialization Formats

### JSON Schema for Contour Files

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "units": {"type": "string", "enum": ["meters", "feet"]},
        "coordinate_system": {"type": "string"},
        "datum": {"type": "string"},
        "created_date": {"type": "string", "format": "date-time"},
        "source": {"type": "string"}
      },
      "required": ["name"]
    },
    "contours": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "elevation": {"type": "number"},
          "points": {
            "type": "array",
            "items": {
              "type": "array",
              "items": {"type": "number"},
              "minItems": 2,
              "maxItems": 2
            },
            "minItems": 3
          }
        },
        "required": ["elevation", "points"]
      }
    }
  },
  "required": ["metadata", "contours"]
}
```

### Export Formats

1. **STL Format**: 3D mesh export for CAD software
2. **CSV Format**: Volume calculation results
3. **PNG/SVG**: 2D/3D visualization images
4. **JSON**: Complete project state for reproducibility

## Performance Considerations

### Memory Management

- Use numpy arrays for efficient storage of coordinate data
- Implement streaming processing for large contour files
- Memory pooling for frequent geometric calculations
- Garbage collection optimization for large temporary objects

### Computational Efficiency

- Vectorized operations using numpy for coordinate transformations
- Spatial indexing for fast point location queries
- Cached triangulation results for repeated calculations
- Lazy evaluation for expensive geometric operations

### Scalability Strategies

- Progressive mesh generation for large terrains
- Level-of-detail rendering for visualization
- Background processing for heavy calculations
- Data pagination for memory-constrained environments