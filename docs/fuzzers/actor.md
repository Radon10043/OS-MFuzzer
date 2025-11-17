# ACTOR

**Original Repository:** [https://github.com/ucsb-seclab/actor](https://github.com/ucsb-seclab/actor)

## Prerequisites

First, build the Docker image and start a container.

Command:
```bash
docker build -t actor:latest -f $OSMFUZZER/docker/Dockerfile.actor $OSMFUZZER/docker
docker run -v volume:/vol --cpus 16 --privileged --name actor-container actor:latest bash
```

Inside the container, download ACTOR and build the necessary files.

Command:
```bash
cd /vol
git clone https://github.com/ucsb-seclab/actor && cd actor
git checkout 918665bf05acb2663a4b3f48a98e48f7f09aa908
cd actor/semantic-inference
echo 'clang-14 -g -fexperimental-new-pass-manager -fpass-plugin=/home/actor/semantic-inference/build/libktypesPass.so "$@"' > clang-ktypes-14
echo 'clang-15 -g -fexperimental-new-pass-manager -fpass-plugin=/home/actor/semantic-inference/build/libktypesPass.so "$@"' > clang-ktypes-15
ln -s /home/actor/semantic-inference/clang-ktypes-14 /usr/local/bin/clang-ktypes-14
ln -s /home/actor/semantic-inference/clang-ktypes-15 /usr/local/bin/clang-ktypes-15
```

## Run

To run ACTOR, follow these steps:
1. Patch the target kernel.
2. Perform static analysis on the target kernel.
3. Build the target kernel.
4. Build the necessary modules for ACTOR.
5. Copy the modules to the disk image that the VM will use.
6. Start fuzzing.

Let's get started!

**1. Patch the target kernel.** We have prepared patches under `$OSMFUZZER/patch/kernel`. We will use Linux v5.15.189 as an example:

```bash
cd $KERNEL
git apply $OSMFUZZER/patch/kernel/linux.v5.15.189.actor.patch
```

**2. Perform static analysis on the target kernel.** First, build ACTOR, then use it to perform static analysis. You can use the pre-built ACTOR under `/home` or customize your settings. We will use LLVM 14 for this analysis. Note that for v5.10.240, LLVM 15 should be used.

Build ACTOR:

```bash
cd $ACTOR/semantic-inference/ && mkdir build && cd build
cmake -DLLVM_DIR=/usr/lib/llvm-14/lib/cmake/llvm .. && make
```

Then, analyze the kernel. This includes merging the configuration and compiling.

```bash
cd $KERNEL
cp $OSMFUZZER/configs/kernel/linux.v5.15.189.config .config
CC=clang-ktypes-14 $KERNEL/scripts/kconfig/merge_config.sh .config $ACTOR/semantic-inference/actor_static.config
make CC=clang-ktypes-14 olddefconfig
make CC=clang-ktypes-14 -j`nproc` 2> ptrs.v5.15.189.txt
```

The `ptrs.*.txt` file can be very large (~100MB), so it is recommended to save it locally.

**3. Build the kernel for ACTOR.** We will use `clang-19` to build the kernel for consistency with other fuzzers.

Command:
```bash
make distclean
cp $OSMFUZZER/configs/kernel/linux.v5.15.189.config .config
./scripts/kconfig/merge_config.sh .config $ACTOR/setup/kernel/actor.config
make CC=clang-19 -j`nproc` 2> /dev/null
```

**4. Build IVSHMEM.**

Command:
```bash
cd $ACTOR/setup/ivshmem/kernel_module/uio
make KDIR=$KERNEL CC=clang-14
```

**5. Create a new disk image and copy the required files.**

Command:
```bash
cd /vol/images
mkdir Debian-for-actor-v5.15.189 && cd Debian-for-actor-v5.15.189
cp $OSMFUZZER/scripts/create-image.sh .
./create-image.sh
```

Start the virtual machine.

Command:
```bash
qemu-system-x86_64 -m 2048 -smp 2 -chardev socket,id=SOCKSYZ,server=on,wait=off,host=localhost,port=27617 -mon chardev=SOCKSYZ,mode=control -display none -serial stdio -no-reboot -device virtio-rng-pci -enable-kvm -cpu host,migratable=off -device e1000,netdev=net0 -netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:2324-:22 -hda $IMAGE/bullseye.img -kernel $KERNEL/arch/x86/boot/bzImage -append "root=/dev/sda console=ttyS0" 2>&1 | tee vm.log
```

Open a new terminal to copy the necessary files for ACTOR to the disk image.

```bash
scp -P 2324 -F /dev/null -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i $SSHKEY -v $KERNEL/drivers/uio/uio.ko root@localhost:
scp -P 2324 -F /dev/null -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i $SSHKEY -v $ACTOR/setup/ivshmem/kernel_module/uio/uio_ivshmem.ko root@localhost:
```

**6. Create the configuration file and start fuzzing.**

Create `actor.config` with the following content:
```json
{
	"target": "linux/amd64",
	"http": ":56741",
	"workdir": "workdir/out",
	"kernel_obj": "$KERNEL",
	"image": "$IMAGE/bullseye.actor.v5.15.189.img",
	"sshkey": "$IMAGE/bullseye.id_rsa",
	"syzkaller": "$ACTOR/src/github.com/google/syzkaller",
	"procs": 8,
	"reproduce": false,
	"type": "qemu",
	"vm": {
		"count": 1,
		"kernel": "$KERNEL/arch/x86/boot/bzImage",
		"cpu": 2,
		"mem": 4096
	},
	"ignores": [
		"WARNING: The mand mount option has been deprecated and",
		"WARNING: fbcon: Driver 'bochs-drmdrmfb' missed to adjust virtual screen size*",
		"WARNING: fbcon: Driver 'vkmsdrmfb' missed to adjust virtual screen size*"
	],
	"disable_syscalls": []
}
```

Copy `ptrs.*.txt` to the work directory and start fuzzing.

Command:
```bash
cp $KERNEL/ptrs.txt workdir/out/
$ACTOR/src/github.com/google/syzkaller/bin/syz-manager -config=actor.config
```