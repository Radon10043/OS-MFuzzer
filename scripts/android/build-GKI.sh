#!/bin/bash

# Script for building Android GKI

set -e

BUILD=""
KERNEL=""

# Show help message
print_help() {
    echo
    echo "Usage: $0 [ARGS]"
    echo "  Arguments [Required]:"
    echo "    -k, --kernel <KERNEL>: Path to the kernel directory."
    echo "    -b, --build <BUILD>: Kernel building method, chocies: build.sh, bazel."
    echo "  Arguments [Optional]:"
    echo "    -h, --help: Show help message."
    echo "Example:"
    echo "  $0 -k /path/to/common-android13-5.15 build.sh"
    echo
}

# Show download prompt for kernel source
print_download_prompt() {
    # USTC mirror: https://mirrors.ustc.edu.cn/aosp/kernel/manifest
    echo
    echo "Oops, looks like '$1' doesn't exist, you need to download it via repo first."
    echo "Try following commands:"
    echo "  mkdir $1 && cd $1"
    echo "  repo init -u https://android.googlesource.com/kernel/manifest -b $1"
    echo "  repo sync -c"
    echo
}

print_build_prompt() {
    echo
    echo "Build system '$1' is not supported, supported systems: build.sh, bazel."
    echo "About Kernel branches and their build systems, see:"
    echo "  https://source.android.com/docs/setup/reference/bazel-support"
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
    -h | --help)
        print_help
        exit 0
        ;;
    -b | --build)
        BUILD=$2
        shift
        shift
        ;;
    -k | --kernel)
        KERNEL=$2
        shift
        shift
        ;;
    *)
        print_help
        exit 1
        ;;
    esac
done

# Check path to GKI
if [[ ! -d $KERNEL ]]; then
    print_download_prompt $KERNEL
    exit 1
fi

# Check build system
if [[ $BUILD != "build.sh" && $BUILD != "bazel" ]]; then
    print_build_prompt $BUILD
    exit 1
fi

# Build kernel and vendor modules with KASAN+KCOV
if [[ $BUILD == "build.sh" ]]; then
    cd $KERNEL
    BUILD_CONFIG=common/build.config.gki_kasan.x86_64 build/build.sh
    BUILD_CONFIG=common-modules/virtual-device/build.config.virtual_device_kasan.x86_64 build/build.sh
    cp -r $(find out/ -name dist) .
elif [[ $BUILD == "bazel" ]]; then
    cd $KERNEL
    # If system cannot boot, try enable optimize for size
    echo "CONFIG_CC_OPTIMIZE_FOR_SIZE=y" >common-modules/virtual-device/optsize.fragment
    tools/bazel run \
        --defconfig_fragment=common-modules/virtual-device:optsize.fragment \
        --kasan \
        //common-modules/virtual-device:virtual_device_x86_64_dist --destdir=dist
fi
