import os
import subprocess
import time
from pathlib import Path
from typing import Tuple

import marko
from marko.md_renderer import MarkdownRenderer


#######################
### Terminal Colors ###
#######################
class TerminalColors:
    cBLK = "\033[0;30m"
    cRED = "\033[0;31m"
    cGRN = "\033[0;32m"
    cBRN = "\033[0;33m"
    cBLU = "\033[0;34m"
    cMGN = "\033[0;35m"
    cCYA = "\033[0;36m"
    cLGR = "\033[0;37m"
    cGRA = "\033[1;90m"
    cLRD = "\033[1;91m"
    cLGN = "\033[1;92m"
    cYEL = "\033[1;93m"
    cLBL = "\033[1;94m"
    cPIN = "\033[1;95m"
    cLCY = "\033[1;96m"
    cBRI = "\033[1;97m"
    cRST = "\033[0m"


###############################
### Debug & error functions ###
###############################
def SAYF(msg: str):
    print(msg, end="")


def WARNF(msg: str):
    SAYF(TerminalColors.cYEL + "[!] " + TerminalColors.cRST + msg + "\n")


def ACTF(msg: str):
    SAYF(TerminalColors.cLBL + "[*] " + TerminalColors.cRST + msg + "\n")


def OKF(msg: str):
    SAYF(TerminalColors.cLGN + "[+] " + TerminalColors.cRST + msg + "\n")


def BADF(msg: str):
    SAYF(TerminalColors.cLRD + "[-] " + TerminalColors.cRST + msg + "\n")


def FATAL(msg: str):
    SAYF(TerminalColors.cLRD + "[-] PROGRAM ABORT : " + TerminalColors.cRST + msg + "\n")
    exit(1)


def PFATAL(msg: str):
    SAYF(TerminalColors.cLRD + "\n[-] SYSTEM ERROR : " + TerminalColors.cBRI + msg + TerminalColors.cRST + "\n")
    exit(1)


###############################
### Miscellaneous functions ###
###############################
def read_file(filepath: str) -> str:
    """Read the content of filepath

    Parameters
    ----------
    filepath : str
        The path to the file

    Returns
    -------
    str
        Content of the file
    """
    return Path(filepath).read_text(encoding="utf-8")


def get_cur_time() -> str:
    """获取当前时间

    Returns
    -------
    str
        返回当前时间, 格式为"年月日时分秒"

    Notes
    -----
    _description_
    """
    cur_time = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
    return cur_time


def get_first_code_block(md_text: str, langs: set) -> str:
    """从markdown文本中获取第一个指定语言(langs中存在的语言)的代码块内容

    Parameters
    ----------
    md_text : str
        markdown文本
    langs: set
        指定语言集合

    Returns
    -------
    str
        makrdonw中代码块的内容, 包含表示代码块开头和结尾的标志
    """
    # 初始化markdown解析器, 将markdown文本解析为AST
    md_instance = marko.Markdown(renderer=MarkdownRenderer)
    md_ast = md_instance.parse(md_text)
    code_list = list()

    # 遍历AST, 获取代码块内容, 存入代码列表中, 获取到第一个指定语言的代码块后就退出
    for child in md_ast.children:
        child_type = child.get_type()
        if child_type == "FencedCode" and child.lang in langs:  # type: ignore
            code_list.extend(md_instance.render(child).split("\n"))  # type: ignore
            break

    # 返回代码块内容, 包含开头的```xxx和结尾的```
    return "\n".join(code_list)


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


def clean_repo(path: str):
    """Clean the repository by checking out and removing untracked files.

    Parameters
    ----------
    path : str
        Path to the repository to clean.
    """
    res = subprocess.run(
        "git checkout . && git clean -fd",
        cwd=path,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        FATAL(f"Failed to clean repository: {res.stderr.decode('utf-8')}")


def patch_syzkaller(syzkaller: str, patch: str):
    """Patch syzkaller to support metamorphic testing.

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory, must be commit 4b25d554.
    patch : str
        Path to the patch file to apply to syzkaller.
    """
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
