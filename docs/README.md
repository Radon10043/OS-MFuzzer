# OS-MFuzzer

OS-MFuzzer is an issue-driven LLM-enabled metamorphic fuzzing approach for operating system kernels, implemented based on syzkaller.

This document detailes the steps of setting up OS-MFuzzer and using it for metamorphic fuzzing.

## Prerequisites

We recommend to use docker:

Build image for OS-MFuzzer:
```bash
mkdir volume && cd volume
mkdir docker
git clone --recurse-submodules https://github.com/XXX/XXX OS-MFuzzer
wget -P volume/OS-MFuzzer/docker https://go.dev/dl/go1.23.6.linux-amd64.tar.gz
wget -P volume/OS-MFuzzer/docker https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz
wget -P volume/OS-MFuzzer/docker https://github.com/google/flatbuffers/archive/refs/tags/v2.0.8.tar.gz
docker build -t os-mfuzzer:latest -f volume/OS-MFuzzer/docker/Dockerfile.myfuzz volume/OS-MFuzzer/docker
```

Let's start a container with a mounted volume so that we can save the data presistently.

Command:
```bash
docker up -d -v volume:/vol --cpus 16 --privileged --name os-mfuzzer-container os-mfuzzer:latest tail -f /dev/null
docker exec -it os-mfuzzer-container bash
```

In the container, let's build linux kernel first, we use v6.12.40 as an example.

Command:
```bash
cd /vol
mkdir linux && cd linux
git clone https://github.com/gregkh/linux stable
cp -r stable v6.12.40
git -C v6.12.40 checkout v6.12.40
```

Let's build linux kernel using syzbot's config, you can get config file from OS-MFuzzer's repository,

Command:
```bash
cd v6.12.40
cp $OSMFuzzer/configs/kernel/linux.v6.12.40.config .config
make CC=clang olddefconfig
make CC=clang -j16
```

We also need to build image to run kernel.

Command:
```bash
cd /vol
mkdir -p images/Debian
cd images/Debian
cp $OSMFUZZER/scripts/create-image.sh
./create-image.sh
```

# Usage (Simplified)

Let's build OS-MFuzzer for metamorphic fuzzing. We need integrated generated EKMRs for metamorphic fuzzing, you can integrate it by patches provided by us. Use following command to integrate EKMRs generate based on part of documents from v6.12.40. Additionally, there are many patches for using, check them [here](/docs/Patch.md).

Command:
```bash
cd $OSMFUZZER
make restore patch PATCH=patch/pseudo-syscall/linux.v6.12.40.patch
make -C syzkaller clean generate all -j16
```

EKMRs of linux v6.12.40 has integrated into OS-MFuzzer/syzkaller, you can run it as normal syzkaller.

```bash
mkdir workdir
export WORKDIR=/vol/OS-MFuzzer/workdir
export KERNEL=/vol/linux/v6.12.40
export IMAGE=/vol/images/Debian
export SYZKALLER=/vol/OS-MFuzzer/syzkaller
export VMCOUNT=4
cat configs/fuzz/linux.cfg | envsubst > workdir/test.cfg
$OSMFUZZER/syzkaller/bin/syz-manager -config=workdir/test.cfg
```

[Click me](/docs/fuzzers/README.md) to check baseline fuzzer's installation.

## Usage (Completed)

This section details how to use OS-MFuzzer for kernel MR synthesizing, encoding, integrating, and metamorphic fuzzing.

### kernel MR Synthesis

#### External corpus construction

Extract all CVE announcements and create a chroma database.

```bash
git clone --mirror https://lore.kernel.org/linux-cve-announce/0 linux-cve-announce/git/0.git
python3 src/corpus.py get_kernel_cves --git_obj linux-cve-announce/git/0.git --outdir workdir/external-corpus
python3 src/corpus.py create_chroma_db --input workdir/external-corpus
```

#### Kernel documents preprocessing

Split documents to documents chunks for better targeted manner. We use `Documentation/kvm/api.rst` as an example. Folders will be created for each document chunk, under the folder, `content.txt` saves section's content.

Command:
```bash
python3 src/rst_analyzer.py \
        --file /vol/linux/v6.12.40/Documentation/virt/kvm/api.rst \
        --outdir workdir/kernel-docs/v6.12.40/kvm/api
```

#### Synthesize kernel MR batchlly

You can run `src/experiment.py` to synthesize kernel MRs batchlly. The program will travese all `content.txt` to synthesize MRs.

Command:
```bash
python3 $OSMFUZZER/src/experiment.py \
            iden \
            --specdir $OSMFUZZER/workdir/kernel-docs \
            --corpus $OSMFUZZER/workdir/external-corpus
```

#### Synthesize kernel MR one by one

Create a json file (e.g. `MRSynt.cfg.json`), write the following content:

```json
{
    "identifier": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "xxx",
        "framework": "openai",
        "model": "gemini-2.5-pro",
        "temperature": 0.5,     // Optional, default as 0.5
        "stream": true,         // Optional, default as false
        "prompts": {
            "system": "/vol/OS-MFuzzer/data/prompts/identifier/system.md",
            "user": [
                "/vol/OS-MFuzzer/data/prompts/identifier/init.md",
                "/vol/OS-MFuzzer/data/prompts/identifier/follow.md"
            ]
        }
    },
    "calibrator": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "api_key": "xxx",
        "framework": "openai",
        "model": "o3",
        "temperature": 0.2,     // Optional, default as 0.5
        "stream": true,         // Optional, default as false
        "prompts": {
            "system": "/vol/OS-MFuzzer/data/prompts/calibrator/system.md",
            "user": [
                "/vol/OS-MFuzzer/data/prompts/calibrator/vanilla.md"
            ]
        }
    },
    "max_iter": 10,
    "output": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/v6.12.40/kvm/api/1.-General-description/iden",
    "specification": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/v6.12.40/kvm/api/1.-General-description/content.txt",
    "driver_name": "kvm"
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
- specification: path of specification file that used in the LLM query.
- driver_name: Name of corresponding driver or subsystem.

### Encode kernel MR

We need clone syzkaller and check it to `4b25d554`.

Command:
```bash
cd /vol
git clone https://github.com/google/syzkaller
git -C syzkaller checkout 4b25d554
cd OS-MFuzzer
```

#### Batchlly

Also run `src/experiment.py` to encode kernel MR batchlly. Program will traverse each `iden` folder and create `impl` folder under the same root.

Command:
```bash
python3 $OSMFUZZER/src/experiment.py \
            impl \
            --idendir $OSMFUZZER/workdir/kernel-docs \
            --syzkaller /vol/syzkaller
```

##### One by one

Create a json file (e.g. `MREncode.json`), write the following content:

```json
{
    "c_programmer": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "xxx",
        "framework": "openai",
        "model": "gemini-2.5-pro",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/vol/OS-MFuzzer/tools/syz-meta/data/prompts/programmer/c/system.md",
            "user": [
                "/vol/OS-MFuzzer/tools/syz-meta/data/prompts/programmer/c/init.md",
                "/vol/OS-MFuzzer/tools/syz-meta/data/prompts/programmer/c/follow.md"
            ]
        }
    },
    "syzlang_programmer": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "xxx",
        "framework": "openai",
        "model": "gemini-2.5-pro",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/vol/OS-MFuzzer/tools/syz-meta/data/prompts/programmer/syzlang/system.md",
            "user": [
                "/vol/OS-MFuzzer/tools/syz-meta/data/prompts/programmer/syzlang/init.md",
                "/vol/OS-MFuzzer/tools/syz-meta/data/prompts/programmer/syzlang/follow.md"
            ]
        }
    },
    "mr_desc": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/v6.12.40/kvm/api/1.-General-description/iden/mr_final.md",
    "max_iter": 10,
    "output": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/v6.12.40/kvm/api/1.-General-description/impl",
    "compiler": "gcc",
    "syzkaller": "/vol/syzkaller"
}
```

MRImpl.py is used to generate C code and corresponding syzlang description of an MR. Explanation of each parameters is as follows:

- Meaning of base_url, api_key, framework, temperature, prompts, stream, and max_iter are same as MR Identification.
- mr_desc: path of markdown file that store the description of an MR. Note the MR should be placed in a markdown code block.
- compiler: specificed compiler that used to compile the generated C code, e.g. gcc.
- syzkaller: path of syzkaller, which used to verify whether the generated MR implementation and syzlang description can be successfully integrated into it.

### Trial run encoded kernel MRs

Also use `src/experiment.py` to trial run encoded kernel MRs batchlly or use `src/MREval.py` to specify want to trail run ones.

Command:
```bash
python3 src/experiment.py \
            eval \
            --impldir workdir/kernel-docs \
            --syzkaller /vol/syzkaller \
            --kernel_obj /vol/linux/v6.12.40 \
            --image_obj /vol/images/Debian
```

### Integrate encoded kernel MRs

Also use `src/experiment.py` to integrate batchlly or use `src/MRIntg.py` to specify which EKMRs want to integrate. If using `src/experiment.py`, program will traverse and get `mr.h` under `--impl_root`. Further, only high-quality will be integrated into syzkaller default, use `--allin` option to integrate all encode kernel MRs.

Command:
```bash
python3 src/experiment.py \
            integrate \
            --impl_root workdir/kernel-docs \
            --syzkaller $OSMFUZZER/syzkaller \
            --clean
```

Or use `src/MRIntg.py` to integrate specifically encode kernel MRs.

Command:
```bash
python3 src/MRIntg.py
            --syzkaller $OSMFUZZER/syzkaller
            --impls /vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/v6.12.40/kvm/api/1.-General-description/impl/mr.h
            ...
```

Build syzkaller, which is integrated encoded kernel MRs.

Command:
```bash
make -C syzkaller clean generate all -j16
```

> [!NOTE]
> We cannot guarantee that collisions among encoded kernel MRs will be completely eliminated after integration. Some collisions may need to be resolved manually based on error messages.

### Metamorphic Fuzzing

Just as mentioned in [Usage (Simplified)](#usage-simplified).

Command:
```bash
mkdir workdir
export WORKDIR=/vol/OS-MFuzzer/workdir
export KERNEL=/vol/linux/v6.12.40
export IMAGE=/vol/images/Debian
export SYZKALLER=/vol/OS-MFuzzer/syzkaller
export VMCOUNT=4
cat configs/fuzz/linux.cfg | envsubst > workdir/test.cfg
$OSMFUZZER/syzkaller/bin/syz-manager -config=workdir/test.cfg
```