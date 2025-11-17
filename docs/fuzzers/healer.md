# HEALER

**Original Repository:** [https://github.com/SunHao-0/healer](https://github.com/SunHao-0/healer)

## Prerequisites

First, build the Docker image.

Command:
```bash
docker build -t healer:latest -f $OSMFUZZER/docker/Dockerfile.healer $OSMFUZZER/docker
docker run -v volume:/vol --cpus 16 --privileged --name healer-container healer:latest bash
```

Next, download and build HEALER.

Command:
```bash
cd /vol
git clone https://github.com/SunHao-0/healer && cd healer
git checkout 2efbb44c7dfaaa6749cd1541949b26fd1d2143fa
cargo build --release
```

## Run

Use the following command to fuzz the Linux kernel with HEALER.

Command:
```bash
cd healer/target/release
./healer \
  -k $KERNEL/arch/x86/boot/bzImage \
  -d $IMAGE/bullseye.img \
  --ssh-key $IMAGE/bullseye.id_rsa \
  -j 4 \
  --disable-repro
```