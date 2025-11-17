# HEALER

Original repositopry link: [https://github.com/SunHao-0/healer](https://github.com/SunHao-0/healer).

## Prerequisites

Build the image first, command:

```bash
docker build -t healer:latest -f $OSMFUZZER/docker/Dockerfile.healer $OSMFUZZER/docker
docker up -v volume:/vol --cpus 16 --privileged --name healer-container healer:latest bash
```

Download and build HEALER.

Command:
```bash
cd /vol
git clone https://github.com/SunHao-0/healer && cd healer
git checkout 2efbb44c7dfaaa6749cd1541949b26fd1d2143fa
cargo build --release
```

## Run

Use following commands to fuzz linux kernel via HEALER.

Command:
```bash
cd healer/target/release
./healer
  -k $KERNEL/arch/x86/boot/bzImage \
  -d $IMAGE/bullseye.img \
  --ssh-key $IMAGE/bullseye.id_rsa \
  -j 4 \
  --disable-repro
```