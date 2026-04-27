#!/bin/bash

# Usage: ./run.sh [--debug|--release|--relwithdebinfo|--config <name>] [args...]

BUILD_CONFIG="Debug"
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
    --config)
      if [[ -z ${2:-} ]]; then
        echo "Missing value for --config" >&2
        exit 1
      fi
      BUILD_CONFIG="$(normalize_build_config "$2")" || exit 1
      shift 2
      ;;
    --debug)
      BUILD_CONFIG="Debug"
      shift
      ;;
    --release)
      BUILD_CONFIG="Release"
      shift
      ;;
    --relwithdebinfo)
      BUILD_CONFIG="RelWithDebInfo"
      shift
      ;;
    *)
      APP_ARGS+=("$1")
      shift
      ;;
  esac
done

PLATFORM_PRESET="$(platform_preset)" || exit 1
BUILD_DIR="build/${PLATFORM_PRESET}"

run() {
    local cmd=(./${BUILD_DIR}/${BUILD_CONFIG}/kinomata_tests "${APP_ARGS[@]}")
    "${cmd[@]}"
}

run
