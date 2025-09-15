#!/bin/bash

# Run cuttilefish virtual device

set -e

IMAGE=""
KERNEL=""
TARGET=""
NUM_INSTANCES=1

# Show help message
print_help() {
    echo
    echo "Usage: $0 [ARGS] \\"
    echo "  Arguments [Required]:"
    echo "    -i, --image <IMAGE>: Path to GSI directory."
    echo "    -k, --kernel <KERNEL>: Path to android kernel, e.g., bzImage."
    echo "    -t, --target <TARGET>: lunch target, e.g., aosp_cf_x86_64_phone-userdebug."
    echo "  Arguments [Optional]:"
    echo "    -n, --num_instances: Number of virtual device instances."
    echo "    -h, --help: Show help message."
    echo "Example:"
    echo "  $0 --image ./android13-gsi --kernel ./common-android13-5.15/dist/bzImage --target aosp_cf_x86_64_phone-userdebug"
    echo
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
    -h | --help)
        print_help
        exit 0
        ;;
    -i | --image)
        IMAGE=$2
        shift 2
        ;;
    -k | --kernel)
        KERNEL=$2
        shift 2
        ;;
    -t | --target)
        TARGET=$2
        shift 2
        ;;
    -n | --num_instances)
        NUM_INSTANCES=$2
        shift 2
        ;;
    *)
        print_help
        exit 1
        ;;
    esac
done
if [[ -z "$IMAGE" || -z "$KERNEL" || -z "$TARGET" ]]; then
    echo "-i (--image), -k (--kernel), and -t (--target) are required arguments."
    exit 1
fi

# Launch cuttlefish virtual device
KERNEL_DIR=$(dirname "$KERNEL")
cd $IMAGE
bash -c "
    source build/envsetup.sh
    lunch $TARGET
    yes | launch_cvd -daemon \
                     -kernel_path=$KERNEL \
                     -initramfs_path=$KERNEL_DIR/initramfs.img \
                     -num_instances=$NUM_INSTANCES
"
