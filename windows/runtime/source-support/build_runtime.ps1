$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$env:RUSTUP_HOME = Join-Path $PSScriptRoot 'rust\rustup'
$env:CARGO_HOME = Join-Path $PSScriptRoot 'rust\cargo'
$env:PATH = "$env:CARGO_HOME\bin;$env:PATH"
$env:CMAKE_GENERATOR = 'Visual Studio 17 2022'
Push-Location (Join-Path $taskRoot 'reference\touchHLE')
try {
    & cargo build --release --bin touchHLE -j 6
    if ($LASTEXITCODE -ne 0) { throw 'Runtime build failed.' }
} finally {
    Pop-Location
}
