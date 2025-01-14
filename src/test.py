import argparse
import os
import sys
import shutil

from openai import OpenAI
from utils import *

# fmt:off
# ========== GLOBAL VARIABLES ==========
BASE_URL = str()    # Base URL for the OpenAI API, e.g. https://api.deepseek.com
API_KEY  = str()    # API Key for the OpenAI API, like sk-xxxxxxx
# ======================================
# fmt:on


def check_args(args: argparse.Namespace):
    """检查命令行参数是否合法

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数集
    """
    global BASE_URL, API_KEY

    # 检查存储base_url和api_key的文件是否存在
    paths = [args.base_url, args.api_key]
    for path in paths:
        if not os.path.exists(path):
            FATAL(f"File not found: {path}")

    # 检查输出目录是否存在, 如果存在则报错, 提示用户需要先删掉该目录
    shutil.rmtree(args.output, ignore_errors=True)  # NOTE: Just for testing ...
    if os.path.exists(args.output):
        FATAL(f"Output directory already exists: {args.output}, please remove it first.")
    os.makedirs(args.output)

    # 读取base_url和api_key, 存储至全局变量
    with open(args.base_url, "r") as f:
        BASE_URL = f.read().strip()
    with open(args.api_key, "r") as f:
        API_KEY = f.read().strip()

    # 列出所有可用的模型, 检查输入的模型是否合法
    available_models = list_models()
    if args.model not in available_models:
        FATAL(f'Model "{args.model}" is not avaliable.\n{" " * 21}Available models: {available_models}')


def write_stats_file(args: argparse.Namespace):
    """将命令行参数信息写入文件

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数集
    """
    fp = os.path.join(args.output, "stats.txt")

    # fmt:off
    with open(fp, "w") as f:
        f.write(
            f"base_url     : {BASE_URL}\n"
            f"api_key      : {API_KEY}\n"
            f"model        : {args.model}\n"
            f"output       : {args.output}\n"
            f"command_line : {" ".join(sys.argv)}\n"
        )
    # fmt:on


def list_models() -> list:
    """列出所有可用的模型

    Returns
    -------
    list
        可用的模型列表
    """
    models = list()
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    for val in client.models.list():
        models.append(val.id)
    return models


def main(args: argparse.Namespace):
    ACTF(f"Checking arguments...")
    check_args(args)
    OKF(f"Arguments are valid.")

    # fmt:off
    OKF(
        "Here is the summary of the arguments:\n\n"
        f"     Base URL : {BASE_URL}\n"
        f"      API Key : {API_KEY}\n"
        f"        Model : {args.model}\n"
        f"   Output dir : {args.output}\n"
    )
    # fmt:on
    write_stats_file(args)

    ACTF("Ready to start ...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_url", type=str, required=True, help="The file path that stores the base url.")
    parser.add_argument("--api_key", type=str, required=True, help="The file path that stores the API key.")
    parser.add_argument("--model", type=str, required=True, help="The model to use.")
    parser.add_argument("--output", type=str, required=True, help="The output directory path.")
    args = parser.parse_args()
    main(args)
