# If host has proxy, you can run "docker run --network host" to make container use host's proxy.

FROM ubuntu:22.04

WORKDIR /home
SHELL [ "/bin/bash", "-c" ]

ENV GOPATH=/usr/local/go/bin
ENV LLVM_HOME=/home/LLVM-19.1.7-Linux-X64
ENV PATH=$GOPATH:${LLVM_HOME}/bin:$PATH

# Enable it to avoid "server certificate verification failed"
# ENV GIT_SSL_NO_VERIFY=1

# Use Tsinghua University mirror for faster package downloads if necessary
# RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
#     echo "deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list

# Download following files to the tools/syz-meta/docker and build the image by COPY command will save time:
# go1.23.6.linux-amd64.tar.gz, LLVM-19.1.7-Linux-X64.tar.xz, v2.0.8.tar.gz (flatbuffers-v2.0.8)
COPY go1.23.6.linux-amd64.tar.gz LLVM-19.1.7-Linux-X64.tar.xz v2.0.8.tar.gz /home/
RUN apt-get update
RUN apt-get install -y sudo wget curl git vim build-essential make gcc g++ flex bison bc debootstrap
RUN apt-get install -y qemu-system-x86 xz-utils cmake gdb libdw-dev libssl-dev sqlite3 libsqlite3-dev
RUN apt-get install -y python3 python3-pip python3-dev language-pack-en-base rsync file devscripts equivs
RUN apt-get install -y config-package-dev debhelper-compat repo adb fastboot gcc-aarch64-linux-gnu
RUN apt-get install -y g++-aarch64-linux-gnu qemu-system-aarch64 libncurses5 cloc
RUN pip install dotenv chromadb GitPython marko clang==19.1.7 google-genai isort unstructured markdown
RUN pip install langchain-text-splitters langchain-community langgraph langchain-core langchain-openai
RUN pip install langchain-google-genai langchain-chroma docutils anthropic
RUN groupadd --system kvm || true
RUN groupadd --system cvdnetwork || true
RUN groupadd --system render || true

# Download
RUN wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz && \
    wget -nc https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz && \
    wget -nc https://github.com/google/flatbuffers/archive/refs/tags/v2.0.8.tar.gz

# Install golang-1.23.6
RUN tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz && \
    rm go1.23.6.linux-amd64.tar.gz

# Install LLVM-19.1.7 (binary)
RUN tar -xvf LLVM-19.1.7-Linux-X64.tar.xz && \
    rm LLVM-19.1.7-Linux-X64.tar.xz

# Install flatbuffers-2.0.8
RUN tar -xzvf v2.0.8.tar.gz && \
    pushd flatbuffers-2.0.8 && \
    cmake -G "Unix Makefiles" && \
    make -j && \
    make install && \
    popd && \
    rm -rf v2.0.8.tar.gz

# Install android-cuttlefish
RUN git clone https://github.com/google/android-cuttlefish
COPY cuttlefish.patch /home/android-cuttlefish/
WORKDIR /home/android-cuttlefish
RUN git checkout v1.15.0 && \
    git apply cuttlefish.patch
RUN tools/buildutils/installbazel.sh
RUN tools/buildutils/build_packages.sh
RUN dpkg -i ./cuttlefish-base_*_*64.deb || apt-get install -f -y
RUN dpkg -i ./cuttlefish-user_*_*64.deb || apt-get install -f -y
RUN usermod -aG kvm,cvdnetwork,render root

WORKDIR /home

# Donwload mockery
RUN go install github.com/vektra/mockery/v2@v2.45.1

# Download syzkaller & SyzMeta
RUN git clone https://github.com/google/syzkaller
RUN --mount=type=secret,id=github_token \
    SECRET_CONTENT=$(cat /run/secrets/github_token) && \
    git clone -b dev --recurse-submodules https://Radon10043:${SECRET_CONTENT}@github.com/Radon10043/SyzMeta.git

# Patch fuzzers
RUN git -C syzkaller checkout 4b25d554 && \
    git -C syzkaller apply /home/SyzMeta/patch/offline.patch && \
    git -C SyzMeta/syzkaller apply /home/SyzMeta/patch/offline.patch

# Build fuzzers
RUN make -C syzkaller generate -j`nproc` && \
    make -C syzkaller clean all -j`nproc`
RUN make -C SyzMeta/syzkaller generate -j`nproc` && \
    make -C SyzMeta/syzkaller clean all -j`nproc`

# Build image
RUN mkdir Debian && \
    cp /home/syzkaller/tools/create-image.sh Debian/ && \
    cd Debian && \
    ./create-image.sh

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