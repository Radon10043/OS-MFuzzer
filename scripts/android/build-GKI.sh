#!/bin/bash

# Script for building Android GKI

set -euo pipefail

BRANCH=""

print_help() {
    echo "Usage: $0 -b/--branch <branch>"
    echo "Example: $0 common-android13-5.15"
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
        *)
            print_help
            exit 0
            ;;
    esac
done

if [[ ! -d $BRANCH ]]; then
    mkdir -p $BRANCH
fi
cd $BRANCH
# USTC mirror: https://mirrors.ustc.edu.cn/aosp/kernel/manifest
repo init -u https://android.googlesource.com/kernel/manifest -b $BRANCH
repo sync -c

# TODO: build GKI via build.s or bazel