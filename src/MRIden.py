"""
Author       : Radon
Date         : 2025-02-12 20:23:29
LastEditors  : Radon
LastEditTime : 2025-07-28 17:13:56
Description  : 提示两个LLM进行MR识别和校对
"""

import argparse
import json
import os
import shutil

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from utils import *
from wrappers.anthropic import Anthropic
from wrappers.googleai import GoogleAI
from wrappers.openai import OpenAI


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


def loop(
    identifier: OpenAI | Anthropic | GoogleAI,
    calibrator: OpenAI | Anthropic | GoogleAI,
    config: dict,
    vector_db: Chroma | None,
):
    """Prompt identifier & calibrator to identify and calibrate metamorphic relations (MRs).

    Parameters
    ----------
    identifier : OpenAI | Anthropic | GoogleAI
        LLM used to identify metamorphic relations
    calibrator : OpenAI | Anthropic | GoogleAI
        LLM used to calibrate metamorphic relations
    config : dict
        Configuration provided by user
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
    gen_success = False  # 是否成功生成MR

    # 读取identifier和calibrator的提示词
    for fn in config["identifier"]["prompts"]["user"]:
        with open(fn, "r") as f:
            iden_prompts.append(f.read())
    for fn in config["calibrator"]["prompts"]["user"]:
        with open(fn, "r") as f:
            cali_prompts.append(f.read())

    # Prompt identifier and calibrator to identify and calibrate metamorphic relations iteratively
    while iterations < config["max_iter"]:
        ACTF(f"Iterations: {iterations + 1}")
        ACTF(f"Asking identifier ({config['identifier']['model']}) ...")
        iden_prompt = iden_prompts[idx_iden_prompt]
        iden_prompt = iden_prompt.replace("[Text from specification]", spec)
        iden_prompt = iden_prompt.replace("[MR generated by calibrator]", mr)
        iden_prompt = iden_prompt.replace("[Driver name]", dirver_name)

        # Retrieve relevant documents from the external corpus if exists
        if vector_db is not None:
            retrieved_docs = vector_db.similarity_search(query=spec)
            docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
            if len(docs_content) > 0:
                retrieved_prompt = f"You can also refer to the following documents:\n\n{docs_content}"
                iden_prompt = f"{iden_prompt}\n\n{retrieved_prompt}"

        # Prompt identifier to generate an metamorphic relation
        iden_response = identifier.chat(iden_prompt)

        # 如果输出的内容中不存在代码块, 认为identifier没有继续改进MR, 跳出循环
        prev_mr = mr
        mr = get_first_code_block(iden_response, {"markdown", "md"})
        if len(mr) == 0:
            break
        OKF(f"Got the MR generated by identifier!")

        ACTF(f"Asking calibrator ({config['calibrator']['model']}) ...")
        cali_prompt = cali_prompts[idx_cali_prompt]
        cali_prompt = cali_prompt.replace("[MR generated by identifier]", mr)
        cali_prompt = cali_prompt.replace("[Driver name]", dirver_name)
        cali_response = calibrator.chat(cali_prompt)

        # 如果calibrator的输出内容中不存在代码块, 或输出的是"correct", 视作calibrator认为此次的MR正确反应了待测对象的属性, 跳出循环
        prev_mr = mr
        mr = get_first_code_block(cali_response, {"markdown", "md"})
        if len(mr) == 0 or cali_response.lower() == "correct":
            gen_success = True
            break
        OKF("Got the MR generated by calibrator!")

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
    if gen_success:
        with open(os.path.join(config["output"], "mr_final.md"), "w") as f:
            f.write("### FINAL DISCUSSION RESULT\n\n")
            f.write(prev_mr + "\n\n")
            f.write(f"IDENTIFIER: {config['identifier']['model']}\n\n")
            f.write(f"CALIBRATOR: {config['calibrator']['model']}\n\n")
            f.write(f"ITERATIONS: {iterations + 1}\n\n")
        OKF(f"Discussion finished! Check the output directory {config['output']} for details.")
    else:
        WARNF(f"{identifier.model} (identifier) and {calibrator.model} (calibrator) did not reach the consistent!")


def main(config: dict):
    """Initialize the identifier and calibrator, then let the two models discuss to identify and calibrate metamorphic relations.

    Parameters
    ----------
    config : dict
        Configuration provided by user
    """
    # Dictionary to map framework names to setup functions
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }

    # Initialize identification llm
    ACTF(f"Initializing identifier model ({config['identifier']['model']}) ...")
    framework = config["identifier"]["framework"].lower()
    if framework not in setup_func_dict.keys():
        FATAL(f"Unsupported model: {framework}\n\nSupported models: {setup_func_dict.keys()}")
    identifier = setup_func_dict[framework](config, "identifier")
    OKF("Identifier model successfully initialized!")

    # Initialize calibration llm
    ACTF(f"Initializing calibrator model ({config['calibrator']['model']}) ...")
    framework = config["calibrator"]["framework"].lower()
    if framework not in setup_func_dict.keys():
        FATAL(f"Unsupported model: {framework}\n\nSupported models: {setup_func_dict.keys()}")
    calibrator = setup_func_dict[framework](config, "calibrator")
    OKF("Calibrator model successfully initialized!")

    # Load the external corpus if exists
    vector_db = None
    if "corpus" in config.keys():
        chroma_dir = os.path.join(config["corpus"]["path"], "chroma")
        embeddings = OpenAIEmbeddings(model=config["corpus"]["embeddings"])
        vector_db = Chroma(persist_directory=chroma_dir, embedding_function=embeddings)

    # Prompt iden llm & cali llm to identify and calibrate metamorphic relations
    ACTF("Let identifier and calibrator discuss ...")
    loop(identifier, calibrator, config, vector_db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration json file.")
    args = parser.parse_args()

    # 检查命令行参数是否合法
    ACTF("Checking arguments...")
    check_config(args)
    OKF("Arguments are valid.")

    # 读取配置文件
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    main(config)
