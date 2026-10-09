@echo off
if "%~1"=="--build" goto plain
if "%~1"=="--install" goto plain
if "%~1"=="--version" goto plain
if "%~1"=="-E" goto plain
"%MECH_CMAKE_EXECUTABLE%" -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-21 -DANDROID_STL=c++_shared -DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON %*
exit /b %errorlevel%
:plain
"%MECH_CMAKE_EXECUTABLE%" %*
exit /b %errorlevel%
