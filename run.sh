#!/bin/bash

# Usage: ./run.sh [--release] [args...]

BUILD_DIR="build"
BUILD_CONFIG="Debug"

APP_ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --release)
      BUILD_CONFIG="Release"
      shift
      ;;
    *)
      APP_ARGS+=("$1")
      shift
      ;;
  esac
done

run() {
    local cmd=(./${BUILD_DIR}/src/${BUILD_CONFIG}/kinomata "${APP_ARGS[@]}")
    "${cmd[@]}"
}

run

