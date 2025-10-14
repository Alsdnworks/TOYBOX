# JointPoint LineMerge

A Python tool for merging lines at joint points using geospatial operations.

## Description

JointPoint LineMerge is a geospatial processing tool that merges line segments at specified joint points. It uses advanced geometric operations to combine connected line segments while maintaining spatial accuracy and handling various edge cases.
The optimal tool for solving problems such as... : https://gis.stackexchange.com/questions/194486/arcgis-10-3-how-to-merge-lines-divided-by-junction-points

## Features

- **Line Merging**: Automatically merge connected line segments at joint points
- **Tolerance-based Processing**: Configure tolerance for geometric operations
- **Error Handling**: Comprehensive error logging and validation
- **Multiple Format Support**: Works with various geospatial file formats
- **Validation**: Input validation for geometries and coordinate reference systems
- **Performance Optimized**: Efficient processing of large datasets

## Installation

### Using UV (Recommended)

```bash
# Install UV if you haven't already
pip install uv

# Clone the repository
git clone https://github.com/Alsdnworks/TOYBOX.git
cd TOYBOX/JOINTPOINTLINEMERGE

# Install dependencies using UV
uv sync

# Activate the virtual environment
uv shell
```

### Traditional Installation

```bash
pip install pandas geopandas shapely pyproj matplotlib numpy
```

## Usage

### Command Line

```bash
# Basic usage
python jointpointLinemerge.py --lines lines.shp --points points.shp --out-lines merged_lines.shp --out-errors errors.shp --tol 1.0

# With additional validation
python jointpointLinemerge.py --lines lines.shp --points points.shp --out-lines merged_lines.shp --out-errors errors.shp --tol 1.0 --point-id-col "ID" --val-chk-col "status,type"
```

### Parameters

- `--lines`: Path to input lines file (shapefile, GeoJSON, etc.)
- `--points`: Path to input points file
- `--out-lines`: Path for output merged lines file
- `--out-errors`: Path for output errors file
- `--tol`: Tolerance for geometric operations (float)
- `--point-id-col`: (Optional) Column name for point IDs
- `--val-chk-col`: (Optional) Columns to validate (comma-separated)

### Python API

```python
from jointpointLinemerge import Param, run
import geopandas as gpd

# Create parameter object
params = Param(
    lines_path="lines.shp",
    points_path="points.shp", 
    out_lines_path="merged_lines.shp",
    out_errors_path="errors.shp",
    tol=1.0,
    point_id_col="ID",
    val_chk_col=("status", "type")
)

# Run the merge process
run(params)
```

## Development

### Setting up Development Environment

```bash
# Using UV
uv sync --extra dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=jointpointLinemerge

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy jointpointLinemerge.py
```

### Testing

The project includes comprehensive tests covering:

- Input validation for various edge cases
- Geometric operations for line merging  
- Error handling and logging
- Integration testing with file I/O
- Performance benchmarks
- Complex network scenarios (T-intersections, crossroads, star patterns)

Run the test suite:

```bash
python test_jointpointLinemerge.py
```

This will generate a detailed visualization (`test_results_visualization.png`) showing test results and performance metrics.

## Dependencies

- **pandas**: Data manipulation and analysis
- **geopandas**: Geospatial data processing
- **shapely**: Geometric operations
- **pyproj**: Coordinate system transformations
- **matplotlib**: Plotting and visualization
- **numpy**: Numerical computing

## Development Dependencies

- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Issues

If you encounter any issues or have questions, please file an issue on the GitHub repository.
