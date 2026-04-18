#!/bin/bash

# Usage: ./build.sh [--run] [--release] [--clean] [run_args...]

BUILD_DIR="build"

echo "--- Configuring with CMake ---"
BUILD_TYPE="Debug"
RUN=false
CLEAN=false
APP_ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --release)
      BUILD_TYPE="Release"
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

set -e # Exit on error

run() {
    local cmd=(./${BUILD_DIR}/src/kinomata ${APP_ARGS[@]})
    "${cmd[@]}"
}

if $CLEAN; then
    echo "--- Cleaning build dir ---"
    rm -rf ${BUILD_DIR}
fi

cmake -S . -B ${BUILD_DIR} -G Ninja -DCMAKE_BUILD_TYPE=${BUILD_TYPE}
cmake --build build --parallel --config ${BUILD_TYPE} 

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

