import time
from pathlib import Path

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
