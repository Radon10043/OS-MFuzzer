# MOCK

Original repositopry link: [https://github.com/m0ck1ng/mock/tree/main](https://github.com/m0ck1ng/mock/tree/main).

## Prerequsits

Build the image for MOCK first.

Command:
```bash
docker build -t mock:latest -f $OSMFUZZER/docker/Dockerfile.mock $OSMFUZZER/docker
docker up -v volume:/vol --cpus 16 --privileged --name mock-container mock:latest bash
```

Download, patch, and build MOCK.

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
> Mock cannot process --syz-dir correctly, we have to run MOCK under $MOCK/target/release.

Run following command to fuzz linux kernel via MOCK.

Command:
```bash
cd $MOCK/tools/model_manager
python3 manage.py runserver &
cd $MOCK/target/release
./healer
  -k $KERNEL/arch/x86/boot/bzImage \
  -d $IMAGE/bullseye.img \
  --ssh-key $IMAGE/bullseye.id_rsa \
  -j 4 \
  --syz-dir syz-bin/ \
  --disable-repro
```