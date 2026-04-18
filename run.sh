#!/bin/bash

# Usage: ./run.sh [args...]

BUILD_DIR="build"

APP_ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    *)
      APP_ARGS+=("$1")
      shift
      ;;
  esac
done

run() {
    local cmd=(./${BUILD_DIR}/src/kinomata ${APP_ARGS[@]})
    "${cmd[@]}"
}

run

