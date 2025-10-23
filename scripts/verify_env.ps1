#!/usr/bin/env pwsh
# Environment Verification Script for Terrain Tunneling Calculator
# Created: 2025-10-20

param(
    [switch]$Detailed,
    [switch]$Help
)

if ($Help) {
    Write-Output "Usage: ./scripts/verify_env.ps1 [options]"
    Write-Output ""
    Write-Output "Options:"
    Write-Output "  -Detailed    Show detailed verification information"
    Write-Output "  -Help        Show this help message"
    exit 0
}

Write-Output "🔍 Verifying Terrain Tunneling Calculator development environment..."
Write-Output ""

# Check Python version
try {
    $pythonVersion = & "venv/Scripts/python.exe" --version 2>&1
    Write-Output "✅ Python: $pythonVersion"
} catch {
    Write-Output "❌ Python not found or not accessible"
    exit 1
}

# Check virtual environment
if (Test-Path "venv") {
    Write-Output "✅ Virtual environment exists"
} else {
    Write-Output "❌ Virtual environment not found"
    exit 1
}

# Check core dependencies
$corePackages = @("numpy", "scipy", "matplotlib", "plotly")
foreach ($package in $corePackages) {
    try {
        $version = & "venv/Scripts/python.exe" -c "import $package; print($package.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Output "✅ $package : $version"
        } else {
            Write-Output "❌ $package : Not installed"
            exit 1
        }
    } catch {
        Write-Output "❌ $package : Failed to import"
        exit 1
    }
}

# Check project structure
$requiredDirs = @("src", "tests", "data", "scripts", "docs")
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Output "✅ Directory $dir exists"
    } else {
        Write-Output "⚠️ Directory $dir not found"
    }
}

# Check configuration files
$configFiles = @("requirements.txt", "pyproject.toml", "config.json", ".env.example")
foreach ($file in $configFiles) {
    if (Test-Path $file) {
        Write-Output "✅ Config file $file exists"
    } else {
        Write-Output "⚠️ Config file $file not found"
    }
}

# Check demo data
if (Test-Path "data/demo_contour.json") {
    Write-Output "✅ Demo contour data exists"
} else {
    Write-Output "⚠️ Demo contour data not found"
}

# Detailed verification if requested
if ($Detailed) {
    Write-Output ""
    Write-Output "📊 Detailed Environment Information:"
    Write-Output ""

    # Python environment details
    Write-Output "Python Environment:"
    & "venv/Scripts/python.exe" -c "import sys; print('  Executable:', sys.executable); print('  Version:', sys.version); print('  Platform:', sys.platform)"

    # Package versions
    Write-Output ""
    Write-Output "Package Versions:"
    & "venv/Scripts/python.exe" -c "import pkg_resources; installed = [d for d in pkg_resources.working_set]; print('  Installed packages:', len(installed))"

    # Memory test
    Write-Output ""
    Write-Output "Memory Test:"
    & "venv/Scripts/python.exe" -c "import numpy as np; arr = np.random.rand(1000, 1000); print('  NumPy array creation: OK'); print('  Array shape:', arr.shape); print('  Memory usage:', arr.nbytes / 1024 / 1024, 'MB')"

    # SciPy triangulation test
    Write-Output ""
    Write-Output "SciPy Triangulation Test:"
    & "venv/Scripts/python.exe" -c "import numpy as np; from scipy.spatial import Delaunay; points = np.random.rand(10, 2); tri = Delaunay(points); print('  Delaunay triangulation: OK'); print('  Number of triangles:', len(tri.simplices))"

    # Matplotlib test
    Write-Output ""
    Write-Output "Matplotlib Test:"
    & "venv/Scripts/python.exe" -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; fig, ax = plt.subplots(); ax.plot([1, 2, 3], [1, 4, 2]); plt.close(fig); print('  Matplotlib figure creation: OK')"

    # Plotly test
    Write-Output ""
    Write-Output "Plotly Test:"
    & "venv/Scripts/python.exe" -c "import plotly.graph_objects as go; fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[1, 4, 2])); print('  Plotly figure creation: OK'); print('  Figure type:', type(fig).__name__)"

    # JSON validation test
    Write-Output ""
    Write-Output "JSON Validation Test:"
    & "venv/Scripts/python.exe" -c "import json; data = {'test': 'value'}; result = json.dumps(data); parsed = json.loads(result); print('  JSON serialization/deserialization: OK'); print('  Test data:', parsed)"
}

Write-Output ""
Write-Output "🎉 Environment verification completed successfully!"
Write-Output ""
Write-Output "Next steps:"
Write-Output "1. Activate virtual environment: venv\Scripts\Activate"
Write-Output "2. Run the application: .\scripts\run.ps1"
Write-Output "3. Run tests: .\scripts\test.ps1"
Write-Output ""
Write-Output "For development setup: .\scripts\setup_env.ps1 -Dev"