#!/bin/bash

# Usage: ./build.sh [--run] [--release] [--clean] [run_args...]

BUILD_DIR="build"
GENERATOR="Ninja Multi-Config"

echo "--- Configuring with CMake ---"
BUILD_CONFIG="Debug"
RUN=false
CLEAN=false
APP_ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --release)
      BUILD_CONFIG="Release"
      shift
      ;;
    --run)
      RUN=true
      shift
      ;;
    --clean)
      CLEAN=true
      shift
      ;;
    *)
      APP_ARGS+=("$1")
      shift
      ;;
  esac
done

echo "--- Build config: ${BUILD_CONFIG} ---"

set -e # Exit on error

run() {
    local cmd=(./${BUILD_DIR}/src/${BUILD_CONFIG}/kinomata "${APP_ARGS[@]}")
    "${cmd[@]}"
}

if $CLEAN; then
    echo "--- Cleaning build dir ---"
    rm -rf ${BUILD_DIR}
fi

cmake -S . -B "${BUILD_DIR}" -G "${GENERATOR}"
cmake --build "${BUILD_DIR}" --parallel --config "${BUILD_CONFIG}"

if [ $? -eq 0 ]; then
    echo "--- Build Successful ---"
    # Optional run
    if $RUN; then
      run
    fi
else
    echo "--- Build Failed ---"
    exit 1
fi
