"""
Author       : Radon
Date         : 2025-04-16 05:32:03
LastEditors  : Radon
LastEditTime : 2025-05-28 09:03:31
Description  : 将MR实现集成到syzkaller中
"""

import argparse
import os
import time
import uuid
import subprocess

from clang.cindex import Config, Index, TranslationUnit, CursorKind, TokenKind
from utils import *


########## GLOBAL VARIABLES ##########
# 黑名单, 记录了需要跳过的节点
BLACK_LIST = {
    CursorKind.STRUCT_DECL: {
        "kvm_ppc_mmuv3_cfg",
        "kvm_create_spapr_tce",
        "kvm_arm_copy_mte_tags",
        "kvm_rtas_token_args",
        "kvm_xen_vcpu_attr",
        "kvm_allocate_rma",
        "kvm_create_spapr_tce_64",
        "kvm_get_htab_fd",
        "kvm_ppc_cpu_char",
    },
    CursorKind.MACRO_DEFINITION: {
        "KVM_XEN_VCPU_GET_ATTR",
    },
    CursorKind.FUNCTION_DECL: {
        "failmsg",
    },
}
######################################


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
    tu = index.parse(path, options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    cursor = tu.cursor

    # 为防止多个源文件之间出现变量, 函数等名称的冲突, 需要为可能冲突的内容进行重命名
    # 构建名称替换映射, key为旧名字, val是对应的新名字, key包含:
    # - 函数名
    # - 全局变量名
    # - 结构体名
    # - 宏定义
    rename_dict = dict()
    concern_cursor_kinds = {CursorKind.FUNCTION_DECL, CursorKind.VAR_DECL, CursorKind.STRUCT_DECL, CursorKind.MACRO_DEFINITION}
    for node in cursor.get_children():
        if node.location.is_in_system_header:  # 跳过系统头文件
            continue
        if node.location.file == None or node.location.file.name != path:  # 跳过不属于当前文件的节点
            continue
        if node.kind in BLACK_LIST.keys() and node.spelling in BLACK_LIST[node.kind]:  # 跳过黑名单中的节点
            # TODO: 这个方法不够通用, 是否存在更好的方式?
            continue
        if node.kind in concern_cursor_kinds:
            name = node.spelling
            n_name = name + "_" + uuid
            rename_dict[name] = n_name

    # 遍历tokens, 进行重命名
    # 一开始是用cursor.walk_preorder()遍历的, 但if语句内的内容似乎无法被解析,
    # 暂时没有解决方案, 用cursor.get_tokens()代替. 直觉上比遍历AST精确度会差很多
    # TODO: 寻找其他更合适的方法重构代码
    mod_times = dict()  # <int, int>, key为行号, val是修改次数, 若一行存在多个需重命名的内容, 需要计算列号的偏移量
    for token in cursor.get_tokens():

        # 如果节点不是标识符或者节点的名称不在函数字典中, 跳过
        if not token.kind == TokenKind.IDENTIFIER or not token.spelling in rename_dict.keys():
            continue

        # 根据重命名字典修改代码中的变量名或函数名
        # 小心! 这种修改方法可能会导致代码被破坏
        name = token.spelling
        row, col = token.location.line, token.location.column

        # 若本行存在多个修改内容, 第一个以外的函数调用需要计算列号的偏移量
        offset = 0
        if row in mod_times.keys():
            offset = mod_times[row] * (len(uuid) + 1)  # 因为多了个下划线, 所以+1
        col += offset

        # 修改函数
        length = len(name)
        code = csource_lines[row - 1]
        to_replace = code[col - 1 : col + length - 1]
        if to_replace != name:
            FATAL("Damn, C source code might broken. I should not modify it anymore.")
        n_code = code[: col - 1] + rename_dict[name] + code[col + length - 1 :]
        csource_lines[row - 1] = n_code

        # 更新修改字典
        if row in mod_times.keys():
            mod_times[row] += 1
        else:
            mod_times[row] = 1

    # 添加源码的来源, 方便调试
    csource_lines.insert(0, f"// Code from {path}\n")

    # 返回修改后的函数
    return "".join(csource_lines)


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
    """将C代码实现和syzlang描述集成到syzkaller中

    Parameters
    ----------
    syzkaller : str
        syzkaller的路径
    csource : str
        C代码实现
    syzlang : str
        syzlang描述
    func : str
        函数名称
    """
    # 将C代码实现写入syzkaller/executor/MRs/[func].h中, 并基于syzkaller./clang-format进行格式化
    os.makedirs(os.path.join(syzkaller, "executor", "MRs"), exist_ok=True)
    fn = os.path.join(syzkaller, "executor", "MRs", func + ".h")
    with open(fn, mode="w", encoding="utf-8") as f:
        f.write(csource)
    res = subprocess.run(["clang-format", "-i", f"--style=file:{syzkaller}/.clang-format", fn])
    if res.returncode != 0:  # unlikely
        FATAL("clang-format failed! Please check the file %s." % fn)

    # 在syzkaller/executor/common_linux.h的结尾添加#if SYZ_EXECUTOR || __NR_[func]和#include "MRs/[func].h"
    common_linux_h = os.path.join(syzkaller, "executor", "common_linux.h")
    with open(common_linux_h, mode="a", encoding="utf-8") as f:
        f.write("\n#if SYZ_EXECUTOR || __NR_" + func + "\n")
        f.write('#include "MRs/%s.h"\n' % func)
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
        "+-----------------------------------------------------+"
        "|   Please make sure that:                            |"
        "|   - commit of syzkaller commit is 4b25d554;         |"
        "|   - pkg/vminfo/syscalls.go has not been modified;   |"
        "|   - no pseudo-syscalls have been added.             |"
        "|   Otherwise the integration may failed!             |"
        "+-----------------------------------------------------+"
    )
    time.sleep(4)

    syzkaller_dir = args.syzkaller
    impls = args.impls
    for impl in impls:
        # 遍历存储MR实现的每个文件夹, 更新C代码实现和syzlang描述
        # 代码生成过程中可能会出现同名函数, 为防止冲突, 为每个MR实现生成uuid作为函数后缀
        uuid4 = uuid.uuid4().hex[:8]

        # 修改C代码实现
        csource_path = os.path.join(impl, "mr.h")
        csource = update_csource(csource_path, uuid4)

        # 修改syzlang描述
        syzlang_path = os.path.join(impl, "syzlang.txt")
        syzlang_desc = update_syzlang(syzlang_path, uuid4)

        # 将修改好的实现插入syzkaller
        func = "syz_mr_" + uuid4
        integrate(syzkaller_dir, csource, syzlang_desc, func)
        OKF("%s is integrated into syzkaller!" % impl)

    WARNF("Integration is complete! Now you can run `make generate -j && make clean all -j` to build syzkaller.")
    SAYF("    Note that errors may occur during the building, please correct them manually.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integrate MR implementation into syzkaller")
    parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory")
    parser.add_argument("--impls", type=str, required=True, nargs="+", help="Path to the MR implementation directory")
    args = parser.parse_args()
    main(args)
