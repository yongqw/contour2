<!--
Sync Impact Report:
- Version change: 0.0.0 → 1.0.0 (initial adoption)
- Modified principles: All 5 principles newly defined
- Added sections: Code Quality Standards, Performance & Usability Requirements, Development Workflow
- Removed sections: None (template placeholders replaced)
- Templates requiring updates: ✅ plan-template.md (Constitution Check aligned), ✅ spec-template.md (measurable outcomes aligned), ✅ tasks-template.md (testing discipline aligned)
- Follow-up TODOs: None
-->

# Contour2 Constitution

## Core Principles

### I. Code Quality Excellence
All code MUST follow Python best practices with type hints, docstrings, and consistent formatting. Every module MUST be self-contained with clear interfaces and comprehensive error handling. Code reviews MUST verify adherence to PEP 8, type safety, and architectural consistency before merge.

### II. Test-First Development (NON-NEGOTIABLE)
Tests MUST be written before implementation and MUST fail initially. All 3D computations, terrain processing, and tunnel calculations MUST have comprehensive unit tests with numerical validation. Integration tests MUST validate end-to-end workflows from contour file input to 3D visualization output.

### III. User Experience Consistency
All visualizations MUST use consistent coordinate systems, color schemes, and interaction patterns. The 2D contour view and 3D terrain/tunnel rendering MUST maintain spatial coherence. User interactions (point selection, tunnel routing) MUST provide immediate visual feedback with clear state indicators.

### IV. Performance & Numerical Accuracy
Triangulation and volume calculations MUST complete within 2 seconds for terrain files up to 10,000 contour points. All geometric computations MUST maintain numerical precision with appropriate error bounds. 3D rendering MUST achieve smooth interaction (30+ FPS) for models up to 50,000 triangles.

### V. Data Format Standards
Contour files MUST use documented format with validation. All generated outputs (triangulation files, volume calculations, 3D models) MUST be version-controlled and reproducible. File operations MUST include proper error handling and progress indication for large datasets.

## Code Quality Standards

### Python Requirements
- Python 3.11+ with strict type checking enabled
- All public functions MUST have type hints and comprehensive docstrings
- Use numpy for numerical computations, matplotlib for 2D visualization
- 3D rendering MUST use matplotlib or plotly for compatibility

### Documentation Standards
- All algorithms MUST be documented with complexity analysis
- Mathematical formulas MUST include proper notation and explanations
- Code comments MUST explain geometric reasoning and coordinate transformations

## Performance & Usability Requirements

### Computational Performance
- Triangulation: O(n log n) or better for n contour points
- Volume calculation: MUST handle complex tunnel geometries efficiently
- Memory usage: MUST stay below 500MB for typical terrain datasets

### User Interface Requirements
- 2D contour view: MUST support zoom, pan, and point selection with visual feedback
- 3D visualization: MUST support rotation, zoom, and tunnel highlighting
- Progress indication: MUST show progress for computations exceeding 1 second

### Accuracy Requirements
- Volume calculations: MUST be accurate within 1% for validation datasets
- Coordinate transformations: MUST preserve geometric relationships
- Tunnel-path intersection: MUST correctly handle terrain-tunnel intersections

## Development Workflow

### Review Process
- All PRs MUST require at least one code review approval
- Tests MUST pass at 100% coverage for computational modules
- Performance benchmarks MUST be included for significant algorithm changes
- Documentation updates MUST accompany all API changes

### Quality Gates
- Unit tests MUST achieve 90%+ line coverage
- Integration tests MUST validate contour-to-3D workflow
- Performance tests MUST verify 2-second computation limit
- Code quality tools (black, flake8, mypy) MUST pass without warnings

## Governance

This constitution supersedes all other development practices. Amendments require:
- Documentation of proposed changes with rationale
- Team approval through consensus process
- Migration plan for existing code compliance
- Version increment according to semantic versioning rules

All feature development MUST reference this constitution for compliance verification. Use project quickstart.md for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2025-10-20 | **Last Amended**: 2025-10-20