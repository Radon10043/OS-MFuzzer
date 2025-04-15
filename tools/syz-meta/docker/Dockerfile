FROM ubuntu:22.04

WORKDIR /home
SHELL [ "/bin/bash", "-c" ]

# Download following files to the tools/syz-meta/docker and build the image by COPY command will save time:
# go1.23.6.linux-amd64.tar.gz, Python-3.12.3.tar.xz, LLVM-19.1.7-Linux-X64.tar.xz
COPY go1.23.6.linux-amd64.tar.gz Python-3.12.3.tar.xz LLVM-19.1.7-Linux-X64.tar.xz /home/
RUN apt update && \
    apt install -y sudo wget curl git vim make gcc g++ flex bison libffi-dev libncurses-dev libelf-dev libssl-dev bc debootstrap qemu-system-x86 xz-utils && \
    # Install docker
    curl -fsSL https://test.docker.com -o test-docker.sh && \
    chmod +x test-docker.sh && \
    ./test-docker.sh && \
    sed -i "s/-Hn/-n/g" /etc/init.d/docker && \
    rm test-docker.sh && \
    # Install golang-1.23.6
    wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz && \
    rm go1.23.6.linux-amd64.tar.gz && \
    # Install Python-3.12.3
    wget -nc https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tar.xz && \
    tar xvf Python-3.12.3.tar.xz && \
    pushd Python-3.12.3 && \
    ./configure --enable-optimizations && \
    make -j && \
    make install && \
    popd && \
    rm -rf Python-3.12.3 Python-3.12.3.tar.xz

ENV GOPATH=/usr/local/go/bin
ENV PATH=$PATH:$GOPATH

# Please note:
# If you want to use docker in the container, you need run "docker run --privileged ..." to create the container.
# If host has proxy, you can run "docker run --network host" to make container use host's proxy.
# After the images build success, you need run the folloing commands in the container:
# docker pull gcr.io/syzkaller/env