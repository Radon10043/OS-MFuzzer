#!/bin/bash

set -euo pipefail

print_help() {
    echo "Usage: $0 -v/--version <version> -c/--config <config>"
    echo "Example: $0 -v v6.6.100 -c ../SyzMeta/configs/kernel/linux.v6.6.100.config"
}

VERSION=""
CONFIG=""

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
        -v|--version)
            VERSION="$2"
            shift
            shift
            ;;
        -c|--config)
            CONFIG="$2"
            shift
            shift
            ;;
        *)
            print_help
            exit 0
            ;;
    esac
done

git clone -b $VERSION --depth 1 git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git $VERSION
cd $VERSION
cp $CONFIG .config
make CC=clang olddefconfig
make CC=clang -j$(nproc)