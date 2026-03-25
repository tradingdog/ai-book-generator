"""
豆包API客户端模块

封装豆包API的调用，提供重试机制、错误处理和流式响应支持。
"""

import time
import json
from typing import Dict, List, Optional, Generator, Any
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from .config import get_config


class DoubaoClient:
    """豆包API客户端
    
    封装OpenAI兼容接口的豆包API调用，提供：
    - 自动重试机制
    - 请求间隔控制
    - 流式响应支持
    - 错误处理和日志记录
    
    Attributes:
        client: OpenAI客户端实例
        model: 使用的模型名称
        timeout: 请求超时时间
        max_retries: 最大重试次数
        request_interval: 请求间隔（秒）
    
    Example:
        >>> client = DoubaoClient()
        >>> response = client.chat("请总结这段文字")
        >>> for chunk in client.chat_stream("请生成内容"):
        ...     print(chunk, end='')
    """
    
    def __init__(self) -> None:
        """初始化豆包客户端
        
        从配置文件读取API配置并初始化OpenAI客户端。
        
        Raises:
            ValueError: API密钥未配置时
            ConnectionError: 初始化客户端失败时
        """
        config = get_config()
        
        self.api_key = config.get_doubao_api_key()
        self.base_url = config.get_doubao_base_url()
        self.model = config.get_doubao_model()
        self.timeout = config.get_doubao_timeout()
        self.max_retries = config.get_doubao_max_retries()
        self.request_interval = config.get_request_interval()
        
        self._last_request_time: Optional[float] = None
        
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
        except Exception as e:
            raise ConnectionError(f"初始化豆包客户端失败: {e}")
    
    def _wait_for_interval(self) -> None:
        """控制请求间隔
        
        确保两次请求之间至少有request_interval秒的间隔。
        """
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_interval:
                time.sleep(self.request_interval - elapsed)
        self._last_request_time = time.time()
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """发送单轮对话请求
        
        非流式方式获取完整响应，适合短文本生成。
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词，None表示不使用
            temperature: 采样温度，控制随机性（0-2）
            max_tokens: 最大生成token数，None表示不限制
            
        Returns:
            API响应的文本内容
            
        Raises:
            APIError: API调用失败且重试次数用尽时
            ConnectionError: 网络连接错误时
        """
        messages: List[Dict[str, str]] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries):
            try:
                self._wait_for_interval()
                
                params: Dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False
                }
                
                if max_tokens:
                    params["max_tokens"] = max_tokens
                
                response = self.client.chat.completions.create(**params)
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        return content.strip()
                
                raise APIError("API返回空响应", request=None, body=None)
                
            except RateLimitError as e:
                last_exception = e
                wait_time = 2 ** attempt  # 指数退避
                print(f"请求频率限制，等待{wait_time}秒后重试...")
                time.sleep(wait_time)
                
            except APITimeoutError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    print(f"请求超时，正在重试({attempt + 1}/{self.max_retries})...")
                    time.sleep(1)
                
            except APIError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    print(f"API错误: {e}，正在重试({attempt + 1}/{self.max_retries})...")
                    time.sleep(1)
                
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    print(f"请求失败: {e}，正在重试({attempt + 1}/{self.max_retries})...")
                    time.sleep(1)
        
        # 所有重试都失败
        raise APIError(
            f"API调用失败，已重试{self.max_retries}次: {last_exception}",
            request=None,
            body=None
        )
    
    def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """发送流式对话请求
        
        流式获取响应，适合长文本生成，可以实时显示进度。
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词，None表示不使用
            temperature: 采样温度（0-2）
            max_tokens: 最大生成token数
            
        Yields:
            响应文本的增量片段
            
        Raises:
            APIError: API调用失败时
        """
        messages: List[Dict[str, str]] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        for attempt in range(self.max_retries):
            try:
                self._wait_for_interval()
                
                params: Dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True
                }
                
                if max_tokens:
                    params["max_tokens"] = max_tokens
                
                stream = self.client.chat.completions.create(**params)
                
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            yield delta.content
                
                return  # 成功完成
                
            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"请求频率限制，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"流式请求失败: {e}，正在重试({attempt + 1}/{self.max_retries})...")
                    time.sleep(1)
                else:
                    raise APIError(
                        f"流式API调用失败: {e}",
                        request=None,
                        body=None
                    )
    
    def analyze_content(
        self,
        content: str,
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """分析文本内容
        
        使用AI分析文本，提取主题、关键词、结构等信息。
        
        Args:
            content: 要分析的文本内容
            analysis_type: 分析类型，可选summary(摘要)、structure(结构)、themes(主题)
            
        Returns:
            分析结果字典
        """
        system_prompt = """你是一位专业的文本分析专家。请对提供的文本进行深入分析，并以JSON格式返回分析结果。
确保返回的JSON格式正确，可以被直接解析。"""
        
        prompts = {
            "summary": f"""请对以下文本进行摘要分析，提取核心内容：

文本内容：
{content[:8000]}

请以JSON格式返回以下信息：
{{
    "main_theme": "主要主题",
    "key_points": ["要点1", "要点2", ...],
    "summary": "整体摘要（200字以内）"
}}""",
            "structure": f"""请分析以下文本的结构：

文本内容：
{content[:8000]}

请以JSON格式返回：
{{
    "sections": [
        {{"title": "章节标题", "content_type": "内容类型", "key_info": "关键信息"}}
    ],
    "narrative_style": "叙事风格",
    "time_line": "时间线描述"
}}""",
            "themes": f"""请提取以下文本的主题和关键词：

文本内容：
{content[:8000]}

请以JSON格式返回：
{{
    "main_themes": ["主题1", "主题2", ...],
    "keywords": ["关键词1", "关键词2", ...],
    "emotional_tone": "情感基调",
    "target_audience": "目标读者"
}}"""
        }
        
        prompt = prompts.get(analysis_type, prompts["summary"])
        
        try:
            response = self.chat(prompt, system_prompt, temperature=0.3)
            # 尝试解析JSON
            json_match = self._extract_json(response)
            if json_match:
                return json.loads(json_match)
            else:
                return {"raw_response": response, "error": "无法解析JSON"}
        except json.JSONDecodeError as e:
            return {"raw_response": response, "error": f"JSON解析错误: {e}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON字符串
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            提取的JSON字符串，如果找不到则返回None
        """
        # 尝试找到JSON对象
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        # 尝试找到JSON数组
        start = text.find('[')
        end = text.rfind(']')
        
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        return None


# 便捷函数
def get_doubao_client() -> DoubaoClient:
    """获取豆包客户端实例
    
    Returns:
        DoubaoClient实例
    """
    return DoubaoClient()


def quick_chat(prompt: str, system_prompt: Optional[str] = None) -> str:
    """快速发送对话请求
    
    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词
        
    Returns:
        API响应文本
    """
    client = get_doubao_client()
    return client.chat(prompt, system_prompt)
