#!/usr/bin/env pwsh
# Terrain Tunneling Calculator - Environment Setup Script
# Created: 2025-10-20

param(
    [switch]$Dev,
    [switch]$Clean,
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Write-Output "Terrain Tunneling Calculator - Environment Setup"
    Write-Output ""
    Write-Output "Usage: ./scripts/setup_env.ps1 [options]"
    Write-Output ""
    Write-Output "Options:"
    Write-Output "  -Dev      Install development dependencies"
    Write-Output "  -Clean    Clean existing environment before setup"
    Write-Output "  -Help     Show this help message"
    Write-Output ""
    Write-Output "Examples:"
    Write-Output "  ./scripts/setup_env.ps1                # Basic setup"
    Write-Output "  ./scripts/setup_env.ps1 -Dev           # Full development setup"
    Write-Output "  ./scripts/setup_env.ps1 -Clean -Dev    # Clean development setup"
    exit 0
}

Write-Output "🚀 Setting up Terrain Tunneling Calculator development environment..."

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Output "✅ Found Python: $pythonVersion"
} catch {
    Write-Output "❌ Python not found. Please install Python 3.11+ from https://python.org"
    exit 1
}

# Check Python version compatibility
$versionOutput = python --version 2>&1
if ($versionOutput -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Output "❌ Python 3.11+ required. Found version $major.$minor"
        exit 1
    }
    Write-Output "✅ Python version compatible"
} else {
    Write-Output "⚠️ Could not determine Python version, proceeding anyway..."
}

# Clean existing environment if requested
if ($Clean) {
    Write-Output "🧹 Cleaning existing environment..."

    if (Test-Path "venv") {
        Write-Output "Removing existing virtual environment..."
        Remove-Item -Recurse -Force venv
        Write-Output "✅ Virtual environment removed"
    }

    if (Test-Path "build") {
        Remove-Item -Recurse -Force build
    }

    if (Test-Path "dist") {
        Remove-Item -Recurse -Force dist
    }

    # Clean cache directories
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
        Remove-Item -Recurse -Force $_
    }

    Write-Output "✅ Cleanup completed"
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Output "📦 Creating virtual environment..."
    python -m venv venv

    if ($LASTEXITCODE -ne 0) {
        Write-Output "❌ Failed to create virtual environment"
        exit 1
    }
    Write-Output "✅ Virtual environment created"
} else {
    Write-Output "✅ Virtual environment already exists"
}

# Activate virtual environment
Write-Output "🔌 Activating virtual environment..."
& "venv/Scripts/Activate.ps1"

# Upgrade pip
Write-Output "⬆️ Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Install basic requirements
Write-Output "📚 Installing basic requirements..."
python -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Output "❌ Failed to install basic requirements"
    exit 1
}

# Install development dependencies if requested
if ($Dev) {
    Write-Output "🛠️ Installing development dependencies..."
    python -m pip install -e ".[dev,docs]"

    if ($LASTEXITCODE -ne 0) {
        Write-Output "❌ Failed to install development dependencies"
        exit 1
    }
    Write-Output "✅ Development dependencies installed"
}

# Create necessary directories
Write-Output "📁 Creating project directories..."
$directories = @(
    "src",
    "src/models",
    "src/services",
    "src/gui",
    "src/utils",
    "tests",
    "tests/unit",
    "tests/integration",
    "tests/fixtures",
    "data",
    "data/examples",
    "data/exports",
    "docs",
    "logs"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Create __init__.py files for Python packages
$packageDirs = @(
    "src",
    "src/models",
    "src/services",
    "src/gui",
    "src/utils",
    "tests"
)

foreach ($dir in $packageDirs) {
    $initFile = Join-Path $dir "__init__.py"
    if (-not (Test-Path $initFile)) {
        Set-Content -Path $initFile -Value "# Terrain Tunneling Calculator Package"
    }
}

# Create demo contour data
Write-Output "🏔️ Creating demo contour data..."
$demoData = @{
    metadata = @{
        name = "Sample Hill Terrain"
        units = "meters"
        coordinate_system = "local"
        created_date = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        source = "generated"
    }
    contours = @(
        @{
            elevation = 100.0
            points = @(
                @(0.0, 0.0), @(100.0, 0.0), @(100.0, 100.0), @(0.0, 100.0), @(0.0, 0.0)
            )
        },
        @{
            elevation = 110.0
            points = @(
                @(20.0, 20.0), @(80.0, 20.0), @(80.0, 80.0), @(20.0, 80.0), @(20.0, 20.0)
            )
        },
        @{
            elevation = 120.0
            points = @(
                @(35.0, 35.0), @(65.0, 35.0), @(65.0, 65.0), @(35.0, 65.0), @(35.0, 35.0)
            )
        },
        @{
            elevation = 125.0
            points = @(
                @(45.0, 45.0), @(55.0, 45.0), @(55.0, 55.0), @(45.0, 55.0), @(45.0, 45.0)
            )
        }
    )
}

$demoDataJson = $demoData | ConvertTo-Json -Depth 3
Set-Content -Path "data/demo_contour.json" -Value $demoDataJson

# Create configuration file
Write-Output "⚙️ Creating configuration file..."
$config = @{
    app = @{
        name = "Terrain Tunneling Calculator"
        version = "0.1.0"
        debug = $false
    }
    visualization = @{
        default_elevation_colormap = "terrain"
        default_tunnel_color = "#FF6B6B"
        default_terrain_color = "#8B7355"
        animation_fps = 30
    }
    performance = @{
        max_memory_mb = 500
        triangulation_timeout_seconds = 2.0
        max_triangles_for_interactive_rendering = 50000
    }
    validation = @{
        min_elevation = -1000.0
        max_elevation = 10000.0
        min_tunnel_radius = 1.0
        max_tunnel_radius = 10.0
        max_tunnel_length = 1000.0
    }
    paths = @{
        data_dir = "data"
        exports_dir = "data/exports"
        cache_dir = "cache"
        log_dir = "logs"
    }
}

$configJson = $config | ConvertTo-Json -Depth 3
Set-Content -Path "config.json" -Value $configJson

# Create .gitignore file
Write-Output "📝 Creating .gitignore file..."
$gitignore = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
.venv/
.env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
*.log
cache/
logs/
data/exports/*.json
data/exports/*.csv
data/exports/*.stl
data/exports/*.obj
temp/
tmp/

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Documentation
docs/_build/
.sphinx/
"@

Set-Content -Path ".gitignore" -Value $gitignore

# Create development scripts
Write-Output "📜 Creating development scripts..."

# Run application script
$runScript = @"
#!/usr/bin/env pwsh
# Run Terrain Tunneling Calculator

param(
    [string]$File,
    [switch]$Debug,
    [switch]$Help
)

if ($Help) {
    Write-Output "Usage: ./scripts/run.ps1 [options]"
    Write-Output ""
    Write-Output "Options:"
    Write-Output "  -File <path>    Load specific contour file"
    Write-Output "  -Debug          Enable debug mode"
    Write-Output "  -Help           Show this help"
    exit 0
}

# Activate virtual environment
& "venv/Scripts/Activate.ps1"

# Set environment variables
`$env:PYTHONPATH = "`$PWD/src"
if (`$Debug) {
    `$env:CONTOUR2_DEBUG = "true"
}

# Run the application
if (`$File) {
    python src/main.py --file "`$File"
} else {
    python src/main.py
}
"@

Set-Content -Path "scripts/run.ps1" -Value $runScript

# Test runner script
$testScript = @"
#!/usr/bin/env pwsh
# Run tests for Terrain Tunneling Calculator

param(
    [string]$Target = "all",
    [switch]$Coverage,
    [switch]$Verbose,
    [switch]$Help
)

if (`$Help) {
    Write-Output "Usage: ./scripts/test.ps1 [options]"
    Write-Output ""
    Write-Output "Options:"
    Write-Output "  -Target <type>    Test target: all, unit, integration"
    Write-Output "  -Coverage        Generate coverage report"
    Write-Output "  -Verbose         Verbose output"
    Write-Output "  -Help            Show this help"
    exit 0
}

# Activate virtual environment
& "venv/Scripts/Activate.ps1"

# Build pytest command
`$pytestArgs = @()

if (`$Target -eq "unit") {
    `$pytestArgs += "tests/unit/"
} elseif (`$Target -eq "integration") {
    `$pytestArgs += "tests/integration/"
} else {
    `$pytestArgs += "tests/"
}

if (`$Coverage) {
    `$pytestArgs += "--cov=src", "--cov-report=html", "--cov-report=term"
}

if (`$Verbose) {
    `$pytestArgs += "-v"
}

# Run tests
Write-Output "🧪 Running tests..."
python -m pytest `$pytestArgs

if (`$LASTEXITCODE -eq 0) {
    Write-Output "✅ All tests passed!"
} else {
    Write-Output "❌ Some tests failed"
    exit 1
}
"@

Set-Content -Path "scripts/test.ps1" -Value $testScript

Write-Output "🎉 Environment setup completed successfully!"
Write-Output ""
Write-Output "Next steps:"
Write-Output "1. Activate the environment: venv\Scripts\Activate"
Write-Output "2. Run the application: .\scripts\run.ps1"
Write-Output "3. Run tests: .\scripts\test.ps1 -Coverage"
Write-Output ""
Write-Output "For development: .\scripts\setup_env.ps1 -Dev"