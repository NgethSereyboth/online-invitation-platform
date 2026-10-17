#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
ANDROID_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
SDK_DIR=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-"$ANDROID_DIR/.android-sdk"}}

if [ ! -d "$SDK_DIR" ]; then
  echo "Android SDK not found at $SDK_DIR; set ANDROID_SDK_ROOT or ANDROID_HOME." >&2
  exit 1
fi

export ANDROID_HOME="$SDK_DIR"
export ANDROID_SDK_ROOT="$SDK_DIR"
export GRADLE_USER_HOME=${GRADLE_USER_HOME:-"$ANDROID_DIR/.gradle"}
exec "$ANDROID_DIR/gradlew" -p "$ANDROID_DIR" :app:assembleDebug "$@"
