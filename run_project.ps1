param(
    [switch]$SkipInstall,
    [switch]$NoDashboard,
    [int]$Port = 8502
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating .venv..."
    python -m venv .venv
}

$python = Resolve-Path ".\.venv\Scripts\python.exe"

if (-not $SkipInstall) {
    Write-Host "Installing dependencies..."
    & $python -m pip install -r requirements.txt
}

Write-Host "Generating synthetic CMP data..."
& $python ".\src\generate_synthetic_cmp_data.py"

Write-Host "Building feature table and alerts..."
& $python ".\src\build_cmp_feature_table.py"

Write-Host "Generating maintenance alert report..."
& $python ".\src\generate_maintenance_alert_report.py"

Write-Host "Training maintenance risk model..."
& $python ".\src\train_maintenance_risk_model.py"

if ($NoDashboard) {
    Write-Host "Pipeline complete. Dashboard launch skipped."
    exit 0
}

Write-Host "Launching dashboard on http://localhost:$Port ..."
& $python -m streamlit run ".\src\dashboard.py" --server.port $Port
