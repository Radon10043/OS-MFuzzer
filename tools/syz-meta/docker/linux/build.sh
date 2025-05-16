#!/bin/bash
# $1: Kernel's version, e.g. v6.2.
# $2: Building configuration, syzbot using syzbot.config.

set -e

git clone --branch $1 --depth 1 git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git $1
pushd $1
make defconfig
make kvm_guest.config
if [ "$2" == "syzbot" ]; then
    if [ "$1" == "v5.15" ]; then
        cp ../syzbot.v5.15.config .config
    else if [ "$1" == "v6.1" ]; then
        cp ../syzbot.v6.1.config .config
    else
        cp ../syzbot.config .config
    fi
else
    echo -e 'CONFIG_KCOV=y\nCONFIG_DEBUG_INFO_DWARF4=y\nCONFIG_KASAN=y\nCONFIG_KASAN_INLINE=y\nCONFIG_CONFIGFS_FS=y\nCONFIG_SECURITYFS=y\nCONFIG_CMDLINE_BOOL=y\nCONFIG_CMDLINE="net.ifnames=0"' > .config
fi
make olddefconfig
make -j`nproc`
popd