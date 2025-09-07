#!/bin/bash

# Run virtual device via Cuttlegfish

set -euo pipefail

IMAGE=""
KERNEL=""
CONFIRM=""

source $(dirname $0)/utils.sh

print_help() {
    echo "Usage: $0 -i/--image <Path to GSI> \\"
    echo "          -k/--kernel <Path to GKI>"
    echo "          [-y/--yes] [-h/--help]"
    echo "Example: $0 --image ./android13-gsi --kernel ./common-android13-5.15 -y"
}

if [[ $(id -u) -ne 0 ]]; then
    echo "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Analyze arguments
if [[ $# -eq 0 ]]; then
    print_help
    exit 1
fi
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_help
            exit 0
            ;;
        -i|--image)
            IMAGE="$2"
            shift
            shift
            ;;
        -k|--kernel)
            KERNEL="$2"
            shift
            shift
            ;;
        -y|--yes)
            CONFIRM="y"
            shift
            ;;
        *)
            print_help
            exit 1
            ;;
    esac
done
if [[ -z "$IMAGE" || -z "$KERNEL" ]]; then
    echo "Both image and kernel must be specified."
    exit 1
fi

# Get lunch target
BRANCH=$(basename "$IMAGE")
TARGET=$(get_lunch_target $BRANCH)

# Prompt for confirmation
if [[ -z $CONFIRM ]]; then
    echo "IMAGE: $IMAGE"
    echo "TARGET: $TARGET"
    echo "KERNEL: $KERNEL"
    echo -n "Are you sure? (y/n) "
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

# Launch virtual device
rm -rf ~/cuttlefish/instances
KERNEL_DIR=$(dirname "$KERNEL")
cd $IMAGE
bash -c "
    source build/envsetup.sh
    lunch $TARGET
    yes | launch_cvd -daemon \
                     -kernel_path=$KERNEL \
                     -initramfs_path=$KERNEL_DIR/initramfs.img
"