from utils import *

class BaseLLM:
    """Base LLM Class"""

    def __init__(self):
        """构造函数"""
        FATAL("This is a base class, please use the derived class instead.")


    def append_sys_prompt(self):
        """设置系统提示信息"""
        FATAL("This is a base class, please use the derived class instead.")

    def chat(self) -> str:
        """对话"""
        FATAL("This is a base class, please use the derived class instead.")

    def avaliable_models(self) -> list:
        """列出所有可用的模型"""
        FATAL("This is a base class, please use the derived class instead.")

    def save_messages(self):
        """保存对话信息, 支持保存为json文件或md文件"""
        FATAL("This is a base class, please use the derived class instead.")
