"""
内容生成模块

根据大纲逐章生成书籍内容，支持上下文连贯和进度保存。
"""

import os
import json
import time
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass, asdict

from .doubao_client import DoubaoClient
from .outline_generator import BookOutline, ChapterOutline
from .config import get_config


@dataclass
class GenerationProgress:
    """生成进度数据类
    
    Attributes:
        total_chapters: 总章节数
        completed_chapters: 已完成章节数
        current_chapter: 当前正在生成的章节
        generated_content: 已生成的内容字典
        status: 状态（running/paused/completed/error）
        error_message: 错误信息
    """
    total_chapters: int
    completed_chapters: int
    current_chapter: int
    generated_content: Dict[int, str]
    status: str
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationProgress':
        """从字典创建实例"""
        return cls(**data)
    
    @property
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return (self.completed_chapters / self.total_chapters) * 100


class ContentGenerator:
    """内容生成器
    
    根据大纲逐章生成书籍内容，确保上下文连贯。
    
    Attributes:
        client: 豆包API客户端
        config: 配置对象
        progress: 生成进度
        original_content: 原始文本内容（用于素材提取）
    
    Example:
        >>> generator = ContentGenerator(original_content)
        >>> for progress in generator.generate_book(outline):
        ...     print(f"进度: {progress.progress_percentage:.1f}%")
    """
    
    def __init__(self, original_content: str = "") -> None:
        """初始化内容生成器
        
        Args:
            original_content: 原始文本内容，用于提取素材
        """
        self.client = DoubaoClient()
        self.config = get_config()
        self.original_content = original_content
        self.progress = GenerationProgress(
            total_chapters=0,
            completed_chapters=0,
            current_chapter=0,
            generated_content={},
            status="idle"
        )
    
    def generate_book(
        self,
        outline: BookOutline,
        resume: bool = False
    ) -> Generator[GenerationProgress, None, None]:
        """生成整本书籍内容
        
        逐章生成内容，每完成一章就yield进度更新。
        
        Args:
            outline: 书籍大纲
            resume: 是否从上次中断处继续
            
        Yields:
            生成进度对象
        """
        self.progress.total_chapters = len(outline.chapters)
        
        # 尝试恢复进度
        if resume:
            self._load_progress()
        
        self.progress.status = "running"
        
        try:
            # 生成自序
            if self.config.should_generate_preface() and 0 not in self.progress.generated_content:
                self.progress.current_chapter = 0
                yield self.progress
                
                preface = self._generate_preface(outline)
                self.progress.generated_content[0] = preface
                self.progress.completed_chapters += 1
                self._save_progress()
                yield self.progress
            
            # 逐章生成
            for chapter in outline.chapters:
                chapter_num = chapter.chapter_number
                
                # 跳过已完成的章节
                if chapter_num in self.progress.generated_content:
                    continue
                
                self.progress.current_chapter = chapter_num
                yield self.progress
                
                # 生成章节内容
                chapter_content = self._generate_chapter(chapter, outline)
                self.progress.generated_content[chapter_num] = chapter_content
                self.progress.completed_chapters += 1
                
                # 保存进度
                self._save_progress()
                yield self.progress
            
            self.progress.status = "completed"
            yield self.progress
            
        except Exception as e:
            self.progress.status = "error"
            self.progress.error_message = str(e)
            self._save_progress()
            yield self.progress
            raise
    
    def _generate_preface(self, outline: BookOutline) -> str:
        """生成自序
        
        Args:
            outline: 书籍大纲
            
        Returns:
            自序内容
        """
        system_prompt = """你是一位作家，正在为自己的新书撰写自序。
文风要求：平实朴素，真诚自然，避免华丽辞藻。
自序应该介绍写作背景、书籍内容概要，以及对读者的期望。"""
        
        style_desc = "平实朴素，通俗易懂，逻辑清晰"
        if outline.style == "literary":
            style_desc = "文学性强，富有文采"
        elif outline.style == "academic":
            style_desc = "学术严谨，论述深入"
        
        prompt = f"""请为书籍《{outline.title}》撰写一篇自序。

【书籍信息】
- 主标题：{outline.title}
- 副标题：{outline.subtitle}
- 文风：{style_desc}
- 总章节数：{len(outline.chapters)}章

【自序概要】
{outline.preface_summary}

【章节主题】
{chr(10).join([f"第{ch.chapter_number}章：{ch.title}" for ch in outline.chapters[:5]])}
...

【写作要求】
1. 字数约2000-3000字
2. 介绍写作背景和动机
3. 概述书籍的主要内容和结构
4. 说明本书的特点和价值
5. 对读者表达期望
6. 文风平实朴素，真诚自然

请直接输出自序正文，不需要标题。"""
        
        print(f"正在生成自序...")
        response = self.client.chat(prompt, system_prompt, temperature=0.7)
        return response
    
    def _generate_chapter(self, chapter: ChapterOutline, outline: BookOutline) -> str:
        """生成单个章节内容
        
        Args:
            chapter: 章节大纲
            outline: 完整大纲（用于上下文）
            
        Returns:
            章节完整内容
        """
        system_prompt = """你是一位专业作家，正在撰写书籍章节。
文风要求：平实朴素，逻辑清晰，避免华丽辞藻和过度修饰。
内容必须基于提供的素材，重新组织表达，保持原创性。"""
        
        # 获取前文摘要（用于保持连贯性）
        previous_summary = self._get_previous_summary(chapter.chapter_number)
        
        # 提取相关素材
        relevant_materials = self._extract_relevant_materials(chapter)
        
        style_desc = "平实朴素，通俗易懂"
        if outline.style == "literary":
            style_desc = "文学性较强，有一定文采"
        elif outline.style == "academic":
            style_desc = "学术严谨，论述深入"
        
        prompt = f"""请撰写书籍《{outline.title}》的第{chapter.chapter_number}章。

【章节信息】
- 章节号：第{chapter.chapter_number}章
- 标题：{chapter.title}
- 目标字数：{chapter.target_words}字
- 小节安排：{', '.join(chapter.subsections)}

【本章概要】
{chapter.summary}

【关键要点】
{chr(10).join(['- ' + kp for kp in chapter.key_points])}

【前文摘要】
{previous_summary if previous_summary else "（本章为开篇）"}

【参考素材】
{relevant_materials[:3000]}

【写作要求】
1. 字数严格控制在{chapter.target_words}字左右（允许±10%误差）
2. 文风：{style_desc}
3. 必须包含所有小节内容
4. 与上文保持逻辑连贯
5. 语言通顺，无逻辑错误
6. 基于素材重新组织，不要直接复制
7. 使用平实的语言，避免堆砌辞藻

【输出格式】
第{chapter.chapter_number}章 {chapter.title}

（正文内容，包含各小节）

本章小结
（简要总结本章要点，200字左右）"""
        
        print(f"正在生成第{chapter.chapter_number}章: {chapter.title}...")
        
        # 使用流式生成以显示进度
        content_parts = []
        for chunk in self.client.chat_stream(prompt, system_prompt, temperature=0.7):
            content_parts.append(chunk)
        
        content = ''.join(content_parts)
        
        # 验证字数
        word_count = self._count_chinese_words(content)
        print(f"第{chapter.chapter_number}章生成完成，字数：{word_count}")
        
        return content
    
    def _get_previous_summary(self, current_chapter_num: int) -> str:
        """获取前一章的摘要
        
        Args:
            current_chapter_num: 当前章节号
            
        Returns:
            前一章的摘要，如果没有则返回空字符串
        """
        if current_chapter_num <= 1:
            return ""
        
        prev_chapter_num = current_chapter_num - 1
        if prev_chapter_num not in self.progress.generated_content:
            return ""
        
        prev_content = self.progress.generated_content[prev_chapter_num]
        
        # 提取最后500字作为摘要
        summary = prev_content[-500:] if len(prev_content) > 500 else prev_content
        return f"前一章结尾内容：{summary}"
    
    def _extract_relevant_materials(self, chapter: ChapterOutline) -> str:
        """从原始内容中提取与章节相关的素材
        
        Args:
            chapter: 章节大纲
            
        Returns:
            相关素材文本
        """
        if not self.original_content:
            return ""
        
        # 简单策略：根据章节号大致分配原始内容
        # 实际项目中可以使用更智能的语义匹配
        total_chars = len(self.original_content)
        chars_per_chapter = total_chars // max(self.progress.total_chapters, 1)
        
        start_pos = (chapter.chapter_number - 1) * chars_per_chapter
        end_pos = start_pos + chars_per_chapter + 2000  # 多取一些保证连贯性
        
        return self.original_content[start_pos:end_pos]
    
    def _count_chinese_words(self, text: str) -> int:
        """统计中文字数
        
        中文字符 + 英文单词数
        
        Args:
            text: 文本内容
            
        Returns:
            字数统计
        """
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars + english_words
    
    def _save_progress(self) -> None:
        """保存生成进度到文件"""
        temp_dir = self.config.get_temp_dir()
        os.makedirs(temp_dir, exist_ok=True)
        
        progress_file = os.path.join(temp_dir, "generation_progress.json")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _load_progress(self) -> bool:
        """从文件加载生成进度
        
        Returns:
            是否成功加载
        """
        temp_dir = self.config.get_temp_dir()
        progress_file = os.path.join(temp_dir, "generation_progress.json")
        
        if not os.path.exists(progress_file):
            return False
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.progress = GenerationProgress.from_dict(data)
            return True
        except Exception as e:
            print(f"加载进度失败: {e}")
            return False
    
    def get_full_book_content(self, outline: BookOutline) -> str:
        """获取完整的书籍内容
        
        Args:
            outline: 书籍大纲
            
        Returns:
            完整的书籍文本
        """
        parts = []
        
        # 书名
        parts.append(f"{outline.title}")
        if outline.subtitle:
            parts.append(f"{outline.subtitle}")
        parts.append("\n" + "=" * 40 + "\n")
        
        # 自序
        if 0 in self.progress.generated_content:
            parts.append("自序")
            parts.append("\n" + "-" * 40 + "\n")
            parts.append(self.progress.generated_content[0])
            parts.append("\n\n")
        
        # 目录
        parts.append("目录")
        parts.append("\n" + "-" * 40 + "\n")
        if 0 in self.progress.generated_content:
            parts.append("自序\n")
        for ch in outline.chapters:
            parts.append(f"第{ch.chapter_number}章 {ch.title}\n")
        parts.append("\n\n")
        
        # 各章节
        for ch in outline.chapters:
            if ch.chapter_number in self.progress.generated_content:
                parts.append(self.progress.generated_content[ch.chapter_number])
                parts.append("\n\n")
        
        return '\n'.join(parts)
