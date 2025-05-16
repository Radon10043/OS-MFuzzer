FROM ubuntu:22.04

WORKDIR /home
SHELL [ "/bin/bash", "-c" ]

ENV GOPATH=/usr/local/go/bin
ENV LLVM_HOME=/home/LLVM-19.1.7-Linux-X64
ENV PATH=$PATH:$GOPATH:${LLVM_HOME}/bin

# Download following files to the tools/syz-meta/docker and build the image by COPY command will save time:
# go1.23.6.linux-amd64.tar.gz, Python-3.12.3.tar.xz, LLVM-19.1.7-Linux-X64.tar.xz, v2.0.8.tar.gz (flatbuffers-v2.0.8)
# TODO: Install SyzMeta
COPY go1.23.6.linux-amd64.tar.gz Python-3.12.3.tar.xz LLVM-19.1.7-Linux-X64.tar.xz v2.0.8.tar.gz /home/
COPY linux /home/
RUN apt update && \
    apt install -y sudo wget curl git vim make gcc g++ flex bison libffi-dev libncurses-dev libelf-dev libssl-dev bc debootstrap qemu-system-x86 xz-utils cmake && \
    # Download
    wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz && \
    wget -nc https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tar.xz && \
    wget -nc https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz && \
    wget -nc https://github.com/google/flatbuffers/archive/refs/tags/v2.0.8.tar.gz && \
    # Install golang-1.23.6
    tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz && \
    rm go1.23.6.linux-amd64.tar.gz && \
    # Install Python-3.12.3
    tar xvf Python-3.12.3.tar.xz && \
    pushd Python-3.12.3 && \
    ./configure --enable-optimizations && \
    make -j && \
    make install && \
    popd && \
    rm -rf Python-3.12.3 Python-3.12.3.tar.xz && \
    # Install LLVM-19.1.7 (binary)
    tar -xvf LLVM-19.1.7-Linux-X64.tar.xz && \
    rm LLVM-19.1.7-Linux-X64.tar.xz && \
    # Install flatbuffers-2.0.8
    tar -xzvf v2.0.8.tar.gz && \
    pushd flatbuffers-2.0.8 && \
    cmake -G "Unix Makefiles" && \
    make -j && \
    make install && \
    popd && \
    # Download & build syzkaller
    rm -rf flatbuffers-2.0.8 v2.0.8.tar.gz && \
    git clone https://github.com/google/syzkaller && \
    pushd syzkaller && \
    git checkout 4b25d554e5643186ba6a09429089ac0275f7573b && \
    make generate -j && make all -j && \
    popd && \
    # Create Debian Bullseye Linux image
    mkdir Debian && pushd Debian && \
    cp ../syzkaller/tools/create-image.sh .

# Please note:
# If host has proxy, you can run "docker run --network host" to make container use host's proxy.