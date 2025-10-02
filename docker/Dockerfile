FROM ubuntu:22.04

WORKDIR /home
SHELL [ "/bin/bash", "-c" ]

ENV GOPATH=/usr/local/go/bin
ENV LLVM_HOME=/home/LLVM-19.1.7-Linux-X64
ENV PATH=$GOPATH:${LLVM_HOME}/bin:$PATH
ENV TZ=Asia/Shanghai

# Download following files to the tools/syz-meta/docker and build the image by COPY command will save time:
# go1.23.6.linux-amd64.tar.gz, LLVM-19.1.7-Linux-X64.tar.xz, v2.0.8.tar.gz (flatbuffers-v2.0.8)
COPY go1.23.6.linux-amd64.tar.gz LLVM-19.1.7-Linux-X64.tar.xz v2.0.8.tar.gz /home/

# Install basic packages
# TODO: Some packages can be removed to reduce image size
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
RUN apt-get install -y sudo wget curl git vim build-essential make gcc g++ flex bison bc debootstrap
RUN apt-get install -y qemu-system-x86 xz-utils cmake gdb libdw-dev libssl-dev sqlite3 libsqlite3-dev
RUN apt-get install -y python3 python3-pip python3-dev language-pack-en-base rsync file devscripts equivs
RUN apt-get install -y config-package-dev debhelper-compat adb fastboot libncurses5 cloc openssh-server
RUN apt-get install -y dwarves unzip

# Install Vulkan-related packages to boost performance of cuttlefish virtual device
RUN apt-get install -y vulkan-tools libegl1-mesa libegl1 libgles2-mesa libgles2 libvulkan1

# Install python packages
RUN pip install dotenv chromadb GitPython marko clang==19.1.7 google-genai isort unstructured markdown
RUN pip install langchain-text-splitters langchain-community langgraph langchain-core langchain-openai
RUN pip install langchain-google-genai langchain-chroma docutils anthropic

# Create necessary groups
RUN groupadd --system kvm || true
RUN groupadd --system cvdnetwork || true
RUN groupadd --system render || true

# Install golang-1.23.6
RUN wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz && \
    rm go1.23.6.linux-amd64.tar.gz

# Install LLVM-19.1.7 (binary)
RUN wget -nc https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz && \
    tar -xvf LLVM-19.1.7-Linux-X64.tar.xz && \
    rm LLVM-19.1.7-Linux-X64.tar.xz

# Install flatbuffers-2.0.8
RUN wget -nc https://github.com/google/flatbuffers/archive/refs/tags/v2.0.8.tar.gz && \
    tar -xzvf v2.0.8.tar.gz && \
    pushd flatbuffers-2.0.8 && \
    cmake -G "Unix Makefiles" && \
    make -j && \
    make install && \
    popd && \
    rm -rf v2.0.8.tar.gz

# Install repo
RUN curl https://storage.googleapis.com/git-repo-downloads/repo > /usr/bin/repo && \
    chmod a+x /usr/bin/repo

# Download syzkaller & SyzMeta
RUN git clone https://github.com/google/syzkaller && \
    cd syzkaller && \
    git checkout 4b25d554e5643186ba6a09429089ac0275f7573b
RUN --mount=type=secret,id=github_token \
    SECRET_CONTENT=$(cat /run/secrets/github_token) && \
    git clone -b dev --recurse-submodules https://Radon10043:${SECRET_CONTENT}@github.com/Radon10043/SyzMeta.git

# Build fuzzers
RUN make -C syzkaller generate -j`nproc` && \
    make -C syzkaller clean all -j`nproc`
RUN make -C SyzMeta/syzkaller generate -j`nproc` && \
    make -C SyzMeta/syzkaller clean all -j`nproc`

# Build image
RUN mkdir Debian && \
    cp /home/SyzMeta/syzkaller/tools/create-image.sh Debian/ && \
    cd Debian && \
    ./create-image.sh

# Install android-cuttlefish
RUN git clone https://github.com/google/android-cuttlefish && \
    cp /home/SyzMeta/patch/cuttlefish.patch /home/android-cuttlefish/
WORKDIR /home/android-cuttlefish
RUN git checkout v1.16.0 && \
    git apply cuttlefish.patch
RUN tools/buildutils/installbazel.sh
RUN tools/buildutils/build_packages.sh
RUN dpkg -i ./cuttlefish-base_*_*64.deb || apt-get install -f -y
RUN dpkg -i ./cuttlefish-user_*_*64.deb || apt-get install -f -y
RUN usermod -aG kvm,cvdnetwork,render root

WORKDIR /home