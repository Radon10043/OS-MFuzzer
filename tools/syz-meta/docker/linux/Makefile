v6.2:
	git clone --branch v6.2 --depth 1 git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux-v6.2
	pushd linux-v6.2
	make defconfig
	make kvm_guest.config
	echo -e 'CONFIG_KCOV=y\nCONFIG_DEBUG_INFO_DWARF4=y\nCONFIG_KASAN=y\nCONFIG_KASAN_INLINE=y\nCONFIG_CONFIGFS_FS=y\nCONFIG_SECURITYFS=y\nCONFIG_CMDLINE_BOOL=y\nCONFIG_CMDLINE="net.ifnames=0"' > .config
	make -j`nproc`
	popd