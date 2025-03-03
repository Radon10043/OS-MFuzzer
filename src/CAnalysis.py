import argparse
import subprocess
import os

from clang.cindex import Config, Cursor, CursorKind, Token, TokenKind, Index


# ========== GLOBAL VARIABLES ==========
SYSCALL_LIST = list()  # 系统调用列表
# ======================================


def getCallExpr(cursor: Cursor):
    """获取当前节点下的所有函数调用

    Parameters
    ----------
    cursor : Cursor
        当前节点
    """
    global SYSCALL_LIST
    for child in cursor.get_children():
        if child.kind == CursorKind.CALL_EXPR and child.spelling != "":
            # 当遇到syscall时, 记录其名称和行号, 组成元组保存至SYSCALL_LIST
            syscall_name = child.spelling
            last_line = child.location.line
            for token in child.get_tokens():
                last_line = token.location.line
            SYSCALL_LIST.append((syscall_name, last_line))
        getCallExpr(child)


def getSyscallsFromMain(cursor: Cursor):
    """获取main函数中的每个系统调用, 对应了syzkaller生成的种子文件的每个系统调用

    Parameters
    ----------
    cursor : Cursor
        当前节点
    """
    # 遍历AST的节点
    for child in cursor.get_children():
        if child.location.is_in_system_header:
            continue
        # 若当前节点是函数声明节点且函数名为main, 访问该节点, 递归遍历其子节点
        if child.kind == CursorKind.FUNCTION_DECL and child.spelling == "main":
            getCallExpr(child)


def main(args: argparse.Namespace):
    """分析获取C文件main函数中所有系统调用的位置

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数
    """
    libclang_path = subprocess.run("llvm-config --libdir", shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
    libclang_path = os.path.join(libclang_path, "libclang.so.19.1")
    Config.set_library_file(libclang_path)
    index = Index.create()
    tu = index.parse(args.file)
    getSyscallsFromMain(tu.cursor)

    # 打印syscall的名称和最后行号
    for syscall in SYSCALL_LIST:
        print(f"{syscall[0]},{syscall[1]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True, help="Path of .c file")
    args = parser.parse_args()
    main(args)
