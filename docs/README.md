# SyzMeta

Try to identify metamorphic relations via large language models for drivers in linux kernels. Also perform metamorphic testing for kernel.

## Dependices

- Ubuntu 22.04
- Python 3.12.3
- LLVM 19.1.7

## Install

```sh
sudo apt update
sudo apt install jq
pip install -r tools/syz-meta/requirements.txt
```

*It is recommended to use syz-env to build syzkaller related binaries, see [syzkaller's docs](docs/contributing.md#using-syz-env) for details*

### Install LLVM & Clang from source code

Please run the following commands in the root path of the repository。

```sh
sudo apt update
sudo apt install ninja-build cmake
mkdir build && pushd build
git clone --depth 1 -b llvmorg-19.1.7 https://github.com/llvm/llvm-project.git
mkdir build-clang && pushd build-clang
cmake -G Ninja ../llvm-project/llvm -DLLVM_ENABLE_PROJECTS="clang;clang-tools-extra" -DCMAKE_BUILD_TYPE=Release -DLLVM_BUILD_TESTS=ON
ninja
ninja check       # Test LLVM only.
ninja clang-test  # Test Clang only.
ninja install
```

### Install flatbuffers-v2.0.8

We need install flatbuffers-2.0.8, which is same as syzkaller used, to compile the flatrpc.fbs.

```sh
cd /path/to/flatbuffers-build
sudo apt purge flatbuffers-compiler
wget https://github.com/google/flatbuffers/archive/refs/tags/v2.0.8.tar.gz
tar -xzvf v2.0.8.tar.gz && cd flatbuffers-2.0.8
cmake -G "Unix Makefiles"
make -j
sudo make install
```

## Run

### Involved kernel versions

linux v5.15.189, v6.1.147, v6.6.100, v6.12.40

candidate: linux v5.10.240, v5.4.296, android15-6.6, android14-6.1, android13-5.15, android12-5.4, androidXX-6.12?

### Download syzbot's config files

```bash
wget -O 'v5.15.189.config' 'https://syzkaller.appspot.com/text?tag=KernelConfig&x=f3b1215b3cf4119f'
wget -O 'v6.1.147.config' 'https://syzkaller.appspot.com/text?tag=KernelConfig&x=30b8ca4950f83e04'
wget -O 'v6.6.100.config' 'https://syzkaller.appspot.com/text?tag=KernelConfig&x=293251cfa8d8100'
```

### External corpus construction

Extract all CVE announcements and create a chroma database.

```bash
git clone --mirror https://lore.kernel.org/linux-cve-announce/0 linux-cve-announce/git/0.git
python3 src/corpus.py get_kernel_cves --git_obj linux-cve-announce/git/0.git --outdir workdir/external-corpus
python3 src/corpus.py create_chroma_db --input workdir/external-corpus
```

### Kernel documents preprocessing

Split documents to many document snippets.

**KVM:**

```bash
VERSION=v5.15.189
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/virt/kvm/api.rst --outdir workdir/kernel-docs/$VERSION/kvm/api
```

**autofs:**

```bash
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/filesystems/autofs.rst --outdir workdir/kernel-docs/$VERSION/autofs/autofs
```

**ppp:**

```bash
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/networking/ppp_generic.rst --outdir workdir/kernel-docs/$VERSION/ppp/ppp_generic
```

fuse:

```bash
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/filesystems/fuse.rst --outdir workdir/kernel-docs/$VERSION/fuse/fuse
```

**ptmx:**

```bash
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/filesystems/devpts.rst --outdir workdir/kernel-docs/$VERSION/ptmx/devpts
```

**rdma_cm:**

```bash
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/infiniband/core_locking.rst --outdir workdir/kernel-docs/$VERSION/rdma_cm/core_locking
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/infiniband/ipoib.rst --outdir workdir/kernel-docs/$VERSION/rdma_cm/ipoib
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/infiniband/opa_vnic.rst  --outdir workdir/kernel-docs/$VERSION/rdma_cm/opa_vnic
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/infiniband/tag_matching.rst --outdir workdir/kernel-docs/$VERSION/rdma_cm/tag_matching
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/infiniband/user_mad.rst --outdir workdir/kernel-docs/$VERSION/rdma_cm/user_mad
python3 src/rst_analyzer.py --file ../linux/$VERSION/Documentation/infiniband/user_verbs.rst --outdir workdir/kernel-docs/$VERSION/rdma_cm/user_verbs
```


### MR Identification

Create a json file (e.g. `MRIden.cfg.json`), write the following content:

```json
{
    "identifier": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-xxx",
        "framework": "openai",
        "model": "deepseek-chat",
        "temperature": 0.5,     // Optional, default as 0.5
        "stream": true,         // Optional, default as false
        "prompts": {
            "system": "/path/to/SyzMeta/tools/syz-meta/data/prompts/identifier/system.md",
            "user": [
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/identifier/init.md",
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/identifier/follow.md"
            ]
        }
    },
    "calibrator": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-xxx",
        "framework": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,     // Optional, default as 0.5
        "stream": true,         // Optional, default as false
        "prompts": {
            "system": "/path/to/SyzMeta/tools/syz-meta/data/prompts/calibrator/system.md",
            "user": [
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/calibrator/vanilla.md"
            ]
        }
    },
    "max_iter": 10,
    "output": "/path/to/SyzMeta/workdir/MRs/autofs-1/iden",
    "specification": "/path/to/SyzMeta/tools/syz-meta/data/spec/linux-v6.2/autofs/1.purpose.md",
    "driver_name": "autofs"
}
```

MRIden.py is used to identify and calibrate MR via LLMs. Explanation of each parameters is as follows:

- identifier: store the settings of identifier model, specifically:
  - base_url: base URL for access model, such as DeepSeek.
  - api_key: your API key for accessing model, usally prefix with "sk-".
  - base_model: based on which series of models to query, such as DeepSeek, GPT (case insensitive).
  - temperature: the temperature wanna used, the lower temperature, the more stable and accurate the LLM's response.
  - stream: whether to enable streaming response. If enabled, the output of LLM will be printed in streaming mode.
  - prompts: prompts that will send to LLM, categorized into system prompt and user prompt. This project supports one system prompt and multi user prompts. Each prompt is stored in a markdown file and its path is presented in the json file, the script will read and load each prompt's content.
- calibrator: store the settings of calibrator model, its content is same as identifier.
- max_iter: maximum iteration for discussing.
- output: output directory that stores query messages, discussion result, etc.
- specification: path of specification file that used in the LLM query (We convert html content to markdown via [devtool.tech](https://devtool.tech/en)).
- driver_name: Name of driver under test.

### MR Implementation

Create a json file (e.g. `MRImpl.json`), write the following content:

```json
{
    "c_programmer": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-xxxx",
        "framework": "openai",
        "model": "deepseek-r1",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/path/to/SyzMeta/tools/syz-meta/data/prompts/programmer/c/system.md",
            "user": [
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/programmer/c/init.md",
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/programmer/c/follow.md"
            ]
        }
    },
    "syzlang_programmer": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-xxxx",
        "framework": "openai",
        "model": "deepseek-r1",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/path/to/SyzMeta/tools/syz-meta/data/prompts/programmer/syzlang/system.md",
            "user": [
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/programmer/syzlang/init.md",
                "/path/to/SyzMeta/tools/syz-meta/data/prompts/programmer/syzlang/follow.md"
            ]
        }
    },
    "mr_desc": "/path/to/SyzMeta/workdir/MRs/autofs-1/iden/mr_final.md",
    "max_iter": 10,
    "output": "/path/to/SyzMeta/workdir/MRs/autofs-1/impl",
    "compiler": "gcc",
    "syzkaller": "/path/to/syzkaller"
}
```

MRImpl.py is used to generate C code and corresponding syzlang description of an MR. Explanation of each parameters is as follows:

- Meaning of base_url, api_key, framework, temperature, prompts, stream, and max_iter are same as MR Identification.
- mr_desc: path of markdown file that store the description of an MR. Note the MR should be placed in a markdown code block.
- compiler: specificed compiler that used to compile the generated C code, e.g. gcc.
- syzkaller: path of syzkaller, which used to verify whether the generated MR implementation and syzlang description can be successfully integrated into it.

### Metamorphic Testing

Create a json file (e.g. `SyzMeta.cfg.json`) and write the following content:

```json
{
    "meta_rel": "/path/to/SyzMeta/workdir/syz-meta/out-MRImpl1/mr.h",
    "cdir": "/path/to/SyzMeta/workdir/syzkaller/out/corpus-c",
    "out": "/path/to/SyzMeta/workdir/syz-meta/out-MT",
    "kernel": "/path/to/linux-kernel/v6.2",
    "compiler": "clang",
    "image": "/path/to/Debian/bullseye.img",
    "sshkey": "/path/to/Debian/bullseye.id_rsa"
}
```

tools/syz-meta/src/mt.go is used to insert the metamorphosis relation implementation into C source files, and compile, execute, and collect coverage for the original and modified files. Explanation of each parameters is as follows:

- meta_rel: path of the metamorphic relation implementation (.h file), generated by `MRImpl.py` stage.
- cdir: directory of C source files. Use `syz-db unpack` to generate syzlang files from `corpus.db`, and use `syz-prog2c` to transfer syzlang files to C source files.
- out: path of output directory.
- kernel: path of kernel directory.
- compiler: compiler that used to build binaries after MR insertion. Default CFALGS is `-static`.
- image: path of image file.
- sshkey: path of ssh key file, which used to connect VM, copy binaries into it, and execute commands.

Build syzkaller under SyzMeta:

```sh
make -C syzkaller all
```

## References

[1] [https://clang.llvm.net.cn/docs/LibASTMatchersTutorial.html](https://clang.llvm.net.cn/docs/LibASTMatchersTutorial.html)

[2] [https://github.com/google/syzkaller](https://github.com/google/syzkaller)

[3] [https://devtool.tech/en](https://devtool.tech/en)