"""
文件读取模块

支持读取大文本文件（md/txt），提供分块读取功能。
"""

import os
import re
from typing import List, Generator, Optional
from pathlib import Path


class FileReader:
    """文件读取类
    
    专门用于读取大文本文件，支持按行读取和按块读取两种方式。
    自动处理文件编码，支持UTF-8和GBK等常见编码。
    
    Attributes:
        file_path: 文件路径
        encoding: 文件编码
        file_size: 文件大小（字节）
    
    Example:
        >>> reader = FileReader("large_file.md")
        >>> content = reader.read_all()
        >>> for chunk in reader.read_chunks(chunk_size=4000):
        ...     process(chunk)
    """
    
    def __init__(self, file_path: str) -> None:
        """初始化文件读取器
        
        Args:
            file_path: 要读取的文件路径
            
        Raises:
            FileNotFoundError: 文件不存在时
            ValueError: 文件格式不支持时
        """
        self.file_path = Path(file_path)
        self.encoding: Optional[str] = None
        
        # 验证文件存在
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 验证文件格式
        if not self._is_supported_format():
            raise ValueError(f"不支持的文件格式: {self.file_path.suffix}，仅支持.md和.txt文件")
        
        # 检测文件编码
        self.encoding = self._detect_encoding()
        self.file_size = self.file_path.stat().st_size
    
    def _is_supported_format(self) -> bool:
        """检查文件格式是否支持
        
        Returns:
            是否支持的布尔值
        """
        supported_extensions = {'.md', '.txt', '.markdown'}
        return self.file_path.suffix.lower() in supported_extensions
    
    def _detect_encoding(self) -> str:
        """检测文件编码
        
        尝试使用UTF-8读取，失败则尝试GBK。
        
        Returns:
            检测到的编码格式
        """
        encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings_to_try:
            try:
                with open(self.file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # 尝试读取前1KB
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # 默认返回UTF-8
        return 'utf-8'
    
    def read_all(self) -> str:
        """读取整个文件内容
        
        注意：对于超大文件，建议使用read_chunks方法分块读取。
        
        Returns:
            文件完整内容字符串
            
        Raises:
            IOError: 读取文件失败时
        """
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                return f.read()
        except Exception as e:
            raise IOError(f"读取文件失败: {e}")
    
    def read_lines(self) -> Generator[str, None, None]:
        """逐行读取文件
        
        内存友好的读取方式，适合处理大文件。
        
        Yields:
            文件的每一行内容（包含换行符）
        """
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                for line in f:
                    yield line
        except Exception as e:
            raise IOError(f"读取文件失败: {e}")
    
    def read_chunks(self, chunk_size: int = 4000, overlap: int = 500) -> Generator[str, None, None]:
        """按块读取文件内容
        
        将文件内容分割成固定大小的块，块之间可以有重叠。
        分割时会尽量在句子边界处断开，避免切断词语。
        
        Args:
            chunk_size: 每块的目标字符数
            overlap: 块之间的重叠字符数
            
        Yields:
            文本块字符串
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size必须大于0")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap必须大于等于0且小于chunk_size")
        
        content = self.read_all()
        
        if len(content) <= chunk_size:
            yield content
            return
        
        start = 0
        while start < len(content):
            end = start + chunk_size
            
            if end >= len(content):
                # 最后一块
                yield content[start:]
                break
            
            # 尝试在句子边界处断开
            # 优先在句号、问号、感叹号后断开
            break_point = self._find_sentence_break(content, end)
            
            if break_point <= start:
                # 如果找不到合适的断点，就在chunk_size处断开
                break_point = end
            
            yield content[start:break_point]
            
            # 下一块的起始位置（考虑重叠）
            start = break_point - overlap
            if start < 0:
                start = 0
    
    def _find_sentence_break(self, content: str, target_pos: int) -> int:
        """查找句子边界位置
        
        从target_pos向前查找，找到最近的句子结束符位置。
        
        Args:
            content: 文本内容
            target_pos: 目标位置
            
        Returns:
            找到的断点位置，如果找不到则返回target_pos
        """
        # 句子结束符
        sentence_endings = {'。', '？', '！', '.', '?', '!', '\n'}
        
        # 向前查找最多200个字符
        search_range = min(200, target_pos)
        
        for i in range(target_pos, target_pos - search_range, -1):
            if i < len(content) and content[i-1] in sentence_endings:
                return i
        
        # 如果没找到句子边界，尝试在空格或标点处断开
        for i in range(target_pos, target_pos - search_range, -1):
            if i < len(content) and content[i-1] in {' ', '，', ',', '、', ';', '；'}:
                return i
        
        return target_pos
    
    def get_statistics(self) -> dict:
        """获取文件统计信息
        
        Returns:
            包含文件统计信息的字典
        """
        content = self.read_all()
        
        # 统计字符数（不含空白）
        char_count = len(content)
        char_count_no_space = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
        
        # 统计行数
        line_count = content.count('\n') + 1
        
        # 估算中文字数（中文字符 + 英文单词数）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        estimated_words = chinese_chars + english_words
        
        return {
            'file_path': str(self.file_path),
            'file_size_bytes': self.file_size,
            'file_size_kb': round(self.file_size / 1024, 2),
            'encoding': self.encoding,
            'total_chars': char_count,
            'chars_no_space': char_count_no_space,
            'line_count': line_count,
            'chinese_chars': chinese_chars,
            'english_words': english_words,
            'estimated_words': estimated_words
        }
    
    def estimate_reading_time(self, words_per_minute: int = 300) -> float:
        """估算阅读时间
        
        Args:
            words_per_minute: 每分钟阅读字数，默认300
            
        Returns:
            预估阅读时间（分钟）
        """
        stats = self.get_statistics()
        return round(stats['estimated_words'] / words_per_minute, 2)


def read_text_file(file_path: str, chunk_size: Optional[int] = None, overlap: int = 500) -> str | Generator[str, None, None]:
    """便捷函数：读取文本文件
    
    如果不指定chunk_size，则返回完整内容；
    如果指定chunk_size，则返回生成器，分块读取。
    
    Args:
        file_path: 文件路径
        chunk_size: 分块大小，None表示不分块
        overlap: 块间重叠大小
        
    Returns:
        完整内容字符串或文本块生成器
    """
    reader = FileReader(file_path)
    
    if chunk_size is None:
        return reader.read_all()
    else:
        return reader.read_chunks(chunk_size, overlap)


def get_file_stats(file_path: str) -> dict:
    """便捷函数：获取文件统计信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件统计信息字典
    """
    reader = FileReader(file_path)
    return reader.get_statistics()
