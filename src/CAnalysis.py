import argparse
import subprocess
import os

from clang.cindex import Config, Cursor, CursorKind, Token, TokenKind, Index


def visit(cursor: Cursor):
    """访问C语言代码中的每一个节点

    Parameters
    ----------
    cursor : Cursor
        当前节点
    """
    if cursor.location.is_in_system_header:
        return
    if cursor.kind == CursorKind.CALL_EXPR and len(cursor.spelling):
        last_line = cursor.location.line
        for token in cursor.get_tokens():
            last_line = token.location.line
        print("[CALL_EXPR]:", cursor.spelling, "[LAST_LINE]:", last_line)
    for child in cursor.get_children():
        visit(child)


def main(args: argparse.Namespace):
    """分析获取C文件中所有函数的调用位置

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
    visit(tu.cursor)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True, help="Path of .c file")
    args = parser.parse_args()
    main(args)
