import time


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
    SAYF(TerminalColors.cLRD + "[-] PROGRAM ABORT :  " + TerminalColors.cRST + msg + "\n")
    exit(1)


def PFATAL(msg: str):
    SAYF(TerminalColors.cLRD + "\n[-] SYSTEM ERROR : " + TerminalColors.cBRI + msg + TerminalColors.cRST + "\n")
    exit(1)


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
