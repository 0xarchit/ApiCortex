$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (Test-Path ".venv\Scripts\Activate.ps1") {
  & ".\.venv\Scripts\Activate.ps1"
}

Set-Location "dbmanage"

if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
  throw "bun is required to run db sync scripts."
}

bun install
bun run db:sync
