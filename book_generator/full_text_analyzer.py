"""
全文分析模块

将大文本分批投喂给AI，让其完整阅读并理解全部内容，
然后基于全文理解生成准确的大纲和内容。
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass, asdict

from .doubao_client import DoubaoClient
from .config import get_config


@dataclass
class ReadingProgress:
    """阅读进度数据类"""
    total_chunks: int
    completed_chunks: int
    current_chunk: int
    accumulated_understanding: str
    status: str
    error_message: str = ""
    
    @property
    def progress_percentage(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100


class FullTextAnalyzer:
    """全文分析器
    
    将大文本分批投喂给AI，让其完整阅读并理解。
    采用渐进式阅读策略，每读一批就更新理解，最后形成完整认知。
    
    Attributes:
        client: 豆包API客户端
        config: 配置对象
        chunk_size: 每块文本大小
    """
    
    def __init__(self, chunk_size: int = 8000) -> None:
        """初始化全文分析器
        
        Args:
            chunk_size: 每块文本的字符数，默认8000
        """
        self.client = DoubaoClient()
        self.config = get_config()
        self.chunk_size = chunk_size
        self.progress = ReadingProgress(
            total_chunks=0,
            completed_chunks=0,
            current_chunk=0,
            accumulated_understanding="",
            status="idle"
        )
    
    def analyze_full_text(
        self,
        full_content: str,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """分析完整文本
        
        将大文本分批投喂给AI，让其完整阅读并理解全部内容。
        
        Args:
            full_content: 完整文本内容
            progress_callback: 进度回调函数
            
        Returns:
            完整的文本分析结果
        """
        total_chars = len(full_content)
        print(f"\n开始全文分析，总字符数: {total_chars:,}")
        print(f"分块大小: {self.chunk_size:,} 字符")
        
        # 计算分块数
        chunks = self._split_into_chunks(full_content)
        self.progress.total_chunks = len(chunks)
        
        print(f"共分 {len(chunks)} 块进行阅读\n")
        
        self.progress.status = "reading"
        accumulated_summary = ""
        
        # 逐块阅读
        for i, chunk in enumerate(chunks, 1):
            self.progress.current_chunk = i
            
            print(f"【阅读进度 {i}/{len(chunks)}】正在阅读第{i}块内容...")
            
            # 阅读当前块并更新理解
            chunk_summary = self._read_chunk(
                chunk=chunk,
                chunk_number=i,
                total_chunks=len(chunks),
                previous_understanding=accumulated_summary
            )
            
            accumulated_summary = chunk_summary
            self.progress.accumulated_understanding = accumulated_summary
            self.progress.completed_chunks = i
            
            # 显示当前理解摘要
            preview = accumulated_summary[:200] + "..." if len(accumulated_summary) > 200 else accumulated_summary
            print(f"  当前理解: {preview}\n")
            
            # 保存进度
            self._save_progress()
        
        # 全文阅读完成后，生成最终分析
        print("\n全文阅读完成，正在生成最终分析...")
        final_analysis = self._generate_final_analysis(accumulated_summary, full_content)
        
        self.progress.status = "completed"
        self._save_progress()
        
        return final_analysis
    
    def _split_into_chunks(self, content: str) -> List[str]:
        """将文本分割成块
        
        尽量在句子边界处分割，避免切断语义。
        
        Args:
            content: 文本内容
            
        Returns:
            文本块列表
        """
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            if end >= len(content):
                # 最后一块
                chunks.append(content[start:])
                break
            
            # 尝试在句子边界处断开
            break_point = self._find_sentence_break(content, end)
            chunks.append(content[start:break_point])
            start = break_point
        
        return chunks
    
    def _find_sentence_break(self, content: str, target_pos: int) -> int:
        """查找句子边界位置"""
        sentence_endings = {'。', '？', '！', '.', '?', '!', '\n'}
        search_range = min(200, target_pos)
        
        for i in range(target_pos, target_pos - search_range, -1):
            if i < len(content) and content[i-1] in sentence_endings:
                return i
        
        return target_pos
    
    def _read_chunk(
        self,
        chunk: str,
        chunk_number: int,
        total_chunks: int,
        previous_understanding: str
    ) -> str:
        """阅读单个文本块
        
        将当前块内容投喂给AI，结合之前的理解，更新整体认知。
        
        Args:
            chunk: 当前文本块
            chunk_number: 当前块编号
            total_chunks: 总块数
            previous_understanding: 之前的理解摘要
            
        Returns:
            更新后的理解摘要
        """
        system_prompt = """你是一位专业的文本分析专家，正在仔细阅读一部书籍的原始素材。
你的任务是理解文本内容，提取核心信息，并形成结构化的理解。
请保持客观、准确，不要添加文本中没有的信息。"""
        
        if chunk_number == 1:
            # 第一块：建立初始理解
            prompt = f"""请仔细阅读以下文本内容（第1部分，共{total_chunks}部分），并提取核心信息：

【文本内容】
{chunk}

【任务要求】
1. 识别文本的主题和核心内容
2. 提取主要人物、事件、观点
3. 记录关键细节和重要论述
4. 总结这部分的核心信息（300字以内）

请输出结构化的内容摘要，这将作为后续阅读的基础理解。"""
        else:
            # 后续块：结合之前的理解
            prompt = f"""请继续阅读以下文本内容（第{chunk_number}部分，共{total_chunks}部分）。

【之前的理解摘要】
{previous_understanding}

【当前阅读内容】
{chunk}

【任务要求】
1. 将当前内容与之前的理解整合
2. 补充新出现的人物、事件、观点
3. 完善对整体内容的认知
4. 更新整体理解摘要（500字以内）

请输出更新后的完整理解摘要。"""
        
        try:
            response = self.client.chat(prompt, system_prompt, temperature=0.3)
            return response.strip()
        except Exception as e:
            print(f"  警告: 第{chunk_number}块阅读失败: {e}")
            return previous_understanding + f"\n[第{chunk_number}块内容未能完整处理]"
    
    def _generate_final_analysis(
        self,
        full_understanding: str,
        original_content: str
    ) -> Dict[str, Any]:
        """生成最终分析
        
        基于完整理解，生成结构化的分析结果。
        
        Args:
            full_understanding: 完整理解摘要
            original_content: 原始内容（用于统计）
            
        Returns:
            结构化分析结果
        """
        system_prompt = """你是一位资深图书编辑，基于对全书内容的完整理解，生成结构化的分析报告。
请以JSON格式返回结果。"""
        
        prompt = f"""基于以下对全书内容的完整理解，生成详细的分析报告。

【完整理解】
{full_understanding}

【原始文本统计】
- 总字符数: {len(original_content):,}

【输出要求】
请以JSON格式返回以下信息：
{{
    "main_theme": "主要主题（50字以内）",
    "summary": "整体摘要（300字以内）",
    "key_points": ["要点1", "要点2", "要点3", "要点4", "要点5"],
    "structure": "内容结构描述",
    "characters": ["关键人物/群体", "..."],
    "topics": ["核心议题1", "核心议题2", "..."],
    "style": "文风特点",
    "target_audience": "目标读者"
}}"""
        
        try:
            response = self.client.chat(prompt, system_prompt, temperature=0.3)
            
            # 提取JSON
            json_str = self._extract_json(response)
            if json_str:
                return json.loads(json_str)
            else:
                return {
                    "main_theme": "基于全文分析的主题",
                    "summary": full_understanding[:500],
                    "key_points": ["要点待提取"],
                    "raw_understanding": full_understanding
                }
        except Exception as e:
            print(f"生成最终分析失败: {e}")
            return {
                "main_theme": "全文分析完成",
                "summary": full_understanding[:500],
                "key_points": ["要点待提取"],
                "error": str(e)
            }
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON字符串"""
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        return None
    
    def _save_progress(self) -> None:
        """保存阅读进度"""
        temp_dir = self.config.get_temp_dir()
        os.makedirs(temp_dir, exist_ok=True)
        
        progress_file = os.path.join(temp_dir, "reading_progress.json")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.progress), f, ensure_ascii=False, indent=2)
    
    def load_progress(self) -> bool:
        """加载阅读进度"""
        temp_dir = self.config.get_temp_dir()
        progress_file = os.path.join(temp_dir, "reading_progress.json")
        
        if not os.path.exists(progress_file):
            return False
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.progress = ReadingProgress(**data)
            return True
        except Exception:
            return False
