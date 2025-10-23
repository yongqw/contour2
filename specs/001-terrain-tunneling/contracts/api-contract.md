# API Contract: Terrain Tunneling Calculator

**Purpose**: Define internal API contracts for terrain tunneling application services
**Created**: 2025-10-20
**Feature**: Terrain Tunneling Calculator

## Service Interfaces

### Contour Parser Service

#### load_contour_file(file_path: str) -> ContourData

**Description**: Load and parse contour data from JSON file

**Parameters**:
- `file_path` (str): Path to contour file (.json)

**Returns**: `ContourData` - Parsed contour data with validation

**Raises**:
- `FileNotFoundError`: File does not exist
- `InvalidContourFileError`: File format is invalid
- `ValidationError`: Contour data fails validation rules

**Example**:
```python
contour_data = contour_parser.load_contour_file("data/terrain.json")
# Returns validated ContourData object
```

#### validate_contour_data(contour_data: ContourData) -> ValidationResult

**Description**: Validate contour data against business rules

**Parameters**:
- `contour_data` (ContourData): Contour data to validate

**Returns**: `ValidationResult` - Validation outcome with errors/warnings

**Validation Rules**:
- Elevation ranges: -1000m to 10000m
- Minimum 3 points per contour line
- Closed contours (start == end point)
- No self-intersections
- Points within reasonable coordinate bounds

### Triangulation Service

#### generate_terrain_mesh(contour_data: ContourData) -> TerrainMesh

**Description**: Generate triangulated 3D terrain mesh from contour data

**Parameters**:
- `contour_data` (ContourData): Validated contour data

**Returns**: `TerrainMesh` - Triangulated 3D surface

**Performance Requirements**:
- Complete within 2 seconds for 10,000 contour points
- Memory usage under 500MB
- O(n log n) time complexity

**Algorithm**: scipy.spatial.Delaunay with point reduction optimization

**Example**:
```python
terrain_mesh = triangulation.generate_terrain_mesh(contour_data)
# Returns TerrainMesh with vertices, triangles, and elevation data
```

#### optimize_mesh(mesh: TerrainMesh, quality_threshold: float = 0.1) -> TerrainMesh

**Description**: Optimize triangulated mesh for better performance

**Parameters**:
- `mesh` (TerrainMesh): Input mesh to optimize
- `quality_threshold` (float): Minimum triangle quality (0.0 to 1.0)

**Returns**: `TerrainMesh` - Optimized mesh with reduced triangles

### Tunnel Geometry Service

#### create_tunnel_geometry(start_point: np.ndarray, end_point: np.ndarray, radius: float) -> TunnelGeometry

**Description**: Create tunnel geometry from user-defined parameters

**Parameters**:
- `start_point` (np.ndarray): Start coordinates [x, y]
- `end_point` (np.ndarray): End coordinates [x, y]
- `radius` (float): Tunnel radius in meters

**Returns**: `TunnelGeometry` - Complete tunnel geometry definition

**Validation**:
- Start/end points within terrain bounds
- Radius between 1m and 10m
- Path length under 1000m

**Example**:
```python
tunnel = tunnel_service.create_tunnel_geometry(
    start_point=np.array([100.0, 200.0]),
    end_point=np.array([300.0, 400.0]),
    radius=3.5
)
```

#### calculate_excavation_volume(tunnel: TunnelGeometry, terrain: TerrainMesh) -> VolumeCalculation

**Description**: Calculate excavation volume for tunnel through terrain

**Parameters**:
- `tunnel` (TunnelGeometry): Tunnel geometry definition
- `terrain` (TerrainMesh): Triangulated terrain surface

**Returns**: `VolumeCalculation` - Volume calculation results with accuracy estimates

**Accuracy Requirements**: Within 1% of actual volume

**Algorithm**: Tetrahedral decomposition of tunnel-terrain intersection

### Visualization Services

#### generate_2d_contour_plot(contour_data: ContourData, tunnel_path: Optional[TunnelPath] = None) -> Figure

**Description**: Generate 2D contour visualization with optional tunnel overlay

**Parameters**:
- `contour_data` (ContourData): Contour data for visualization
- `tunnel_path` (Optional[TunnelPath]): Tunnel path to overlay

**Returns**: `matplotlib.figure.Figure` - 2D plot figure

**Features**:
- Elevation-based color mapping
- Interactive point selection
- Tunnel path visualization
- Coordinate grid and labels

#### generate_3d_visualization(terrain: TerrainMesh, tunnel: TunnelGeometry) -> Figure

**Description**: Generate 3D visualization of terrain and tunnel

**Parameters**:
- `terrain` (TerrainMesh): Triangulated terrain surface
- `tunnel` (TunnelGeometry): Tunnel geometry to display

**Returns**: `plotly.graph_objects.Figure` - Interactive 3D visualization

**Performance**: 30+ FPS for models up to 50,000 triangles

**Features**:
- Interactive rotation, zoom, pan
- Distinct materials for terrain and tunnel
- Cross-section views
- Measurement tools

#### create_tunnel_animation(tunnel: TunnelGeometry, terrain: TerrainMesh, car_speed: float = 10.0) -> Animation

**Description**: Create animation of car traveling through tunnel

**Parameters**:
- `tunnel` (TunnelGeometry): Tunnel geometry
- `terrain` (TerrainMesh): Terrain surface
- `car_speed` (float): Car speed in m/s

**Returns**: `plotly.graph_objects.Figure` - Animated 3D scene

**Animation Features**:
- Realistic car movement along tunnel path
- Camera following car motion
- Smooth transitions between frames
- Playback controls

### Export Service

#### export_triangulation(mesh: TerrainMesh, format: str, file_path: str) -> bool

**Description**: Export triangulated mesh to various 3D formats

**Parameters**:
- `mesh` (TerrainMesh): Mesh to export
- `format` (str): Export format ("STL", "OBJ", "PLY")
- `file_path` (str): Output file path

**Returns**: `bool` - Success status

**Supported Formats**:
- STL: 3D printing and CAD software
- OBJ: General 3D model format
- PLY: Point cloud and mesh data

#### export_visualization(figure: Figure, format: str, file_path: str) -> bool

**Description**: Export visualization to image format

**Parameters**:
- `figure` (Figure): Visualization figure
- `format` (str): Image format ("PNG", "SVG", "PDF")
- `file_path` (str): Output file path

**Returns**: `bool` - Success status

**Resolution**: High-quality output suitable for reports and presentations

#### export_volume_results(volume_calc: VolumeCalculation, format: str, file_path: str) -> bool

**Description**: Export volume calculation results

**Parameters**:
- `volume_calc` (VolumeCalculation): Volume calculation results
- `format` (str): Export format ("CSV", "JSON", "XLSX")
- `file_path` (str): Output file path

**Returns**: `bool` - Success status

**Content**: Detailed breakdown by excavation zone, accuracy estimates, methodology

## Event System

### User Interaction Events

#### PointSelectedEvent

**Description**: User selected point on 2D contour view

**Payload**:
```python
@dataclass
class PointSelectedEvent:
    x: float
    y: float
    coordinate_system: str
    timestamp: datetime
```

#### TunnelParameterChangedEvent

**Description**: User modified tunnel parameters

**Payload**:
```python
@dataclass
class TunnelParameterChangedEvent:
    parameter_name: str  # "start_point", "end_point", "radius"
    old_value: Any
    new_value: Any
    timestamp: datetime
```

### Computation Events

#### TriangulationCompletedEvent

**Description**: Terrain triangulation completed

**Payload**:
```python
@dataclass
class TriangulationCompletedEvent:
    triangle_count: int
    processing_time: float
    memory_usage: int
    success: bool
    error_message: Optional[str] = None
```

#### VolumeCalculationCompletedEvent

**Description**: Volume calculation completed

**Payload**:
```python
@dataclass
class VolumeCalculationCompletedEvent:
    total_volume: float
    accuracy_estimate: float
    processing_time: float
    excavation_zone_count: int
```

## Error Handling

### Custom Exceptions

```python
class ContourError(Exception):
    """Base class for contour-related errors"""
    pass

class InvalidContourFileError(ContourError):
    """Contour file format is invalid"""
    pass

class TriangulationError(Exception):
    """Triangulation processing failed"""
    pass

class VolumeCalculationError(Exception):
    """Volume calculation failed"""
    pass

class VisualizationError(Exception):
    """3D visualization failed"""
    pass
```

### Error Response Format

```python
@dataclass
class ErrorResponse:
    error_type: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = field(default_factory=datetime.now)
    suggested_action: Optional[str] = None
```

## Performance Contracts

### Response Time Requirements

| Operation | Maximum Time | Typical Time | Dataset Size |
|-----------|--------------|--------------|--------------|
| Load contour file | 5 seconds | 1 second | 10k points |
| Triangulation | 2 seconds | 0.5 seconds | 10k points |
| Volume calculation | 3 seconds | 1 second | Complex geometry |
| 3D rendering | 1 second | 0.3 seconds | 50k triangles |
| Export operations | 10 seconds | 2 seconds | Full model |

### Memory Usage Limits

| Operation | Maximum Memory | Typical Memory | Dataset Size |
|-----------|---------------|----------------|--------------|
| Load contour file | 100MB | 20MB | 10k points |
| Triangulation | 200MB | 50MB | 10k points |
| 3D visualization | 300MB | 100MB | 50k triangles |
| Total application | 500MB | 200MB | Full workflow |

### Concurrency Constraints

- Single-threaded GUI operations (tkinter requirement)
- Background processing for heavy computations
- Thread-safe data structures for shared state
- Event-driven architecture for user interactions

## Integration Points

### File System Integration

**Supported File Formats**:
- Input: JSON contour files
- Output: STL, OBJ, PNG, SVG, CSV, JSON
- Temporary: Binary cache files for performance

**File Path Conventions**:
- Input: `data/contours/*.json`
- Output: `exports/{timestamp}/*.{format}`
- Cache: `cache/{hash}/*.tmp`

### GUI Integration

**Tkinter Integration Points**:
- Matplotlib canvas for 2D plots
- Web browser component for plotly 3D views
- Form widgets for parameter input
- Menu system for file operations

**Event Handling**:
- Mouse click events for point selection
- Keyboard shortcuts for common operations
- Window resize events for responsive layout
- Progress updates for long operations