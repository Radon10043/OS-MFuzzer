#!/bin/bash

# Script for building Android GSI
# Possible branches: android12-gsi, android13-gsi, android14-gsi, android-15.0.0_r36, android-16.0.0_r2

set -euo pipefail

source $(dirname $0)/utils.sh

BRANCH=""
TARGET=""
CONFIRM=""

PRODUCT_NAME=aosp_cf_x86_64_phone
RELEASE_CONFIG=trunk_staging
BUILD_VARIANT=userdebug

print_help() {
    echo "Usage: $0 -b/--branch <branch>"
    echo "Example: $0 android13-gsi"
}

if [[ $(id -u) -ne 0 ]]; then
    echo "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Analyze arguments
if [[ $# -eq 0 ]]; then
    print_help
    exit 0
fi
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_help
            exit 0
            ;;
        -b|--branch)
            BRANCH="$2"
            shift
            shift
            ;;
        -y|--yes)
            CONFIRM="y"
            shift
            ;;
        *)
            print_help
            exit 0
            ;;
    esac
done

# Determine build target through branch
TARGET=$(get_lunch_target $BRANCH)

# Prompt for confirmation
if [[ -z $CONFIRM ]]; then
    echo "BRANCH: $BRANCH"
    echo "TARGET: $TARGET"
    echo -n "Are you sure? (y/n) "
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

apt update
apt install -y git wget curl repo libncurses5 vim gcc make bison bc zip rsync language-pack-en-base

# Checkout source code of GSI
if [[ ! -d $BRANCH ]]; then
    mkdir $BRANCH
fi
cd $BRANCH
# USTC mirror: https://mirrors.ustc.edu.cn/aosp/platform/manifest
repo init --partial-clone -u https://android.googlesource.com/platform/manifest -b $BRANCH
repo sync -c

# Build GSI, using 16 CPU cores takes about two hours
cd $BRANCH
source build/envsetup.sh
lunch $TARGET
m

echo "Done. You can run the Android Virtual Device by following commands:"
echo "  cd $BRANCH"
echo "  source build/envsetup.sh"
echo "  lunch $TARGET"
echo "  launch_cvd"