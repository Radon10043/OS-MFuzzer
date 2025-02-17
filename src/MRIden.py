"""
Author       : Radon
Date         : 2025-02-12 20:23:29
LastEditors  : Radon
LastEditTime : 2025-02-17 21:21:56
Description  : 提示两个LLM进行MR识别和校对
"""

import argparse
import os
import shutil
import json

from utils import *
from LLMs.DeepSeek import DeepSeek
from LLMs.GPT import GPT
from LLMs.Claude import Claude
from LLMs.Gemini import Gemini


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

    # 检查输出目录是否存在, 如果存在则报错, 提示用户需要先删掉该目录
    out_dir = config["output"]
    shutil.rmtree(out_dir, ignore_errors=True)  # NOTE: Just for testing ...
    if os.path.exists(out_dir):
        FATAL(f"Output directory already exists: {out_dir}, please remove it first.")
    os.makedirs(out_dir)

    # 将用户的输入配置文件复制到输出目录下
    shutil.copy(args.config, os.path.join(out_dir, "config.json"))


def setup_deepseek_model(config: dict, role: str) -> DeepSeek:
    """初始化DeepSeek聊天模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        DeepSeek模型的角色, 可以是identifier或calibrator

    Returns
    -------
    DeepSeek
        DeepSeek聊天模型
    """
    # 初始化DeepSeek聊天模型
    deepseek = DeepSeek(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
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
    deepseek.set_sys_prompt(sys_prompt)

    return deepseek


def setup_gpt_model(config: dict, role: str) -> GPT:
    """初始化GPT聊天模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        GPT模型的角色, 可以是identifier或calibrator

    Returns
    -------
    GPT
        GPT聊天模型
    """
    # 初始化GPT聊天模型
    gpt = GPT(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
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
    gpt.set_sys_prompt(sys_prompt)

    return gpt


def setup_claude_model(config: dict, role: str) -> Claude:
    """初始化Claude聊天模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        Claude模型的角色, 可以是identifier或calibrator

    Returns
    -------
    Claude
        Claude聊天模型
    """
    # 初始化Claude聊天模型
    claude = Claude(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
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
    claude.set_sys_prompt(sys_prompt)

    return claude


def setup_gemini_model(config: dict, role: str) -> Gemini:
    """初始化Gemini聊天模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    role : str
        Gemini模型的角色, 可以是identifier或calibrator

    Returns
    -------
    Gemini
        Gemini聊天模型
    """
    # 初始化Gemini聊天模型
    gemini = Gemini(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
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
    gemini.set_sys_prompt(sys_prompt)

    return gemini


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
    prev_mrc = str()  # 上一次的蜕变关系候选(Metamorphic Relation Candidate, MRC)内容
    mrc = str()  # 当前的蜕变关系候选内容
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
        iden_prompt = iden_prompt.replace("[MR generated by calibrator]", mrc)
        iden_prompt = iden_prompt.replace("[Driver name]", dirver_name)
        iden_response = identifier.chat(iden_prompt)

        # 如果输出的内容中不存在代码块, 认为identifier没有继续改进MRC, 跳出循环
        prev_mrc = mrc
        mrc = get_first_code_block(iden_response, {"markdown", "md"})
        if len(mrc) == 0:
            break
        ACTF(f"Got the MRC generatd by identifier!")

        cali_prompt = cali_prompts[idx_cali_prompt]
        cali_prompt = cali_prompt.replace("[MR generated by identifier]", mrc)
        cali_prompt = cali_prompt.replace("[Driver name]", dirver_name)
        cali_response = calibrator.chat(cali_prompt)

        # 如果calibrator的输出内容中不存在代码块, 或输出的是"correct", 视作calibrator认为MRC正确反应了待测对象的属性, 跳出循环
        prev_mrc = mrc
        mrc = get_first_code_block(cali_response, {"markdown", "md"})
        if len(mrc) == 0 or cali_response.lower() == "correct":
            break
        ACTF("Got the MRC generated by calibrator!")

        # 更新identifier和calibrator的提示词索引, 如果索引超出范围, 则不再更新
        if idx_iden_prompt < len(config["identifier"]["prompts"]["user"]) - 1:
            idx_iden_prompt += 1
        if idx_cali_prompt < len(config["calibrator"]["prompts"]["user"]) - 1:
            idx_cali_prompt += 1

        # 更新迭代轮数计数
        iterations += 1

    # 将和identifier及calibrator的对话记录保存至markdown和json文件, 并将两个LLM的最终讨论结果保存至output下的mrc_final.md
    identifier.save_messages(os.path.join(config["output"], "iden_messages.md"))
    identifier.save_messages(os.path.join(config["output"], "iden_messages.json"))
    calibrator.save_messages(os.path.join(config["output"], "cali_messages.md"))
    calibrator.save_messages(os.path.join(config["output"], "cali_messages.json"))
    with open(os.path.join(config["output"], "mrc_final.md"), "w") as f:
        f.write(f"### FINAL DISCUSSIN RESULT\n\n{prev_mrc}\n\nITERATIONS: {iterations + 1}")
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

    # 初始化模型字典, 用于根据配置文件中base_model的值初始化相应的模型
    setup_model_dict = {
        "deepseek": setup_deepseek_model,
        "gpt": setup_gpt_model,
        "claude": setup_claude_model,
        "gemini": setup_gemini_model,
    }

    # 初始化identifier模型, 该模型主要用于识别蜕变关系
    ACTF("Initializing identifier model ...")
    base_model = config["identifier"]["base_model"].lower()
    if base_model not in setup_model_dict.keys():
        FATAL(f"Unsupported model: {base_model}\n\nSupported models: {setup_model_dict.keys()}")
    identifier = setup_model_dict[base_model](config, "identifier")
    OKF("Identifier model successfully initialized!")

    # 初始化calibrator模型, 该模型主要用于校准蜕变关系
    ACTF("Initializing calibrator model ...")
    base_model = config["calibrator"]["base_model"].lower()
    if base_model not in setup_model_dict.keys():
        FATAL(f"Unsupported model: {base_model}\n\nSupported models: {setup_model_dict.keys()}")
    calibrator = setup_model_dict[base_model](config, "calibrator")
    OKF("Calibrator model successfully initialized!")

    # 开始通过两个模型之间的讨论来识别和校准蜕变关系
    ACTF("Let identifier and calibrator discuss ...")
    loop(identifier, calibrator, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration json file.")
    args = parser.parse_args()
    main(args)
