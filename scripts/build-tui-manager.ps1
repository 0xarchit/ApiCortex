# Build script for ApiCortex TUI Manager
# This script compiles the Go TUI manager into a Windows executable

$ErrorActionPreference = "Stop"

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Join-Path $scriptDir "tui-manager"
$buildDir = Join-Path $projectDir "build"
$outputPath = Join-Path $buildDir "apicortex-manager.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ApiCortex TUI Manager - Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Go is installed
try {
    $goVersion = go version
    Write-Host "Found Go: $goVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Go is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Go from https://golang.org/dl/" -ForegroundColor Yellow
    exit 1
}

# Create build directory if it doesn't exist
if (!(Test-Path $buildDir)) {
    Write-Host "Creating build directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

# Change to project directory
Write-Host "Building in: $projectDir" -ForegroundColor Cyan
Set-Location $projectDir

# Download dependencies
Write-Host "Downloading dependencies..." -ForegroundColor Yellow
go mod tidy

# Build for Windows
Write-Host "Compiling for Windows..." -ForegroundColor Yellow
$env:GOOS = "windows"
$env:GOARCH = "amd64"

go build -o $outputPath -ldflags="-s -w" .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[+] Build successful!" -ForegroundColor Green
    Write-Host "  Output: $outputPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To run:" -ForegroundColor Yellow
    Write-Host "  $outputPath" -ForegroundColor White
    Write-Host ""
    Write-Host "Or copy to project root for easy access" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "[-] Build failed!" -ForegroundColor Red
    exit 1
}
