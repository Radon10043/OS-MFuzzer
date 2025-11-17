# MOCK

**Original Repository:** [https://github.com/m0ck1ng/mock/tree/main](https://github.com/m0ck1ng/mock/tree/main)

## Prerequisites

First, build the Docker image for MOCK.

Command:
```bash
docker build -t mock:latest -f $OSMFUZZER/docker/Dockerfile.mock $OSMFUZZER/docker
docker run -v volume:/vol --cpus 16 --privileged --name mock-container mock:latest bash
```

Next, download, patch, and build MOCK.

Command:
```bash
cd /vol
git clone https://github.com/m0ck1ng/mock && cd mock
git checkout 8f68fe365d7eb17ce354c8fc8ec7ff9a320080df
git apply $OSMFUZZER/patch/fuzzers/mock.patch
cargo build --release
```

## Run

> [!NOTE]
> MOCK does not handle the `--syz-dir` argument correctly. Therefore, you must run MOCK from the `$MOCK/target/release` directory.

Use the following commands to fuzz the Linux kernel with MOCK.

Command:
```bash
cd $MOCK/tools/model_manager
python3 manage.py runserver &
cd $MOCK/target/release
./mock \
  -k $KERNEL/arch/x86/boot/bzImage \
  -d $IMAGE/bullseye.img \
  --ssh-key $IMAGE/bullseye.id_rsa \
  -j 4 \
  --syz-dir syz-bin/ \
  --disable-repro
```