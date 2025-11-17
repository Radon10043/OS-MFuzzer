# ACTOR

Original repositopry link: [https://github.com/ucsb-seclab/actor](https://github.com/ucsb-seclab/actor).

## Prerequisites

Build docker image and run.

Command:
```bash
docker build -t actor:latest -f $OSMFUZZER/docker/Dockerfile.actor $OSMFUZZER/docker
docker up -v volume:/vol --cpus 16 --privileged --name actor-container actor:latest bash
```

In the container, download ACTOR and build some necessary files.

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

To run ACTOR, we need:
1. Patch target kernel.
2. Perform static analysis to target kernel.
3. Build target kernel.
4. Build necessary modules for ACTOR.
5. Copy modules to disk image which VM will be used.
6. Run fuzzing.

Let's go!

**Patch target kernel.** We have prepared some patches under `$OSMFUZZER/patch/kernel`. We use linux v5.15.189 as an example:

```bash
cd $KERNEL
git apply $OSMFUZZER/patch/kernel/linux.v5.15.189.actor.patch
```

**Perform static analysis to target kernel.** Build ACTOR first, then using ACTOR to perform static analysis, you can use the actor under `/home`,
or customize your settings. We use LLVM 14 to analyze kernel. Note that for v5.10.240, we use llvm 15.

Build ACTOR:

```bash
cd $ACTOR/semantic-inference/ && mkdir build && cd build
cmake -DLLVM_DIR=/usr/lib/llvm-14/lib/cmake/llvm .. && make
```

Then analyze kernel, including merge config and compile. Command:

```bash
cd $KERNEL
cp $OSMFUZZER/configs/kernel/linux.v5.15.189.patch
CC=clang-ktypes-14 $KERNEL/scripts/kconfig/merge_config.sh .config $ACTOR/semantic-inference/actor_static.config
make CC=clang-ktypes-14 olddefconfig
make CC=clang-ktypes-14 -j`nproc` 2> ptrs.v5.15.189.txt
```

ptrs.*.txt may very large (~100MB), so it is good for you to save it locally.

Build kernel for actor. In addition, we use clang-19 to build kernel to keep consistent with other fuzzers.

Command:
```bash
make distclean
cp $OSMFUZZER/configs/kernel/linux.v5.15.189.config .config
./scripts/kconfig/merge_config.sh .config $ACTOR/setup/kernel/actor.config
make CC=clang-19 -j`nproc` 2> /dev/null
```

Build IVSHMEM:

Command:
```bash
cd $ACTOR/setup/ivshmem/kernel_module/uio
make KDIR=$KERNEL CC=clang-14
```

Let's create a new disk image then copy ACTOR required files to it.

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

Open a new terminal to copy necessary files for actor to disk image:

```bash
scp -P 2324 -F /dev/null -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i $SSHKEY -v $KERNEL/drivers/uio/uio.ko root@localhost:
scp -P 2324 -F /dev/null -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i $SSHKEY -v $ACTOR/setup/ivshmem/kernel_module/uio/uio_ivshmem.ko root@localhost:
```

Create the config file:

Config:
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

Copy ptrs.*.txt to work directory and perform fuzzing as usual:

Command:
```bash
cp $KERNEL/ptrs.txt workdir/out/
$ACTOR/src/github.com/google/syzkaller/bin/syz-manager -config=actor.config
```