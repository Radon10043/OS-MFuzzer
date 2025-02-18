"""
Author       : Radon
Date         : 2025-02-12 21:30:59
LastEditors  : Radon
LastEditTime : 2025-02-18 11:00:39
Description  : 提示LLM用C语言实现指定的MR
"""

import argparse
import os
import json
import shutil
import subprocess

from typing import Tuple
from utils import *
from LLMs.DeepSeek import DeepSeek
from LLMs.GPT import GPT
from LLMs.Claude import Claude
from LLMs.Gemini import Gemini


def check_config(args: argparse.Namespace):
    """检查命令行参数是否合法, 并读取配置文件

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数集
    """
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        FATAL(f"File not found: {args.config}")

    # 读取配置文件
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # 检查存储MRC(MR候选)描述的文件是否存在
    if not os.path.exists(config["mrc_desc"]):
        FATAL(f"File not found: {config["mrc_desc"]}")

    # 检查指定的编译器是否存在
    compiler = config["compiler"]
    res = subprocess.run([compiler, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        FATAL(f"Compiler not found: {compiler}")

    # 检查cflags是否合法
    cflags = config["cflags"]
    ret_code, _ = build_c_program("int main() { return 0; }", compiler, cflags)
    if ret_code != 0:
        FATAL(f"Invalid cflags: {cflags}")

    # 检查输出目录是否存在, 如果存在则报错, 提示用户需要先删掉该目录
    out_dir = config["output"]
    shutil.rmtree(out_dir, ignore_errors=True)  # NOTE: Just for testing ...
    if os.path.exists(out_dir):
        FATAL(f"Output directory already exists: {out_dir}, please remove it first.")
    os.makedirs(config["output"])

    # 将用户的输入配置文件复制到输出目录下
    shutil.copy(args.config, os.path.join(out_dir, "config.json"))


def setup_deepseek_model(config: dict) -> DeepSeek:
    """初始化DeepSeek模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    DeepSeek
        DeepSeek模型
    """
    # 初始化DeepSeek模型
    deepseek = DeepSeek(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    deepseek.set_sys_prompt(sys_prompt)

    # 返回初始化后的DeepSeek模型
    return deepseek


def setup_gpt_model(config: dict) -> GPT:
    """初始化GPT模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    GPT
        GPT模型
    """
    # 初始化GPT聊天模型
    gpt = GPT(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    gpt.set_sys_prompt(sys_prompt)

    # 返回初始化后的GPT模型
    return gpt


def setup_claude_model(config: dict) -> Claude:
    """初始化Claude模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    Claude
        Claude模型
    """
    # 初始化Claude模型
    claude = Claude(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    claude.set_sys_prompt(sys_prompt)

    # 返回初始化后的Claude模型
    return claude


def setup_gemini_model(config: dict) -> Gemini:
    """初始化Gemini模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    Gemini
        Gemini模型
    """
    # 初始化Gemini模型
    gemini = Gemini(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    gemini.set_sys_prompt(sys_prompt)

    # 返回初始化后的Gemini模型
    return gemini


def build_c_program(c_code: str, compiler: str, cflags: str) -> Tuple[int, str]:
    """编译构建C代码

    Parameters
    ----------
    c_code : str
        C代码
    compiler : str
        编译器
    cflags : str
        编译选项

    Returns
    -------
    Tuple[int, str]
        返回值和错误信息
    """
    # 将C代码写入临时文件并进行编译, 返回编译结果和错误信息
    sfn = "/tmp/GQuuuuuuX.c"
    binary = "/tmp/GQuuuuuuX"
    with open(sfn, mode="w", encoding="utf-8") as f:
        f.write(c_code)
    res = subprocess.run([compiler, cflags, "-o", binary, sfn], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode, res.stderr.decode("utf-8")


def loop(programmer, config: dict):
    """迭代地让programmer生成用C语言实现的MRC

    Parameters
    ----------
    programmer : _type_
        programmer模型
    config : dict
        配置文件
    """
    gen_success = False  # 代码生成成功标志
    index = 0  # 提示词下标
    iterations = 0  # 迭代次数
    usr_prompts = list()  # 用户提示列表
    err_msgs = str()  # 编译器报告的错误信息
    c_code = str()  # 生成的C代码

    # 读取包含MRC自然语言描述的markdown文件
    md_text = str()
    with open(config["mrc_desc"], "r", encoding="utf-8") as f:
        md_text = f.read()

    # 读取所有用户提示, 存入usr_prompts中
    for fn in config["prompts"]["user"]:
        with open(fn, "r", encoding="utf-8") as f:
            usr_prompts.append(f.read())

    # 从markdown文本中提取MRC的描述, MRC的描述需要放入markdown或md代码块中才能成功提取, 对应了前一步MR识别与校对的最终输出
    mrc_desc = get_first_code_block(md_text, {"markdown", "md"})

    # 如果没有找到MRC描述, 报错退出
    if len(mrc_desc) == 0:
        FATAL(f"No MRC description found in the {config["mrc_desc"]}!")

    # 进行多轮对话, 持续迭代, 直到MRC对应的代码成功生成并编译不报错, 或者达到最大迭代次数
    while not gen_success and iterations < config["max_iter"]:
        prompt = usr_prompts[index]
        prompt = prompt.replace("[MR rendered in markdown]", mrc_desc)
        prompt = prompt.replace("[Errors reported by compiler]", err_msgs)

        # 与programmer模型进行对话, 生成MRC的C代码
        ACTF(f"Iter {iterations + 1}: Prompting {config["model"]} to generate C code implementation of MRC ...")
        response = programmer.chat(prompt)
        c_code = get_first_code_block(response, {"c"})

        # 如果生成的C代码为空, 认为生成失败
        if len(c_code) == 0:
            FATAL(f"{config["model"]} generated empty C code implementation of MRC.")

        # 编译构建C代码, 同时获取错误信息
        ret_code, err_msgs = build_c_program(c_code, config["compiler"], config["cflags"])
        if ret_code == 0:  # 如果编译成功, 跳出循环
            break

        # 更新迭代次数和提示词下标
        iterations += 1
        if index < len(usr_prompts) - 1:
            index += 1

    # 如果代码未生成成功, 报错
    if not gen_success:
        FATAL(f"Failed to generate C code implementation of MRC after {iterations} iterations.")

    # 保存交互记录, 将生成的C代码写入文件
    programmer.save_messages(os.path.join(config["output"], "messages.json"))
    programmer.save_messages(os.path.join(config["output"], "messages.md"))
    with open(os.path.join(config["output"], "mrc.c"), "w", encoding="utf-8") as f:
        f.write(c_code)
    OKF(f"Successfully generated C code implementation of MRC after {iterations + 1} iterations.")


def main(args: argparse.Namespace):
    """主函数, 初始化programmer, 迭代地让模型生成用C语言实现的蜕变关系

    Parameters
    ----------
    args : argparse.Namespace
        命令函参数集
    """
    ACTF("Checking arguments ...")
    check_config(args)
    ACTF("Arguments are valid.")

    # 读取配置文件, 创建输出文件夹
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # 模型字典, 用于根据配置文件中的base_model字段选择对应的模型初始化函数
    # fmt:off
    setup_model_dict = {
        "deepseek": setup_deepseek_model,
        "gpt": setup_gpt_model,
        "claude": setup_claude_model,
        "gemini": setup_gemini_model
    }
    # fmt:on

    # 初始化programmer模型, 该模型用于将MRC的自然语言描述转换为C语言实现
    ACTF("Initializing programmer model ...")
    base_model = config["base_model"].lower()
    if base_model not in setup_model_dict:
        FATAL(f"Unsupported model: {base_model}, Supported models: {setup_model_dict.keys()}")
    programmer = setup_model_dict[base_model](config)
    OKF("Programmer model successfully initislized!.")

    # 让programmer模型迭代地生成用C语言实现的MRC
    ACTF("Generating C code implementation of MRC ...")
    loop(programmer, config)


# TODO: Need to test to ensure the correctness
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration file")
    args = parser.parse_args()
    main(args)
