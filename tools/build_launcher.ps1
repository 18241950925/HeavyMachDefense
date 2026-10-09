$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    & windres.exe tools/launcher.rc -O coff -o tools/launcher-resource.o
    if ($LASTEXITCODE -ne 0) { throw 'Icon resource compilation failed.' }
    & g++.exe tools/launcher.cpp tools/launcher-resource.o -municode -mwindows -static -O2 -lshell32 -o 'windows/HeavyMachDefense.exe'
    if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed.' }
} finally {
    Pop-Location
}
