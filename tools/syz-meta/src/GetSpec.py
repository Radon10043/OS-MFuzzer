"""
Author       : Radon
Date         : 2025-04-09 02:53:19
LastEditors  : Radon
LastEditTime : 2025-04-09 06:41:38
Description  : Get the specification (HTML) and convert it to markdown
"""

import os
import argparse
import html2text
import urllib.request

import pandas as pd

from utils import *


def main(args: argparse.Namespace):
    """读取用户指定的excel, 获取所有驱动程序文档的链接, 获取HTML内容并转换为markdown

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数
    """
    dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_excel(args.excel, sheet_name=args.sheet, header=args.header, engine="calamine")

    # 遍历excel中的所有内容
    for _, row in df.iterrows():
        kernel = row["kernel"]  # 内核名称
        ver = row["kernel version"]  # 内核版本
        driver = row["driver"]  # 驱动程序名称
        link = row["link"]  # 驱动程序文档的链接

        # 如果driver名称为空或链接为空, 跳过
        if pd.isnull(driver) or pd.isnull(link):
            continue

        # 建立保存文件夹
        spec_dir = os.path.join(dir, "data", "spec", f"{kernel}-{ver}", driver)
        os.makedirs(spec_dir, exist_ok=True)

        # 获取文件名和对应的存储路径
        bn = os.path.basename(link)
        fn = str()
        if len(bn):
            fn = os.path.splitext(bn)[0] + ".md"
        else:
            fn = "index.md"
        md_path = os.path.join(spec_dir, fn)

        # 获取HTML内容并转换为markdown
        try:
            response = urllib.request.urlopen(link)
            html_content = response.read().decode("utf-8")
            md_content = html2text.html2text(html_content)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            OKF(f"Write {md_path} done")
        except BaseException as e:
            BADF(f"Write {md_path} failed, error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", type=str, required=True, help="The excel file path")
    parser.add_argument("--sheet", type=str, required=True, help="The sheet that include spec info")
    parser.add_argument("--header", type=str, default=1, help="The number of header row")
    args = parser.parse_args()
    main(args)
