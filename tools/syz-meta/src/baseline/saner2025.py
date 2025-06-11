"""
Author       : Radon
Date         : 2025-06-11 06:52:52
LastEditors  : Radon
LastEditTime : 2025-06-11 09:21:38
Description  : 参考Zhang等人提出的LLM发现MR的方法识别内核中的MR (SANER 2025)
               论文名称: Can large language models discover metamorphic relations? A large-scale empirical study
"""

import argparse
import json
import sys
import os

from os.path import *

# 添加tools/syz-meta/src目录到sys.path中, 以便导入其他模块
pa = dirname(dirname(abspath(__file__)))
sys.path.append(pa)
import MRImpl

from wrappers.openai import OpenAI
from utils import *


def validate(mr_code: str, syzkaller: str) -> bool:
    """验证LLM生成的代码是否可作为pseudo-syscall集成至syzkaller

    Parameters
    ----------
    mr_code : str
        LLM生成的MR实现代码
    syzkaller : str
        syzkaller的路径

    Returns
    -------
    bool
        如果MR代码可以合并至syzkaller, 返回True; 否则返回False
    """
    func = "syz_mr"
    params = MRImpl.get_params(mr_code, func, input_file=False)
    syzlang = "syz_mr(" + ",".join([f"{param} int32" for param in params]) + ")"
    ret_code, _, _ = MRImpl.add_pseudo_syscall(syzkaller, mr_code, syzlang, func)
    return ret_code


def main(args: argparse.Namespace):
    """使用Zhang et al. (SANER 2025)提出的方法识别内核的蜕变关系。

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数
    """
    # 读取配置文件
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # 读取系统提示和用户提示
    sys_prompt = str()
    with open(config["prompts"]["system"], "r") as f:
        sys_prompt = f.read()
    usr_prompts = list()
    for fn in config["prompts"]["user"]:
        with open(fn, "r") as f:
            usr_prompts.append(f.read())

    # 根据配置文件初始化llm对象
    llm_obj = OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )
    llm_obj.set_sys_prompt(sys_prompt)

    # 与LLM交互, 让LLM识别内核的蜕变关系. 原论文多次与LLM进行交互生成多个MRs,
    # 考虑到成本问题, 这里只让LLM基于规格说明生成一个MR
    prompt = usr_prompts[0]
    spec = str()
    with open(config["specification"], "r") as f:
        spec = f.read()
    prompt = prompt.replace("[specification]", spec)
    response = llm_obj.chat(prompt)
    mr_code = get_first_code_block(response, {"c"})
    mr_code = mr_code.lstrip("`c\n").rstrip("`\n")
    if len(mr_code) == 0:
        FATAL("No code block found in the response. Please check the prompt and try again.")
    valid_res = validate(mr_code, config["syzkaller"])
    if valid_res:
        BADF("The generated code cannot be integrated into syzkaller.")
    else:
        OKF("The generated code can be integrated into syzkaller.")

    # 保存mr_code和LLM交互记录
    out_dir = config["output"]
    if not exists(out_dir):
        os.makedirs(out_dir)
    with open(join(out_dir, "mr.h"), "w") as f:
        f.write(mr_code)
    with open(join(out_dir, "valid_res"), "w") as f:
        f.write(str(valid_res == 0))
    llm_obj.save_messages(join(out_dir, "messages.json"))
    llm_obj.save_messages(join(out_dir, "messages.md"))
    OKF("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseline method for MR identification, refer to the paper published by Zhang et al. in SANER 2025.")
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file.")
    args = parser.parse_args()
    main(args)
