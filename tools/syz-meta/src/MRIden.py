"""
Author       : Radon
Date         : 2025-02-12 20:23:29
LastEditors  : Radon
LastEditTime : 2025-04-24 10:21:54
Description  : 提示两个LLM进行MR识别和校对
"""

import argparse
import os
import shutil
import json

from utils import *
from wrappers.openai import OpenAI
from wrappers.anthropic import Anthropic
from wrappers.googleai import GoogleAI


def check_config(args: argparse.Namespace):
    """检查配置文件是否合法

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

    # 如果config中没有temperature字段, 使用默认值0.5
    if "temperature" not in config["identifier"].keys():
        WARNF('Key "temperature" not found in config file for "identifier", using default value: 0.5')
        config["identifier"]["temperature"] = 0.5
    if "temperature" not in config["calibrator"].keys():
        WARNF('Key "temperature" not found in config file for "calibrator", using default value: 0.5')
        config["calibrator"]["temperature"] = 0.5

    # 如果config中没有stream字段, 使用默认值False
    if "stream" not in config["identifier"].keys():
        WARNF('Key "stream" not found in config file for "identifier", using default value: False')
        config["identifier"]["stream"] = False
    if "stream" not in config["calibrator"].keys():
        WARNF('Key "stream" not found in config file for "calibrator", using default value: False')
        config["calibrator"]["stream"] = False

    # 检查输出目录是否存在, 如果存在则报错, 提示用户需要先删掉该目录
    out_dir = config["output"]
    shutil.rmtree(out_dir, ignore_errors=True)  # NOTE: Just for testing ...
    if os.path.exists(out_dir):
        FATAL(f"Output directory already exists: {out_dir}, please remove it first.")
    os.makedirs(out_dir)

    # 将用户的输入配置文件复制到输出目录下
    shutil.copy(args.config, os.path.join(out_dir, "config.json"))


def setup_openai(config: dict, role: str) -> OpenAI:
    """初始化以OpenAI为框架的聊天对象, 主要是GPT, DeepSeek等系列模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        GPT模型的角色, 可以是identifier或calibrator

    Returns
    -------
    OpenAI
        封装的OpenAI聊天对象
    """
    # 初始化以OpenAI为框架的聊天对象
    openai_obj = OpenAI(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
        stream=config[role]["stream"],
    )

    driver_name = config["driver_name"]  # 待测驱动程序名称
    spec = read_file(config["specification"])  # 规约说明文件的内容

    # 设置模型的系统提示信息
    fn = config[role]["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    sys_prompt = sys_prompt.replace("[Driver name]", driver_name)
    sys_prompt = sys_prompt.replace("[Text from specification]", spec)
    openai_obj.set_sys_prompt(sys_prompt)

    return openai_obj


def setup_anthropic(config: dict, role: str) -> Anthropic:
    """初始化以Anthropic为框架的聊天对象, 主要是Claude系列模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        以Anthropic为框架的角色, 可以是identifier或calibrator

    Returns
    -------
    Anthropic
        封装的Anthropic聊天对象
    """
    # 初始化以Anthropic为框架的聊天对象
    anthropic_obj = Anthropic(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
        stream=config[role]["stream"],
    )

    driver_name = config["driver_name"]  # 待测驱动程序名称
    spec = read_file(config["specification"])  # 规约说明文件的内容

    # 设置模型的系统提示信息
    fn = config[role]["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    sys_prompt = sys_prompt.replace("[Driver name]", driver_name)
    sys_prompt = sys_prompt.replace("[Text from specification]", spec)
    anthropic_obj.set_sys_prompt(sys_prompt)

    return anthropic_obj


def setup_googleai(config: dict, role: str) -> GoogleAI:
    """初始化以GoogleAI为框架的聊天对象, 主要是调用Gemini等模型
    官方库名为google.genai

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        对象的角色, 可以是identifier或calibrator

    Returns
    -------
    GoogleAI
        封装的以GoogleAI为框架的聊天对象
    """
    # 初始化Gemini聊天模型
    googleai_obj = GoogleAI(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
        stream=config[role]["stream"],
    )

    driver_name = config["driver_name"]  # 待测驱动程序名称
    spec = read_file(config["specification"])  # 规约说明文件的内容

    # 设置模型的系统提示信息
    fn = config[role]["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    sys_prompt = sys_prompt.replace("[Driver name]", driver_name)
    sys_prompt = sys_prompt.replace("[Text from specification]", spec)
    googleai_obj.set_sys_prompt(sys_prompt)

    return googleai_obj


def loop(identifier, calibrator, config: dict):
    """迭代地让两个LLM进行讨论, 识别和校准蜕变关系

    Parameters
    ----------
    identifier : _type_
        用于识别蜕变关系的LLM
    calibrator : _type_
        用于校准蜕变关系的LLM
    config : dict
        存储配置信息的字典
    """
    iden_prompts = list()  # identifier提示词列表
    cali_prompts = list()  # calibrator提示词列表
    idx_iden_prompt = 0  # identifier提示词索引
    idx_cali_prompt = 0  # calibrator提示词索引
    spec = read_file(config["specification"])  # 读取规格说明文件的内容
    dirver_name = config["driver_name"]  # 驱动程序的名称
    prev_mr = str()  # 上一次的蜕变关系内容
    mr = str()  # 当前的蜕变关系候选内容
    iterations = 0  # 讨论轮数

    # 读取identifier和calibrator的提示词
    for fn in config["identifier"]["prompts"]["user"]:
        with open(fn, "r") as f:
            iden_prompts.append(f.read())
    for fn in config["calibrator"]["prompts"]["user"]:
        with open(fn, "r") as f:
            cali_prompts.append(f.read())

    # 迭代地让两个LLM进行讨论, 识别和校准蜕变关系
    while iterations < config["max_iter"]:
        ACTF(f"Iterations: {iterations + 1}")
        iden_prompt = iden_prompts[idx_iden_prompt]
        iden_prompt = iden_prompt.replace("[Text from specification]", spec)
        iden_prompt = iden_prompt.replace("[MR generated by calibrator]", mr)
        iden_prompt = iden_prompt.replace("[Driver name]", dirver_name)
        iden_response = identifier.chat(iden_prompt)

        # 如果输出的内容中不存在代码块, 认为identifier没有继续改进MR, 跳出循环
        prev_mr = mr
        mr = get_first_code_block(iden_response, {"markdown", "md"})
        if len(mr) == 0:
            break
        ACTF(f"Got the MR generatd by identifier!")

        cali_prompt = cali_prompts[idx_cali_prompt]
        cali_prompt = cali_prompt.replace("[MR generated by identifier]", mr)
        cali_prompt = cali_prompt.replace("[Driver name]", dirver_name)
        cali_response = calibrator.chat(cali_prompt)

        # 如果calibrator的输出内容中不存在代码块, 或输出的是"correct", 视作calibrator认为此次的MR正确反应了待测对象的属性, 跳出循环
        prev_mr = mr
        mr = get_first_code_block(cali_response, {"markdown", "md"})
        if len(mr) == 0 or cali_response.lower() == "correct":
            break
        ACTF("Got the MR generated by calibrator!")

        # 更新identifier和calibrator的提示词索引, 如果索引超出范围, 则不再更新
        if idx_iden_prompt < len(config["identifier"]["prompts"]["user"]) - 1:
            idx_iden_prompt += 1
        if idx_cali_prompt < len(config["calibrator"]["prompts"]["user"]) - 1:
            idx_cali_prompt += 1

        # 更新迭代轮数计数
        iterations += 1

    # 将和identifier及calibrator的对话记录保存至markdown和json文件, 并将两个LLM的最终讨论结果保存至output下的mr_final.md
    identifier.save_messages(os.path.join(config["output"], "iden_messages.md"))
    identifier.save_messages(os.path.join(config["output"], "iden_messages.json"))
    calibrator.save_messages(os.path.join(config["output"], "cali_messages.md"))
    calibrator.save_messages(os.path.join(config["output"], "cali_messages.json"))
    with open(os.path.join(config["output"], "mr_final.md"), "w") as f:
        f.write("### FINAL DISCUSSION RESULT\n\n")
        f.write(prev_mr + "\n\n")
        f.write(f"IDENTIFIER: {config["identifier"]["model"]}\n\n")
        f.write(f"CALIBRATOR: {config["calibrator"]["model"]}\n\n")
        f.write(f"ITERATIONS: {iterations + 1}\n\n")
    OKF(f"Discussion finished! Check the output directory {config["output"]} for details.")


def main(args: argparse.Namespace):
    """主函数, 初始化identifier和calibrator, 然后让两个模型进行讨论, 识别和校准蜕变关系

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数集
    """
    # 检查命令行参数是否合法
    ACTF("Checking arguments...")
    check_config(args)
    OKF("Arguments are valid.")

    # 读取配置文件
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # 打印规格说明路径, 方便批量识别时调试用
    text = f"*   Specification: {config["specification"]}   *"
    width = len(text)
    SAYF("*" * width + "\n" + "*  " + " " * (width - 6) + "  *\n" + text + "\n" + "*  " + " " * (width - 6) + "  *\n" + "*" * width + "\n")

    # 初始化模型字典, 用于根据配置文件中framework的值初始化相应的模型
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }

    # 初始化identifier模型, 该模型主要用于识别蜕变关系
    ACTF(f"Initializing identifier model ({config["identifier"]["model"]}) ...")
    framework = config["identifier"]["framework"].lower()
    if framework not in setup_func_dict.keys():
        FATAL(f"Unsupported model: {framework}\n\nSupported models: {setup_func_dict.keys()}")
    identifier = setup_func_dict[framework](config, "identifier")
    OKF("Identifier model successfully initialized!")

    # 初始化calibrator模型, 该模型主要用于校准蜕变关系
    ACTF(f"Initializing calibrator model ({config["calibrator"]["model"]}) ...")
    framework = config["calibrator"]["framework"].lower()
    if framework not in setup_func_dict.keys():
        FATAL(f"Unsupported model: {framework}\n\nSupported models: {setup_func_dict.keys()}")
    calibrator = setup_func_dict[framework](config, "calibrator")
    OKF("Calibrator model successfully initialized!")

    # 开始通过两个模型之间的讨论来识别和校准蜕变关系
    ACTF("Let identifier and calibrator discuss ...")
    loop(identifier, calibrator, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration json file.")
    args = parser.parse_args()
    main(args)
