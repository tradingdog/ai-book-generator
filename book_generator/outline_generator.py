"""
大纲生成模块

根据文本分析结果生成书籍大纲，包括章节结构、标题和字数分配。
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .doubao_client import DoubaoClient
from .config import get_config


@dataclass
class ChapterOutline:
    """章节大纲数据类
    
    Attributes:
        chapter_number: 章节序号
        title: 章节标题
        subsections: 小节列表
        target_words: 目标字数
        summary: 章节内容概要
        key_points: 关键要点列表
    """
    chapter_number: int
    title: str
    subsections: List[str]
    target_words: int
    summary: str
    key_points: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChapterOutline':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class BookOutline:
    """书籍大纲数据类
    
    Attributes:
        title: 书籍标题
        subtitle: 副标题
        preface_summary: 自序概要
        chapters: 章节大纲列表
        total_words: 总字数
        style: 文风描述
    """
    title: str
    subtitle: str
    preface_summary: str
    chapters: List[ChapterOutline]
    total_words: int
    style: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'title': self.title,
            'subtitle': self.subtitle,
            'preface_summary': self.preface_summary,
            'chapters': [c.to_dict() for c in self.chapters],
            'total_words': self.total_words,
            'style': self.style
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookOutline':
        """从字典创建实例"""
        chapters = [ChapterOutline.from_dict(c) for c in data.get('chapters', [])]
        return cls(
            title=data.get('title', ''),
            subtitle=data.get('subtitle', ''),
            preface_summary=data.get('preface_summary', ''),
            chapters=chapters,
            total_words=data.get('total_words', 0),
            style=data.get('style', 'plain')
        )


class OutlineGenerator:
    """大纲生成器
    
    基于文本分析结果，使用AI生成完整的书籍大纲。
    
    Attributes:
        client: 豆包API客户端
        config: 配置对象
    
    Example:
        >>> generator = OutlineGenerator()
        >>> outline = generator.generate_outline(analysis_result, total_words=500000)
    """
    
    def __init__(self) -> None:
        """初始化大纲生成器"""
        self.client = DoubaoClient()
        self.config = get_config()
    
    def generate_outline(
        self,
        content_analysis: Dict[str, Any],
        total_words: int,
        sample_content: str = "",
        total_chapters: int = None,
        chapter_target_words: int = None
    ) -> BookOutline:
        """生成书籍大纲
        
        基于内容分析结果，生成完整的书籍结构大纲。
        
        Args:
            content_analysis: 内容分析结果字典
            total_words: 目标总字数
            sample_content: 原始文本样本（用于AI理解原文风格）
            total_chapters: 总章节数（可选，默认从配置读取）
            chapter_target_words: 每章目标字数（可选，默认从配置读取）
            
        Returns:
            完整的书籍大纲对象
        """
        style = self.config.get_style()
        # 使用传入的参数或从配置读取
        if total_chapters is None:
            total_chapters = self.config.get_total_chapters()
        if chapter_target_words is None:
            chapter_target_words = self.config.get_chapter_target_words()
        
        chapter_target = chapter_target_words
        
        # 构建提示词
        system_prompt = """你是一位资深图书编辑和作家，擅长将素材重组为结构完整的书籍。
请根据提供的内容分析，设计一部书籍的完整大纲。
文风要求：平实朴素，逻辑清晰，避免华丽辞藻。
必须以JSON格式返回结果。"""
        
        prompt = f"""请为以下内容设计一部书籍的完整大纲。

【内容分析】
{json.dumps(content_analysis, ensure_ascii=False, indent=2)}

【原始文本样本】
{sample_content[:5000]}

【设计要求】
1. 书籍总字数约{total_words}字
2. 共{total_chapters}章
3. 每章约{chapter_target}字
4. 文风：{"平实朴素，通俗易懂" if style == "plain" else style}
5. 必须包含自序
6. 章节之间要有逻辑递进关系

【输出格式】
请以JSON格式返回，确保可以被直接解析：
{{
    "title": "书籍主标题",
    "subtitle": "副标题",
    "preface_summary": "自序概要（100字左右）",
    "chapters": [
        {{
            "chapter_number": 1,
            "title": "第一章标题",
            "subsections": ["小节1", "小节2", "小节3"],
            "target_words": {chapter_target},
            "summary": "本章内容概要（100字左右）",
            "key_points": ["要点1", "要点2", "要点3"]
        }}
    ],
    "total_words": {total_words},
    "style": "{style}"
}}"""
        
        try:
            response = self.client.chat(prompt, system_prompt, temperature=0.7)
            
            # 提取JSON
            json_str = self._extract_json(response)
            if not json_str:
                raise ValueError("无法从响应中提取JSON")
            
            data = json.loads(json_str)
            
            # 验证数据完整性
            outline = self._validate_and_fix_outline(data, total_chapters, chapter_target)
            
            return outline
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {response}")
            # 返回默认大纲
            return self._create_default_outline(total_chapters, chapter_target)
        except Exception as e:
            print(f"生成大纲失败: {e}")
            return self._create_default_outline(total_chapters, chapter_target)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON字符串"""
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        return None
    
    def _validate_and_fix_outline(
        self,
        data: Dict[str, Any],
        expected_chapters: int,
        target_words: int
    ) -> BookOutline:
        """验证并修复大纲数据
        
        Args:
            data: 解析后的大纲数据
            expected_chapters: 期望的章节数
            target_words: 每章目标字数
            
        Returns:
            验证后的大纲对象
        """
        # 确保基本字段存在
        title = data.get('title', '未命名书籍')
        subtitle = data.get('subtitle', '')
        preface_summary = data.get('preface_summary', '本书是基于原始素材重新整理而成的作品。')
        style = data.get('style', 'plain')
        
        # 处理章节数据
        chapters_data = data.get('chapters', [])
        chapters: List[ChapterOutline] = []
        
        for i, ch_data in enumerate(chapters_data[:expected_chapters], 1):
            chapter = ChapterOutline(
                chapter_number=ch_data.get('chapter_number', i),
                title=ch_data.get('title', f'第{i}章'),
                subsections=ch_data.get('subsections', ['第一节', '第二节', '第三节']),
                target_words=ch_data.get('target_words', target_words),
                summary=ch_data.get('summary', f'本章主要讲述相关内容。'),
                key_points=ch_data.get('key_points', ['要点待补充'])
            )
            chapters.append(chapter)
        
        # 如果章节不足，补充默认章节
        while len(chapters) < expected_chapters:
            i = len(chapters) + 1
            chapters.append(ChapterOutline(
                chapter_number=i,
                title=f'第{i}章',
                subsections=['概述', '详细内容', '总结'],
                target_words=target_words,
                summary=f'本章为第{i}章，将深入探讨相关内容。',
                key_points=['核心内容']
            ))
        
        total_words = sum(ch.target_words for ch in chapters)
        
        return BookOutline(
            title=title,
            subtitle=subtitle,
            preface_summary=preface_summary,
            chapters=chapters,
            total_words=total_words,
            style=style
        )
    
    def _create_default_outline(
        self,
        total_chapters: int,
        target_words: int
    ) -> BookOutline:
        """创建默认大纲
        
        当AI生成失败时使用的备用方案。
        
        Args:
            total_chapters: 章节数
            target_words: 每章目标字数
            
        Returns:
            默认大纲对象
        """
        chapters: List[ChapterOutline] = []
        
        for i in range(1, total_chapters + 1):
            chapters.append(ChapterOutline(
                chapter_number=i,
                title=f'第{i}章 主题内容',
                subsections=['背景介绍', '主要内容', '深入分析', '本章小结'],
                target_words=target_words,
                summary=f'本章将详细探讨第{i}部分的核心内容。',
                key_points=['核心概念', '重要观点', '实践意义']
            ))
        
        return BookOutline(
            title='重构之作',
            subtitle='基于原始素材的全新呈现',
            preface_summary='本书是基于原始素材重新整理而成的作品，力求以平实朴素的语言呈现内容。',
            chapters=chapters,
            total_words=total_chapters * target_words,
            style='plain'
        )
    
    def save_outline(self, outline: BookOutline, filepath: str) -> None:
        """保存大纲到JSON文件
        
        Args:
            outline: 大纲对象
            filepath: 保存路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_outline(self, filepath: str) -> BookOutline:
        """从JSON文件加载大纲
        
        Args:
            filepath: 文件路径
            
        Returns:
            大纲对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return BookOutline.from_dict(data)
