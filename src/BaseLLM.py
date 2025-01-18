from utils import *


class BaseLLM:
    """Base LLM Class"""

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.5):
        """构造函数, 初始化LLM对象

        Parameters
        ----------
        base_url : str
            API的基础URL
        api_key : str
            API Key
        model : str
            要调用的模型
        temperature : float, optional
            温度参数, by default 0.5
        """
        FATAL("BaseLLM is an abstract class, please use other class instead.")

    def append_sys_prompt(self, sys_prompt: str):
        """设置系统提示信息, 感觉大部分情况下系统提示一条就够了...?

        Parameters
        ----------
        sys_prompt : str
            系统提示信息
        """
        FATAL("BaseLLM is an abstract class, please use other class instead.")

    def chat(self, user_prompt: str) -> str:
        """对话

        Parameters
        ----------
        user_prompt : str
            用户提示信息

        Returns
        -------
        str
            LLM回复的信息
        """
        FATAL("BaseLLM is an abstract class, please use other class instead.")

    def avaliable_models(self) -> list:
        """列出所有可用的模型

        Returns
        -------
        list
            可用的模型列表
        """
        FATAL("BaseLLM is an abstract class, please use other class instead.")

    def save_messages(self, path: str):
        """保存对话信息, 支持保存为json文件或md文件

        Parameters
        ----------
        path : str
            消息记录保存路径
        """
        FATAL("BaseLLM is an abstract class, please use other class instead.")
