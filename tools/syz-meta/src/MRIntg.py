"""
Author       : Radon
Date         : 2025-04-16 05:32:03
LastEditors  : Radon
LastEditTime : 2025-04-24 09:36:56
Description  : 将MR实现集成到syzkaller中
"""

import argparse
import os
import time
import uuid
import subprocess

from clang.cindex import Config, Index, CursorKind
from utils import *


def update_csource(path: str, uuid: str) -> str:
    """更新C代码实现

    Parameters
    ----------
    path : str
        C代码实现文件路径
    uuid : str
        uuid, 为函数添加后缀

    Returns
    -------
    str
        更新后的C代码实现
    """
    # 加载libclang.so
    if not Config.loaded:
        libclang_path = subprocess.run("llvm-config --libdir", shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
        Config.set_library_path(libclang_path)

    # 获得C代码实现的文本内容
    csource_lines = list()
    with open(path, mode="r", encoding="utf-8") as f:
        csource_lines = f.readlines()

    # 获得C代码实现的AST
    index = Index.create()
    tu = index.parse(path)
    cursor = tu.cursor

    # 构建函数名称字典, key为旧函数名, val是对应的新函数名
    func_dict = dict()
    for node in cursor.walk_preorder():
        if node.location.is_in_system_header:  # 跳过系统头文件
            continue
        if node.kind == CursorKind.FUNCTION_DECL:
            func = node.spelling
            n_func = func + "_" + uuid
            func_dict[func] = n_func

    # 遍历AST, 修改函数名, 包括函数声明和函数体
    for node in cursor.walk_preorder():
        update = False
        if node.location.is_in_system_header:  # 跳过系统头文件
            continue
        if node.kind in {CursorKind.FUNCTION_DECL, CursorKind.CALL_EXPR} and node.spelling in func_dict.keys():
            update = True
        if update:  # 小心! 这种修改方法可能会导致代码被破坏
            func = node.spelling
            row, col = node.location.line, node.location.column
            length = len(func)
            code = csource_lines[row - 1]
            to_replace = code[col - 1 : col + length - 1]
            if to_replace != func:
                FATAL("Damn, C source code might broken. I should not modify it anymore.")
            n_code = code[: col - 1] + func_dict[func] + code[col + length - 1 :]
            csource_lines[row - 1] = n_code

    # 返回修改后的函数
    return "\n".join(csource_lines)


def update_syzlang(path: str, uuid: str) -> str:
    """更新syzlang描述

    Parameters
    ----------
    path : str
        syzlang描述文件路径
    uuid : str
        uuid, 为函数添加后缀

    Returns
    -------
    str
        更新后的syzlang描述
    """
    desc = str()
    with open(path, mode="r", encoding="utf-8") as f:
        desc = f.read()
    desc = desc.replace("syz_mr", "syz_mr_" + uuid)
    return desc


def integrate(syzkaller: str, csource: str, syzlang: str, func: str):
    # 将C实现代码插入syzkaller/executor/common_linux.h的后面
    common_linux_h = os.path.join(syzkaller, "executor", "common_linux.h")
    with open(common_linux_h, mode="a", encoding="utf-8") as f:
        f.write("\n#if SYZ_EXECUTOR || __NR_" + func + "\n")
        f.write(csource)
        f.write("\n#endif\n")

    # 将syzlang描述插入syzkaller/sys/linux/metamorphic.txt中
    metamorphic_txt = os.path.join(syzkaller, "sys", "linux", "metamorphic.txt")
    with open(metamorphic_txt, mode="a", encoding="utf-8") as f:
        f.write("\n" + syzlang + "\n")

    # 将pseudo-syscall的函数名称加入syzkaller/pkg/vminfo/linux_syscalls.go中的linuxSyscallChecks中
    linux_syscalls_go = os.path.join(syzkaller, "pkg", "vminfo", "linux_syscalls.go")
    lines = list()
    with open(linux_syscalls_go, mode="r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines[104].startswith('\t"syz_create_resource"'):
        FATAL("Damn, the syscall list has been modified. I should not modify it anymore.")
    lines[104] += '"%s":alwaysSupported,\n' % func
    with open(linux_syscalls_go, mode="w", encoding="utf-8") as f:
        f.writelines(lines)


def main(args: argparse.Namespace):
    print(
        """
+-----------------------------------------------------+
|   Please make sure that:                            |
|   - commit of syzkaller commit is 4b25d554;         |
|   - pkg/vminfo/syscalls.go has not been modified;   |
|   - no pseudo-syscalls have been added.             |
|   Otherwise the integration may failed!             |
+-----------------------------------------------------+
        """
    )
    time.sleep(4)

    syzkaller_dir = args.syzkaller
    impls = args.impls
    for impl in impls:
        # 遍历存储MR实现的每个文件夹, 更新C代码实现和syzlang描述
        # 代码生成过程中可能会出现同名函数, 为防止冲突, 为每个MR实现生成uuid作为函数后缀
        uuid4 = uuid.uuid4().hex[:8]

        # 修改C代码实现
        csource_path = os.path.join(impl, "mrc.h")
        csource = update_csource(csource_path, uuid4)

        # 修改syzlang描述
        syzlang_path = os.path.join(impl, "syzlang.txt")
        syzlang_desc = update_syzlang(syzlang_path, uuid4)

        # 将修改好的实现插入syzkaller
        func = "syz_mr_" + uuid4
        integrate(syzkaller_dir, csource, syzlang_desc, func)
        OKF("%s is integrated into syzkaller!" % impl)

    WARNF("Integration is complete! Now you can run `make clean all -j` to build syzkaller.")
    SAYF("    Note that errors may occur during the building, please correct them manually.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integrate MR implementation into syzkaller")
    parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory")
    parser.add_argument("--impls", type=str, required=True, nargs="+", help="Path to the MR implementation directory")
    args = parser.parse_args()
    main(args)
