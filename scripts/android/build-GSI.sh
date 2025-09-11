#!/bin/bash

# Script for building Android GSI
#
# Possible branches: android13-gsi, android14-gsi, android-15.0.0_r10, android-16.0.0_r2
#
# Recommended lunch target for different branches:
#   < 15: aosp_cf_x86_64_phone-userdebug
#   >= 15: aosp_cf_x86_64_phone_64-trunk_staging-userdebug

set -e

source $(dirname $0)/utils.sh

IMAGE=""
TARGET=""

# Show help message
print_help() {
    echo
    echo "Usage: $0 [ARGS]"
    echo "  Arguments [Required]:"
    echo "    -i, --image <IMAGE>: Path to GSI directory."
    echo "    -t, --target <TARGET>: Lunch target, e.g. aosp_cf_x86_64_phone-userdebug."
    echo "  Arguments [Optional]:"
    echo "    -h, --help: Show help message."
    echo "Example:"
    echo "  $0 -i android13-gsi -t aosp_cf_x86_64_phone-userdebug"
    echo
}

# Show download prompt for kernel source
print_download_prompt() {
    # USTC mirror: https://mirrors.ustc.edu.cn/aosp/kernel/manifest
    echo
    echo "Oops, looks like '$1' doesn't exist, you need to download it via repo first."
    echo "Try following commands:"
    echo "  mkdir $1 && cd $1"
    echo "  repo init --partial-clone -u https://android.googlesource.com/platform/manifest -b $1"
    echo "  repo sync -c"
    echo
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
            exit 1
            ;;
    esac
done

apt update
apt install -y git wget curl repo libncurses5 vim gcc make bison bc zip rsync language-pack-en-base

# Check path to GSI
if [[ ! -d $IMAGE ]]; then
    print_download_prompt $IMAGE
    exit 1
fi

# Build GSI, using 16 CPU cores takes about two hours
cd $IMAGE
source build/envsetup.sh
lunch $TARGET
m