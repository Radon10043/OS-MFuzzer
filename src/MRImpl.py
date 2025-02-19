"""
Author       : Radon
Date         : 2025-02-12 21:30:59
LastEditors  : Radon
LastEditTime : 2025-02-19 12:05:03
Description  : 提示LLM用C语言实现指定的MR
"""

import argparse
import os
import json
import shutil
import subprocess

from typing import Tuple
from utils import *
from wrappers.openai import OpenAI
from wrappers.anthropic import Anthropic
from wrappers.googleai import GoogleAI


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


def setup_openai(config: dict) -> OpenAI:
    """初始化以OpenAI为框架的聊天对象, 主要是GPT, DeepSeek等模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    OpenAI
        封装的以OpenAI为框架的聊天对象
    """
    # 初始化OpenAI聊天对象
    openai_obj = OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    openai_obj.set_sys_prompt(sys_prompt)

    # 返回初始化后的GPT模型
    return openai_obj


def setup_anthropic(config: dict) -> Anthropic:
    """初始化以Anthropic为框架的聊天对象, 主要是Claude等系列模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    Anthropic
        封装的以Anthropic为框架的聊天对象
    """
    # 初始化Anthropic聊天对象
    anthropic_obj = Anthropic(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    anthropic_obj.set_sys_prompt(sys_prompt)

    # 返回初始化后的Claude模型
    return anthropic_obj


def setup_googleai(config: dict) -> GoogleAI:
    """初始化以GooelAI为框架的聊天对象, 主要是Gemini等模型
    官方库的名称是google.genai

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    GoogleAI
        Gemini模型
    """
    # 初始化Gemini模型
    googleai_obj = GoogleAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )

    # 设置模型的系统提示信息
    fn = config["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    googleai_obj.set_sys_prompt(sys_prompt)

    # 返回初始化后的Gemini模型
    return googleai_obj


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
    mrc_code = str()  # 实现MRC的C代码

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
        mrc_code = get_first_code_block(response, {"c"})
        mrc_code = mrc_code.lstrip("```c\n").rstrip("```\n")

        # 如果生成的C代码为空, 认为生成失败
        if len(mrc_code) == 0:
            FATAL(f"{config["model"]} generated empty C code implementation of MRC.")

        # 加一段main函数调用MR(void)的代码, 与MRC代码结合形成完整C代码
        # 编译构建C代码, 同时获取错误信息
        c_code = f"{mrc_code}\n\nint main() {{ MR(); return 0; }}"
        ret_code, err_msgs = build_c_program(c_code, config["compiler"], config["cflags"])
        if ret_code == 0:  # 如果编译成功, 跳出循环
            gen_success = True
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
    with open(os.path.join(config["output"], "mrc.h"), "w", encoding="utf-8") as f:
        f.write(mrc_code)
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
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }
    # fmt:on

    # 初始化programmer模型, 该模型用于将MRC的自然语言描述转换为C语言实现
    ACTF("Initializing programmer model ...")
    framework = config["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported model: {framework}, Supported models: {setup_func_dict.keys()}")
    programmer = setup_func_dict[framework](config)
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
