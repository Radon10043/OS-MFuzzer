# MoonShine

Original repositopry link: [https://github.com/shankarapailoor/moonshine](https://github.com/shankarapailoor/moonshine).

## Prerequisites

Build the image first, command:

```bash
docker build -t moonshine:latest -f $OSMFUZZER/docker/Dockerfile.moonshine $OSMFUZZER/docker
docker up -v volume:/vol --cpus 16 --privileged --name moonshine-container moonshine:latest bash
```

Download and build MoonShine.

Command:
```bash
cd /vol
git clone https://github.com/shankarapailoor/moonshine && cd moonshine
git checkout 95e5f6dfd2760a9d763fc2bc90623c9e1e74e804
go mod init github.com/shankarapailoor/moonshine
go get github.com/google/syzkaller@f48c20b8f9b2a6c26629f11cc15e1c9c316572c8
go install golang.org/x/tools/cmd/goyacc@v0.27.0
go mod vendor
git checkout vendor/github.com/google/syzkaller/prog/
make
```

## Run

Download `sampletraces.tar.gz` from Generate corpus.db for syzkaller.

Command:
```bash
cd moonshine
cp /home/sampletraces.tar.gz .
tar -xzvf ../sampletraces.tar.gz
./bin/moonshine -dir sampletraces/ -distill getting-started/distill.json
```

Copy corpus.db to the workdir of syzkllaer to start fuzzing.

```bash
cd $SYZKALLER
mkdir -p workdir/moonshine-out
cp $MOONSHINE/corpus.db workdir/moonshine-out/
$SYZKALLER/bin/syz-manager -config=$CONFIG
```