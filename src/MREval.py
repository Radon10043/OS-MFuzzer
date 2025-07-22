"""
Author       : Radon
Date         : 2025-07-22 16:25:40
LastEditors  : Radon
LastEditTime : 2025-07-22 20:58:39
Description  : Evaluate quality of encoded metamorphic relation
"""

import argparse
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Tuple

from utils import *


def get_field_val(line: str, field: str) -> int:
    """Get the value of a specific field in a line.

    Parameters
    ----------
    line : str
        The line from the log of syzkaller(-based) fuzzer
    field : str
        Field name to extract the value from, e.g., "coverage", "exec total"

    Returns
    -------
    int
        The value of the field
    """
    lst = line.split(field + "=")
    if len(lst) < 2:
        FATAL(f"Field '{field}' not found in line: {line}")
    suffix = lst[1].strip()
    val = 0
    for ch in suffix:
        if ch.isdigit():
            val = val * 10 + int(ch)
        else:
            break
    return val


def get_commit(dir: str) -> str:
    """Get the current commit hash of the given directory.

    Parameters
    ----------
    dir : str
        The directory to get the commit hash from.

    Returns
    -------
    str
        The current commit hash of the given directory.
    """
    try:
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=dir,
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )
    except Exception as e:
        FATAL(f"Failed to get commit hash: {e}")
    return commit


def patch_syzkaller(syzkaller: str, patch: str):
    """Patch syzkaller to support metamorphic testing.

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory, must be commit 4b25d554.
    patch : str
        Path to the patch file to apply to syzkaller.
    """
    # Clean the syzkaller repository first
    res = subprocess.run(
        "git checkout . && git clean -fd",
        cwd=syzkaller,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        FATAL(f"Failed to clean syzkaller repository: {res.stderr.decode('utf-8')}")

    try:
        subprocess.run(
            ["git", "apply", patch],
            cwd=syzkaller,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except BaseException as e:
        FATAL(f"Failed to apply patch {patch} to syzkaller: {e}")


def build_syzkaller(syzkaller: str) -> Tuple[int, str, str]:
    """Run `make generate -j` and `make clean all -j` to build the syzkaller.

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory

    Returns
    -------
    Tuple[int, str, str]
        The return code, stderr, and stdout of the build process.
    """
    res = subprocess.run(
        ["make", "generate", "-j"],
        cwd=syzkaller,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        return res.returncode, res.stderr.decode("utf-8"), res.stdout.decode("utf-8")

    res = subprocess.run(
        ["make", "clean", "all", "-j"],
        cwd=syzkaller,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return res.returncode, res.stderr.decode("utf-8"), res.stdout.decode("utf-8")


def add_pseudo_syscall(syzkaller: str, csource: str, syzlang_desc: str, func: str):
    """Add pseudo-syscall to syzkaller, including:
    - Insert C source to syzkaller/executor/common_linux.h;
    - Create metamorphic.txt under syzkaller/sys/linux and write syzlang description;
    - Modify syzkaller/pkg/vminfo/linux_syscalls.go to add corresponding syscall.

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory, must be commit 4b25d554
    csource : str
        C source code of the pseudo-syscall
    syzlang_desc : str
        syzlang description of the pseudo-syscall
    func : str
        Name of the pseudo-syscall function, used to modify linux_syscalls.go
    """
    linux_syscall_file = os.path.join(syzkaller, "pkg", "vminfo", "linux_syscalls.go")
    linux_syscall_content = str()
    common_linux_file = os.path.join(syzkaller, "executor", "common_linux.h")

    # Add syzlang description to syzkaller
    syzlang_fn = os.path.join(syzkaller, "sys", "linux", "metamorphic.txt")
    with open(syzlang_fn, "w", encoding="utf-8") as f:
        f.write(syzlang_desc)

    # Add C source code to common_linux.h
    with open(common_linux_file, "a", encoding="utf-8") as f:
        f.write("#if SYZ_EXECUTOR || __NR_syz_mr\n")
        f.write(csource)
        f.write("\n#endif\n")

    # Add syscall to linux_syscalls.go
    with open(linux_syscall_file, "r", encoding="utf-8") as f:
        linux_syscall_content = f.readlines()
    with open(linux_syscall_file, "w", encoding="utf-8") as f:
        linux_syscall_content[104] += f'"{func}": alwaysSupported,'
        f.writelines(linux_syscall_content)


def dryrun(syzkaller: str, kernel_obj: str, image_obj: str, func: str) -> Tuple[int, int, int]:
    """Dry run the syzkaller to check whether the pseudo-syscall can cover kernel code, and
    whether encoded metamorphic relation is high-quality.

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory
    kernel_obj : str
        Path to the kernel object directory
    image_obj : str
        Path to the image object directory
    func : str
        Name of the pseudo-syscall

    Returns
    -------
    Tuple[int, int, int]
        coverage, total execs, mrvio execs

        Please note that, `mrvio execs` may more than `total execs` since we got the latter from
        the log of syzkaller, while the former is got from counting files under `out_dir/mrvio`,
        time difference may cause the inconsistency.

        TODO: We can modify syzkaller to output `mrvio execs` in the same way as `total execs`
    """
    id = uuid.uuid4().hex[:8]
    os.makedirs(os.path.join(syzkaller, "workdir"), exist_ok=True)
    shutil.rmtree(os.path.join(syzkaller, "workdir", f"out-{id}"), ignore_errors=True)

    imgpath = str()
    idrsapath = str()
    for file in os.listdir(image_obj):
        if file.endswith(".img"):
            imgpath = os.path.join(image_obj, file)
        elif file.endswith(".id_rsa"):
            idrsapath = os.path.join(image_obj, file)

    out_dir = os.path.join(syzkaller, "workdir", f"out-{id}")
    config_path = os.path.join(syzkaller, "workdir", f"config-{id}.json")
    fuzzing_config = {
        "target": "linux/amd64",
        "http": "127.0.0.1:56741",
        "workdir": out_dir,
        "kernel_obj": kernel_obj,
        "image": imgpath,
        "sshkey": idrsapath,
        "syzkaller": syzkaller,
        "procs": 8,
        "type": "qemu",
        "reproduce": False,
        "enable_syscalls": [func],  # Just enable the pseudo-syscall to evaluate its quality
        "vm": {"count": 1, "kernel": os.path.join(kernel_obj, "arch", "x86", "boot", "bzImage"), "cpu": 2, "mem": 2048},
    }
    Path(config_path).write_text(json.dumps(fuzzing_config, indent=4), encoding="utf-8")

    # Dry run
    dryrun_log = os.path.join(out_dir, "dryrun.log")
    try:
        subprocess.run(
            [
                f"{syzkaller}/bin/syz-manager",
                f"-config={config_path}",
            ],
            cwd=syzkaller,
            timeout=120,  # Dry run for 120 seconds
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired as e:  # This is expected
        Path(dryrun_log).write_text(e.stderr.decode("utf-8"), encoding="utf-8")  # type: ignore
    except Exception as e:
        FATAL(f"Failed to run syzkaller: {e}")

    # Get latest coverage, total execs, and mrvio execs
    lines = Path(dryrun_log).read_text(encoding="utf-8").splitlines()
    lines.reverse()
    last_line = str()
    for line in lines:
        if "coverage=" in line:
            last_line = line
            break

    # Check coverage, total execs, and mrvio execs
    coverage = get_field_val(last_line, "coverage")
    exec_total = get_field_val(last_line, "exec total")
    mrvio_execs = 0
    for _, _, files in os.walk(os.path.join(out_dir, "mrvio")):
        mrvio_execs += len(files)
    # shutil.rmtree(out_dir)  # Remove the output directory & config file after dry run
    # os.remove(config_path)

    return coverage, exec_total, mrvio_execs


def main(args):
    # Check whether syzkaller image directory, as well as csource, syzlang description, and patch file
    ACTF("Checking configs ...")
    syzkaller = args.syzkaller
    csource_path = args.csource
    syzlang_path = args.syzlang
    patch = args.patch
    if not os.path.exists(syzkaller):
        FATAL(f"{syzkaller} does not exist.")
    if not os.path.exists(csource_path):
        FATAL(f"{csource_path} does not exist.")
    if not os.path.exists(syzlang_path):
        FATAL(f"{syzlang_path} does not exist.")
    if not os.path.exists(patch):
        FATAL(f"{patch} does not exist.")
    csource = Path(csource_path).read_text(encoding="utf-8")
    syzlang = Path(syzlang_path).read_text(encoding="utf-8")
    func = syzlang.split("(")[0]

    # Check whether vmlinux exist under kernel_obj
    kernel_obj = args.kernel_obj
    vmlinux = os.path.join(kernel_obj, "vmlinux")
    if not os.path.exists(vmlinux):
        FATAL(f"{vmlinux} does not exist, please build first.")

    # Check whether *.img & *.id_rsa exist under image_obj
    image_obj = args.image_obj
    ext_set = set()
    for file in os.listdir(image_obj):
        if file.endswith(".img") or file.endswith(".id_rsa"):
            ext_set.add(file.split(".")[-1])
    if not len(ext_set) == 2:
        FATAL(f"Please ensure that {image_obj} contains both .img and .id_rsa files, but found {ext_set}.")

    # Check whether commit of syzkaller is 4b25d554
    commit = get_commit(syzkaller)[:8]
    if commit != "4b25d554":
        FATAL(f"Current commit of syzkaller is {commit}, but expected 4b25d554. Please checkout first.")
    OKF("Configs are valid!")

    # Patch syzkaller to support metamorphic testing
    ACTF("Patching syzkaller ...")
    patch_syzkaller(syzkaller, patch)

    # Add csource & syzlang desc to syzkaller, then build it
    ACTF("Add pseudo-syscall & build syzkaller ...")
    add_pseudo_syscall(syzkaller, csource, syzlang, func)
    retval, stderr, stdout = build_syzkaller(syzkaller)
    if retval != 0:
        FATAL(f"Failed to build syzkaller: {stderr}\n\n{stdout}")

    # Dryrun for fuzzing, check whether pseudo-syscall can cover kernel code,
    # and if many violations are reported, we should consider that the pseudo-syscall
    # is low-quality
    ACTF("Dry run syzkaller to evaluate the quality of pseudo-syscall ...")
    coverage, total_execs, mrvio_execs = dryrun(syzkaller, kernel_obj, image_obj, func)
    SAYF(f"Coverage: {coverage}, Total Execs: {total_execs}, MRVIO Execs: {mrvio_execs}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate encoded metamorphic relation")
    parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory, must be commit 4b25d554")
    parser.add_argument("--csource", type=str, required=True, help="Path to the C source file of pseudo-syscall")
    parser.add_argument("--syzlang", type=str, required=True, help="Path to the syzlang description of pseudo-syscall")
    parser.add_argument("--kernel_obj", type=str, required=True, help="Path to the kernel object directory")
    parser.add_argument("--image_obj", type=str, required=True, help="Path to the image object directory")
    parser.add_argument("--patch", type=str, default=os.path.join(os.path.dirname(__file__), "..", "patch", "debug.patch"), help="Path to the patch file to apply to syzkaller")
    args = parser.parse_args()
    main(args)
