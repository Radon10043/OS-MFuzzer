# Guide for fuzzing Android Kernel

This document guides users to download, build, and fuzzing Android kernel.

## Build GSI

Download and run following commands:

Command:
```bash
TARGET=aosp_cf_x86_64_phone-userdebug
cd android13-gsi
source build/envsetup.sh
lunch $TARGET
```

For GSI version >= 15, `TARGET` should be asop_cf_x86_64_phone-trunk_staging-userdebug

## Build GKI

Download first. We can build GKI via build.sh or bazel.

For branch supported build systems, see [officail documentation](https://source.android.com/docs/setup/reference/bazel-support).

### build.sh

For build.sh, run following commands to build kernel and vendor modules with KASAN+KCOV:

Command:
```bash
cd common-android13-5.15
BUILD_CONFIG=common/build.config.gki_kasan.x86_64 build/build.sh
BUILD_CONFIG=common-modules/virtual-device/build.config.virtual_device_kasan.x86_64 build/build.sh
cp out/android13-5.15 dist
```

### bazel

For bazel, run following commands to build kernel and vendor modules with KASAN+KCOV:

Command:
```bash
cd common-android15-6.1
tools/bazel run \
    --kasan \
    //common-modules/virtual-device:virtual_device_x86_64_dist --destdir=dist
```

For `common-android16-6.12`, we should add `--kcov`:

```bash
cd common-android16-6.12
tools/bazel run \
    --kasan \
    --kcov \
    //common-modules/virtual-device:virtual_device_x86_64_dist --destdir=dist
```

You should see `bzImage` and `initramfs.img` in `dist` directory under the kernel root.

## GPU boost (Optional)

For gpu boost, install gpu drivers in the host first, see [official tutorial](https://documentation.ubuntu.com/server/how-to/graphics/install-nvidia-drivers/). I ran the following commands on my host:

Command:
```bash
ubuntu-drivers devices
sudo apt install -y nvidia-driver-575-open
```

Run `nvidia-smi` on the host. If the table show expectly, then we can go next.

Let's install nvidia-container-toolkit, see [officical installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#with-apt-ubuntu-debian).

Configure and restart docker use the following commands:

Command:
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Build cuttlefish image, see [this](/docs/image-building.md#cuttlefish).

Run cuttlefish image with flags `--gpus all`, `--runtime nvidia`, and `-e NVIDIA_DRIVER_CAPABILITIES=all`.

Command:
```bash
docker run \
    --rm \
    -it \
    --privileged \
    --network host \
    --cpus 8 \
    -v $GSI:/vol/android \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --runtime nvidia \
    --gpus all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    cuttlefish:v1.15.0 bash
```

> [!WARNING]
> If you build GSI in the container that run with `--gpus all`, GSI cannot be built successfully. I don't know the reason but we'd better don't build GSI under that precondition.

In container, run the following command to check whether GPU can be accessed:

```bash
vulkaninfo --summary | grep deviceName
```

If GPU's name is presented, e.g. `NVIDIA GeForce RTX 4090`, means that we are going to success.

Boot android system with gpu boost:

Command:
```bash
cd /vol/android
source build/envsetup.sh
lunch aosp_cf_x86_64_phone-userdebug    # For GSI >= 15, it should be aosp_cf_x86_64_phone-trunk_staging-userdebug
launch_cvd -daemon # --gpu_mode=gfxstream <- Optional flag, it will enable automatically if it is avaliable
```

You can see `launcher.log` of cuttlefish or console output to confirm whether GPU boost is enabled.

> [!WARNING]
> Some GSI may cannot booted when GPU boost is enabled. I use RTX 4090, ubuntu 24.04 (host), ubuntu 22.04 (container), and nvidia driver is 575.64.03. Android 14-16 GSI can be booted under GPU boost, but android 13 cannot.

## Fuzzing

Todo