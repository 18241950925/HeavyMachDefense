$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskDrive = 'X:'
if (Test-Path "$taskDrive\") {
    throw 'Drive X: is already in use; choose a free temporary drive in this build script.'
}
& subst.exe $taskDrive $taskRoot
if ($LASTEXITCODE -ne 0) { throw 'Could not create a build path without spaces.' }
try {
    $taskBuildRoot = $taskDrive
    $env:RUSTUP_HOME = "$taskBuildRoot\tools\rust\rustup"
    $env:CARGO_HOME = "$taskBuildRoot\tools\rust\cargo"
    $env:CARGO_TARGET_DIR = "$taskBuildRoot\tools\android-native-build"
    $env:ANDROID_NDK_HOME = "$taskBuildRoot\tools\android-sdk\ndk\28.2.13676358"
    $env:ANDROID_NDK = $env:ANDROID_NDK_HOME
    $env:ANDROID_NDK_ROOT = $env:ANDROID_NDK_HOME
    $env:CC = "$env:ANDROID_NDK_HOME\toolchains\llvm\prebuilt\windows-x86_64\bin\clang.exe"
    $env:CXX = "$env:ANDROID_NDK_HOME\toolchains\llvm\prebuilt\windows-x86_64\bin\clang++.exe"
    $taskNinja = 'D:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja'
    $env:PATH = "$env:CARGO_HOME\bin;$taskNinja;$env:PATH"
    $env:CMAKE_GENERATOR = 'Ninja'
    $env:CMAKE_TOOLCHAIN_FILE = "$env:ANDROID_NDK_HOME\build\cmake\android.toolchain.cmake"
    $env:MECH_CMAKE_EXECUTABLE = (Get-Command cmake.exe).Source
    $env:CMAKE = "$taskBuildRoot\tools\android_cmake.cmd"
    $env:RUSTFLAGS = '-C link-arg=-Wl,-z,max-page-size=16384 -C link-arg=-Wl,-z,common-page-size=16384'
    Push-Location "$taskBuildRoot\reference\touchHLE"
    try {
        & cargo ndk -t arm64-v8a -p 21 -o "$taskBuildRoot\android\project\jniLibs" build --release --lib --no-default-features --features 'touchHLE_openal_soft_wrapper/static,sdl2/bundled' -j 6
        if ($LASTEXITCODE -ne 0) { throw 'Android native runtime build failed.' }
    } finally {
        Pop-Location
    }
} finally {
    & subst.exe $taskDrive /d
}
