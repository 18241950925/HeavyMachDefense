$ErrorActionPreference = 'Stop'
$env:RUSTUP_HOME = Join-Path $PSScriptRoot 'rust\rustup'
$env:CARGO_HOME = Join-Path $PSScriptRoot 'rust\cargo'
$env:PATH = "$env:CARGO_HOME\bin;$env:PATH"
& rustup target add aarch64-linux-android
if ($LASTEXITCODE -ne 0) { throw 'Android Rust target installation failed.' }
& cargo install cargo-ndk --version 3.5.4 --locked
if ($LASTEXITCODE -ne 0) { throw 'cargo-ndk installation failed.' }
