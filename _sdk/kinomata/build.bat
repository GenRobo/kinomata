@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Usage: build.bat [--run] [--config=<name>] [--clean] [run_args...]

set "BUILD_CONFIG=Debug"
set "PLATFORM_PRESET=win-x64"
set "BUILD_DIR=build\%PLATFORM_PRESET%"
set "RUN=false"
set "CLEAN=false"
set "APP_ARGS="
set "VCVARS_ARCH=x64"
set "CMAKE_EXE="
set "NINJA_EXE="
set "VCVARSALL_EXE="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--config" (
    if "%~2"=="" (
        echo Missing value for --config
        goto build_failed
    )
    if /I "%~2"=="Debug" (
        set "BUILD_CONFIG=Debug"
    ) else if /I "%~2"=="Release" (
        set "BUILD_CONFIG=Release"
    ) else if /I "%~2"=="RelWithDebInfo" (
        set "BUILD_CONFIG=RelWithDebInfo"
    ) else (
        echo Unsupported build config: "%~2"
        goto build_failed
    )
    shift
    shift
    goto parse_args
)

if /I "%~1"=="--run" (
    set "RUN=true"
    shift
    goto parse_args
)

if /I "%~1"=="--clean" (
    set "CLEAN=true"
    shift
    goto parse_args
)

set "APP_ARGS=!APP_ARGS! %~1"
shift
goto parse_args

:args_done
call :locate_cmake
if errorlevel 1 goto build_failed
call :locate_ninja
if errorlevel 1 goto build_failed
call :locate_vcvarsall
if errorlevel 1 goto build_failed
if /I "%BUILD_CONFIG%"=="Debug" (
    set "PRESET_SUFFIX=debug"
) else if /I "%BUILD_CONFIG%"=="Release" (
    set "PRESET_SUFFIX=release"
) else if /I "%BUILD_CONFIG%"=="RelWithDebInfo" (
    set "PRESET_SUFFIX=relwithdebinfo"
) else (
    echo Unsupported build config: "%BUILD_CONFIG%"
    goto build_failed
)
set "BUILD_PRESET=%PLATFORM_PRESET%-%PRESET_SUFFIX%"

echo --- Build config: %BUILD_CONFIG% ---
echo --- Configure preset: %PLATFORM_PRESET% ---
echo --- Build preset: %BUILD_PRESET% ---
echo --- Install dir: ..\..\Source\FirstParty\KinomataLibrary\%PLATFORM_PRESET%\%BUILD_CONFIG% ---
echo --- CMake: %CMAKE_EXE% ---
echo --- Ninja: %NINJA_EXE% ---
if defined VCVARSALL_EXE (
    echo --- MSVC env: %VCVARSALL_EXE% ---
)
for %%I in ("%NINJA_EXE%") do set "PATH=%%~dpI;%PATH%"
if defined VCVARSALL_EXE (
    call "%VCVARSALL_EXE%" %VCVARS_ARCH%
    if errorlevel 1 goto build_failed
) else if defined VCVARSALL (
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
    if exist "%BUILD_DIR%" (
        echo Failed to remove "%BUILD_DIR%". A build artifact may still be in use.
        echo Close any running kinomata process, debugger session, or terminal in that directory and try again.
        goto build_failed
    )
)

echo --- Configuring with CMake ---
"%CMAKE_EXE%" --preset "%PLATFORM_PRESET%"
if errorlevel 1 goto build_failed

"%CMAKE_EXE%" --build --preset "%BUILD_PRESET%" --parallel
if errorlevel 1 goto build_failed

"%CMAKE_EXE%" --install "%BUILD_DIR%" --config "%BUILD_CONFIG%" --component KinomataRuntime
if errorlevel 1 goto build_failed

echo --- Build Successful ---
if /I "%RUN%"=="true" goto run_app
exit /b 0

:run_app
"%BUILD_DIR%\src\%BUILD_CONFIG%\kinomata.exe"%APP_ARGS%
exit /b %errorlevel%

:locate_cmake
for %%I in (cmake.exe) do set "CMAKE_EXE=%%~$PATH:I"
if defined CMAKE_EXE exit /b 0

for /d %%V in ("%ProgramFiles%\Microsoft Visual Studio\*") do (
    for /d %%E in ("%%~fV\*") do (
        if exist "%%~fE\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" (
            set "CMAKE_EXE=%%~fE\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
            exit /b 0
        )
    )
)

echo Could not locate cmake.exe. Add CMake to PATH or install the Visual Studio CMake workload.
exit /b 1

:locate_ninja
for %%I in (ninja.exe) do set "NINJA_EXE=%%~$PATH:I"
if defined NINJA_EXE exit /b 0

for /d %%V in ("%ProgramFiles%\Microsoft Visual Studio\*") do (
    for /d %%E in ("%%~fV\*") do (
        if exist "%%~fE\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe" (
            set "NINJA_EXE=%%~fE\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
            exit /b 0
        )
    )
)

echo Could not locate ninja.exe. Add Ninja to PATH or install the Visual Studio CMake workload.
exit /b 1

:locate_vcvarsall
if defined VCVARSALL (
    if exist "%VCVARSALL%" (
        set "VCVARSALL_EXE=%VCVARSALL%"
        exit /b 0
    )
    echo VCVARSALL is set but does not point to an existing file: "%VCVARSALL%"
)

for /d %%V in ("%ProgramFiles%\Microsoft Visual Studio\*") do (
    for /d %%E in ("%%~fV\*") do (
        if exist "%%~fE\VC\Auxiliary\Build\vcvarsall.bat" (
            set "VCVARSALL_EXE=%%~fE\VC\Auxiliary\Build\vcvarsall.bat"
            exit /b 0
        )
    )
)

echo Could not locate vcvarsall.bat. Install the Visual Studio C++ workload or set VCVARSALL manually.
exit /b 1

:build_failed
echo --- Build Failed ---
exit /b 1
