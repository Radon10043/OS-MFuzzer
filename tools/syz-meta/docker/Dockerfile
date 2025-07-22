# If host has proxy, you can run "docker run --network host" to make container use host's proxy.

FROM ubuntu:22.04

WORKDIR /home
SHELL [ "/bin/bash", "-c" ]

ENV GOPATH=/usr/local/go/bin
ENV LLVM_HOME=/home/LLVM-19.1.7-Linux-X64
ENV PATH=$PATH:$GOPATH:${LLVM_HOME}/bin

# Download following files to the tools/syz-meta/docker and build the image by COPY command will save time:
# go1.23.6.linux-amd64.tar.gz, Python-3.12.3.tar.xz, LLVM-19.1.7-Linux-X64.tar.xz, v2.0.8.tar.gz (flatbuffers-v2.0.8)
COPY go1.23.6.linux-amd64.tar.gz Python-3.12.3.tar.xz LLVM-19.1.7-Linux-X64.tar.xz v2.0.8.tar.gz /home/
RUN apt update && \
    apt install -y sudo wget curl git vim build-essential make gcc g++ flex bison libffi-dev libncurses-dev libelf-dev libssl-dev bc debootstrap qemu-system-x86 xz-utils cmake gdb libdw-dev && \
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
    rm -rf flatbuffers-2.0.8 v2.0.8.tar.gz

# After the container is constructed, we need to build the Debian, Linux kernels, syzkaller and SyzMeta.
# It is recommended to save above contents in a docker volume. We can run the following commands on the host:
# **NOTE: THE FOLLOWING COMMANDS ARE JUST EXAMPLES, PLEASE MODIFY THEM ACCORDING TO THE ACTUAL SITUATION**
# TODO: Write them in a script
#
# docker volume create vol-syzmeta
# docker run -d -v /vol-syzmeta:/vol --cpuset-cpus 16-19 --network host --privileged --name kernel-fuzzing syzmeta:v1 tail -f /dev/null
# docker exec --workdir /vol git clone https://github.com/google/syzkaller
# docker exec --workdir /vol/syzkaller git checkout 4b25d554
# docker exec --workdir /vol git clone https://github.com/Radon10043/SyzMeta
# docker exec --workdir /vol cp SyzMeta/tools/syz-meta/docker/linux .
# docker exec --workdir /vol mkdir Debian
# docker exec --workdir /vol/Debian cp SyzMeta/tools/create-image.sh .
# docker exec --workdir /vol/Debian create-image.sh
# docker exec --workdir /vol/linux ./build.sh v5.15 syzbot
# docker exec --workdir /vol/linux ./build.sh v6.1 syzbot
# docker exec --workdir /vol/linux ./build.sh v6.2 syzbot
# docker exec --workdir /vol/linux ./build.sh v6.7 syzbot