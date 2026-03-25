"""
日志系统模块

提供详细的日志记录功能，包括终端输出和文件保存。
"""

import os
import sys
import time
from datetime import datetime
from typing import Optional
from pathlib import Path


class BookGeneratorLogger:
    """书籍生成器日志系统
    
    提供多级别日志记录，同时输出到终端和文件。
    
    Attributes:
        log_dir: 日志文件目录
        log_file: 当前日志文件路径
        verbose: 是否显示详细输出
    """
    
    # 日志级别
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    
    def __init__(self, log_dir: str = "./logs", verbose: bool = True) -> None:
        """初始化日志系统
        
        Args:
            log_dir: 日志文件保存目录
            verbose: 是否显示详细输出
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self.level = self.INFO
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"book_generator_{timestamp}.log"
        
        # 写入日志头
        self._write_to_file(f"{'='*60}\n")
        self._write_to_file(f"AI书籍生成器日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._write_to_file(f"{'='*60}\n\n")
    
    def _write_to_file(self, message: str) -> None:
        """写入日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message)
                f.flush()
        except Exception as e:
            print(f"[日志写入失败] {e}")
    
    def _format_message(self, level: str, message: str) -> str:
        """格式化日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{level}] {message}\n"
    
    def debug(self, message: str) -> None:
        """调试级别日志"""
        if self.level <= self.DEBUG:
            formatted = self._format_message("DEBUG", message)
            self._write_to_file(formatted)
            if self.verbose:
                print(f"\033[90m[DEBUG] {message}\033[0m")  # 灰色
    
    def info(self, message: str) -> None:
        """信息级别日志"""
        if self.level <= self.INFO:
            formatted = self._format_message("INFO", message)
            self._write_to_file(formatted)
            if self.verbose:
                print(f"[INFO] {message}")
    
    def warning(self, message: str) -> None:
        """警告级别日志"""
        if self.level <= self.WARNING:
            formatted = self._format_message("WARNING", message)
            self._write_to_file(formatted)
            if self.verbose:
                print(f"\033[93m[WARNING] {message}\033[0m")  # 黄色
    
    def error(self, message: str) -> None:
        """错误级别日志"""
        if self.level <= self.ERROR:
            formatted = self._format_message("ERROR", message)
            self._write_to_file(formatted)
            if self.verbose:
                print(f"\033[91m[ERROR] {message}\033[0m")  # 红色
    
    def section(self, title: str) -> None:
        """输出章节标题"""
        separator = "=" * 50
        self._write_to_file(f"\n{separator}\n")
        self._write_to_file(f"{title}\n")
        self._write_to_file(f"{separator}\n\n")
        if self.verbose:
            print(f"\n{separator}")
            print(f"{title}")
            print(f"{separator}")
    
    def step(self, step_num: int, total_steps: int, description: str) -> None:
        """输出步骤信息"""
        message = f"【步骤 {step_num}/{total_steps}】{description}"
        self._write_to_file(f"\n{message}\n")
        self._write_to_file("-" * 40 + "\n")
        if self.verbose:
            print(f"\n{message}")
            print("-" * 40)
    
    def progress(self, current: int, total: int, description: str = "") -> None:
        """输出进度信息"""
        percentage = (current / total * 100) if total > 0 else 0
        message = f"进度: {current}/{total} ({percentage:.1f}%) {description}"
        self._write_to_file(f"{message}\n")
        if self.verbose:
            print(f"  → {message}")
    
    def ai_prompt(self, prompt_type: str, prompt_content: str) -> None:
        """记录AI提示词"""
        self._write_to_file(f"\n{'='*40}\n")
        self._write_to_file(f"AI提示词 [{prompt_type}]\n")
        self._write_to_file(f"{'='*40}\n")
        self._write_to_file(prompt_content)
        self._write_to_file(f"\n{'='*40}\n\n")
    
    def ai_response(self, response_type: str, response_content: str) -> None:
        """记录AI响应"""
        preview = response_content[:500] + "..." if len(response_content) > 500 else response_content
        self._write_to_file(f"\nAI响应 [{response_type}]:\n")
        self._write_to_file(f"{preview}\n\n")
    
    def stats(self, **kwargs) -> None:
        """输出统计信息"""
        self._write_to_file("\n统计信息:\n")
        for key, value in kwargs.items():
            line = f"  {key}: {value}"
            self._write_to_file(f"{line}\n")
            if self.verbose:
                print(line)
        self._write_to_file("\n")
    
    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)


# 全局日志实例
_logger: Optional[BookGeneratorLogger] = None


def get_logger(log_dir: str = "./logs", verbose: bool = True) -> BookGeneratorLogger:
    """获取全局日志实例
    
    Args:
        log_dir: 日志目录
        verbose: 是否详细输出
        
    Returns:
        BookGeneratorLogger实例
    """
    global _logger
    if _logger is None:
        _logger = BookGeneratorLogger(log_dir, verbose)
    return _logger


def set_logger(logger: BookGeneratorLogger) -> None:
    """设置全局日志实例"""
    global _logger
    _logger = logger
