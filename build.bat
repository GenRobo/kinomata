@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Usage: build.bat [--run] [--release] [--clean] [run_args...]

set "BUILD_DIR=build"
set "BUILD_CONFIG=Debug"
set "GENERATOR=Ninja Multi-Config"
set "RUN=false"
set "CLEAN=false"
set "APP_ARGS="
set "VCVARS_ARCH=x64"

:parse_args
if "%~1"=="" goto args_done

if "%~1"=="--release" (
    set "BUILD_CONFIG=Release"
    shift
    goto parse_args
)

if "%~1"=="--run" (
    set "RUN=true"
    shift
    goto parse_args
)

if "%~1"=="--clean" (
    set "CLEAN=true"
    shift
    goto parse_args
)

set "APP_ARGS=!APP_ARGS! %~1"
shift
goto parse_args

:args_done
echo --- Build config: %BUILD_CONFIG% ---
if defined VCVARSALL (
    if exist "%VCVARSALL%" (
        echo --- Loading MSVC environment ---
        call "%VCVARSALL%" %VCVARS_ARCH%
        if errorlevel 1 goto build_failed
    ) else (
        echo VCVARSALL is set but does not point to an existing file: "%VCVARSALL%"
        echo --- Continuing without loading MSVC environment ---
    )
)

if /I "%CLEAN%"=="true" (
    echo --- Cleaning build dir ---
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
)

echo --- Configuring with CMake ---
cmake -S . -B "%BUILD_DIR%" -G "%GENERATOR%"
if errorlevel 1 goto build_failed

cmake --build "%BUILD_DIR%" --parallel --config %BUILD_CONFIG%
if errorlevel 1 goto build_failed

echo --- Build Successful ---
if /I "%RUN%"=="true" goto run_app
exit /b 0

:run_app
"%BUILD_DIR%\src\%BUILD_CONFIG%\kinomata.exe"%APP_ARGS%
exit /b %errorlevel%

:build_failed
echo --- Build Failed ---
exit /b 1
