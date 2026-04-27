#!/bin/bash

# Usage: ./build.sh [--run] [--config=<name>] [--clean] [run_args...]

echo "--- Configuring with CMake ---"
BUILD_CONFIG="Debug"
RUN=false
CLEAN=false
APP_ARGS=()

platform_preset() {
  case "$(uname -s)" in
    Darwin) echo "macos-arm64" ;;
    Linux) echo "linux-debian-x64" ;;
    *)
      echo "Unsupported host platform: $(uname -s)" >&2
      return 1
      ;;
  esac
}

build_preset_suffix() {
  case "$1" in
    Debug) echo "debug" ;;
    Release) echo "release" ;;
    RelWithDebInfo) echo "relwithdebinfo" ;;
    *)
      echo "Unsupported build config: $1" >&2
      return 1
      ;;
  esac
}

normalize_build_config() {
  case "${1,,}" in
    debug) echo "Debug" ;;
    release) echo "Release" ;;
    relwithdebinfo) echo "RelWithDebInfo" ;;
    *)
      echo "Unsupported build config: $1" >&2
      return 1
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --config=*)
      BUILD_CONFIG="$(normalize_build_config "${1#--config=}")" || exit 1
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

PLATFORM_PRESET="$(platform_preset)" || exit 1
BUILD_PRESET="${PLATFORM_PRESET}-$(build_preset_suffix "${BUILD_CONFIG}")" || exit 1
BUILD_DIR="build/${PLATFORM_PRESET}"

echo "--- Build config: ${BUILD_CONFIG} ---"
echo "--- Configure preset: ${PLATFORM_PRESET} ---"
echo "--- Build preset: ${BUILD_PRESET} ---"

set -e # Exit on error

run() {
    local cmd=(./${BUILD_DIR}/${BUILD_CONFIG}/kinomata_tests "${APP_ARGS[@]}")
    "${cmd[@]}"
}

if $CLEAN; then
    echo "--- Cleaning build dir ---"
    rm -rf "${BUILD_DIR}"
    if [[ -e "${BUILD_DIR}" ]]; then
        echo "Failed to remove ${BUILD_DIR}. A build artifact may still be in use." >&2
        echo "Close any running kinomata_tests process, debugger session, or terminal in that directory and try again." >&2
        exit 1
    fi
fi

cmake --preset "${PLATFORM_PRESET}"
cmake --build --preset "${BUILD_PRESET}" --parallel

echo "--- Build Successful ---"
if $RUN; then
  run
fi
