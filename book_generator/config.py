"""
配置管理模块

负责读取和管理项目配置，包括API配置、生成配置等。
"""

import os
import yaml
from typing import Dict, Any, Optional


class Config:
    """配置管理类
    
    统一管理项目所有配置项，支持从YAML文件加载和默认值设置。
    
    Attributes:
        config_data: 配置数据的字典存储
        config_path: 配置文件路径
    
    Example:
        >>> config = Config()
        >>> api_key = config.get_doubao_api_key()
        >>> timeout = config.get('doubao', 'timeout')
    """
    
    _instance: Optional['Config'] = None
    
    def __new__(cls, config_path: str = "config.yaml") -> 'Config':
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = "config.yaml") -> None:
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为"config.yaml"
        """
        if self._initialized:
            return
            
        self.config_path = config_path
        self.config_data: Dict[str, Any] = {}
        self._load_config()
        self._initialized = True
    
    def _load_config(self) -> None:
        """从YAML文件加载配置
        
        如果配置文件不存在，则使用默认配置。
        """
        default_config = self._get_default_config()
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        # 合并文件配置和默认配置
                        self.config_data = self._merge_config(default_config, file_config)
                    else:
                        self.config_data = default_config
            except yaml.YAMLError as e:
                print(f"警告: 配置文件解析失败，使用默认配置。错误: {e}")
                self.config_data = default_config
            except Exception as e:
                print(f"警告: 读取配置文件失败，使用默认配置。错误: {e}")
                self.config_data = default_config
        else:
            print(f"提示: 配置文件 {self.config_path} 不存在，使用默认配置")
            self.config_data = default_config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置
        
        Returns:
            包含所有默认配置项的字典
        """
        return {
            'doubao': {
                'api_key': '',
                'model': 'doubao-seed-1-8-251228',
                'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
                'timeout': 120,
                'max_retries': 3
            },
            'generation': {
                'style': 'plain',
                'chapter_target_words': 35000,
                'total_chapters': 15,
                'generate_preface': True,
                'output_filename': 'generated_book.docx'
            },
            'processing': {
                'chunk_size': 4000,
                'chunk_overlap': 500,
                'request_interval': 1,
                'save_intermediate': True,
                'temp_dir': './temp'
            },
            'document': {
                'body_font': '宋体',
                'body_size': 12,
                'title_font': '黑体',
                'line_spacing': 1.5
            }
        }
    
    def _merge_config(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并配置字典
        
        Args:
            default: 默认配置字典
            override: 覆盖配置字典
            
        Returns:
            合并后的配置字典
        """
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """获取配置项
        
        支持多级键访问，如 config.get('doubao', 'api_key')
        
        Args:
            *keys: 配置键路径
            default: 键不存在时的默认值
            
        Returns:
            配置值或默认值
        """
        value = self.config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def get_doubao_api_key(self) -> str:
        """获取豆包API密钥
        
        Returns:
            API密钥字符串
            
        Raises:
            ValueError: 当API密钥未配置时
        """
        api_key = self.get('doubao', 'api_key', default='')
        if not api_key:
            raise ValueError("豆包API密钥未配置，请在config.yaml中设置doubao.api_key")
        return api_key
    
    def get_doubao_model(self) -> str:
        """获取豆包模型名称
        
        Returns:
            模型名称字符串
        """
        return self.get('doubao', 'model', default='doubao-seed-1-8-251228')
    
    def get_doubao_base_url(self) -> str:
        """获取豆包API基础URL
        
        Returns:
            API基础URL字符串
        """
        return self.get('doubao', 'base_url', default='https://ark.cn-beijing.volces.com/api/v3')
    
    def get_doubao_timeout(self) -> int:
        """获取API请求超时时间
        
        Returns:
            超时时间（秒）
        """
        return self.get('doubao', 'timeout', default=120)
    
    def get_doubao_max_retries(self) -> int:
        """获取API最大重试次数
        
        Returns:
            最大重试次数
        """
        return self.get('doubao', 'max_retries', default=3)
    
    def get_style(self) -> str:
        """获取文风风格
        
        Returns:
            风格名称：plain(平实朴素)、literary(文学性)、academic(学术性)
        """
        return self.get('generation', 'style', default='plain')
    
    def get_chapter_target_words(self) -> int:
        """获取每章目标字数
        
        Returns:
            目标字数
        """
        return self.get('generation', 'chapter_target_words', default=35000)
    
    def get_total_chapters(self) -> int:
        """获取总章节数
        
        Returns:
            章节数量
        """
        return self.get('generation', 'total_chapters', default=15)
    
    def should_generate_preface(self) -> bool:
        """是否生成自序
        
        Returns:
            是否生成自序的布尔值
        """
        return self.get('generation', 'generate_preface', default=True)
    
    def get_output_filename(self) -> str:
        """获取输出文件名
        
        Returns:
            输出文件路径
        """
        return self.get('generation', 'output_filename', default='generated_book.docx')
    
    def get_chunk_size(self) -> int:
        """获取文本分块大小
        
        Returns:
            分块字符数
        """
        return self.get('processing', 'chunk_size', default=4000)
    
    def get_chunk_overlap(self) -> int:
        """获取分块重叠大小
        
        Returns:
            重叠字符数
        """
        return self.get('processing', 'chunk_overlap', default=500)
    
    def get_request_interval(self) -> float:
        """获取API请求间隔
        
        Returns:
            间隔时间（秒）
        """
        return self.get('processing', 'request_interval', default=1.0)
    
    def should_save_intermediate(self) -> bool:
        """是否保存中间结果
        
        Returns:
            是否保存的布尔值
        """
        return self.get('processing', 'save_intermediate', default=True)
    
    def get_temp_dir(self) -> str:
        """获取临时文件目录
        
        Returns:
            临时目录路径
        """
        return self.get('processing', 'temp_dir', default='./temp')
    
    def get_document_config(self) -> Dict[str, Any]:
        """获取文档格式配置
        
        Returns:
            文档格式配置字典
        """
        return self.get('document', default={
            'body_font': '宋体',
            'body_size': 12,
            'title_font': '黑体',
            'line_spacing': 1.5
        })


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """获取全局配置实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Config实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reload_config(config_path: str = "config.yaml") -> Config:
    """重新加载配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        重新加载后的Config实例
    """
    global _config_instance
    _config_instance = Config(config_path)
    # 强制重新加载
    _config_instance._initialized = False
    _config_instance.__init__(config_path)
    return _config_instance
