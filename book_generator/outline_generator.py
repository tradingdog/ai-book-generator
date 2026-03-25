"""
大纲生成模块

根据文本分析结果生成书籍大纲，支持多级章节结构。
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .doubao_client import DoubaoClient
from .config import get_config


@dataclass
class SectionOutline:
    """小节大纲数据类（三级标题）"""
    section_number: str
    title: str
    target_words: int
    summary: str
    key_points: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SectionOutline':
        return cls(**data)


@dataclass
class SubChapterOutline:
    """子章节大纲数据类（二级标题）"""
    subchapter_number: str
    title: str
    target_words: int
    summary: str
    sections: List[SectionOutline]
    key_points: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'subchapter_number': self.subchapter_number,
            'title': self.title,
            'target_words': self.target_words,
            'summary': self.summary,
            'sections': [s.to_dict() for s in self.sections],
            'key_points': self.key_points
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubChapterOutline':
        sections = [SectionOutline.from_dict(s) for s in data.get('sections', [])]
        return cls(
            subchapter_number=data.get('subchapter_number', ''),
            title=data.get('title', ''),
            target_words=data.get('target_words', 0),
            summary=data.get('summary', ''),
            sections=sections,
            key_points=data.get('key_points', [])
        )


@dataclass
class ChapterOutline:
    """章节大纲数据类（一级标题）"""
    chapter_number: int
    title: str
    target_words: int
    summary: str
    subchapters: List[SubChapterOutline]
    key_points: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'chapter_number': self.chapter_number,
            'title': self.title,
            'target_words': self.target_words,
            'summary': self.summary,
            'subchapters': [s.to_dict() for s in self.subchapters],
            'key_points': self.key_points
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChapterOutline':
        subchapters = [SubChapterOutline.from_dict(s) for s in data.get('subchapters', [])]
        return cls(
            chapter_number=data.get('chapter_number', 0),
            title=data.get('title', ''),
            target_words=data.get('target_words', 0),
            summary=data.get('summary', ''),
            subchapters=subchapters,
            key_points=data.get('key_points', [])
        )


@dataclass
class BookOutline:
    """书籍大纲数据类"""
    title: str
    subtitle: str
    preface_summary: str
    chapters: List[ChapterOutline]
    total_words: int
    style: str
    
    def to_dict(self) -> Dict[str, Any]:
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
        chapters = [ChapterOutline.from_dict(c) for c in data.get('chapters', [])]
        return cls(
            title=data.get('title', ''),
            subtitle=data.get('subtitle', ''),
            preface_summary=data.get('preface_summary', ''),
            chapters=chapters,
            total_words=data.get('total_words', 0),
            style=data.get('style', '')
        )


class OutlineGenerator:
    """大纲生成器"""
    
    def __init__(self) -> None:
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
        """生成书籍大纲"""
        style = self.config.get_style()
        if total_chapters is None:
            total_chapters = self.config.get_total_chapters()
        if chapter_target_words is None:
            chapter_target_words = self.config.get_chapter_target_words()
        
        chapter_target = chapter_target_words
        
        system_prompt = """你是一位资深图书编辑和作家，擅长将素材重组为结构完整的书籍。
请根据提供的内容分析，设计一部书籍的完整大纲，要求结构清晰、层级分明。
文风要求：平实朴素，逻辑清晰，避免华丽辞藻。
必须以JSON格式返回结果。"""
        
        prompt = f"""请为以下内容设计一部书籍的完整大纲。

【内容分析】
{json.dumps(content_analysis, ensure_ascii=False, indent=2)}

【原始文本样本】
{sample_content[:5000]}

【设计要求】
1. 书籍总字数约{total_words}字
2. 共{total_chapters}章（一级标题）
3. 每章包含3-4个子章节（二级标题，如1.1, 1.2, 1.3）
4. 每个子章节包含2-3个小节（三级标题，如1.1.1, 1.1.2）
5. 每章约{chapter_target}字
6. 文风：{"平实朴素，通俗易懂" if style == "plain" else style}
7. 必须包含自序
8. 章节之间要有逻辑递进关系
9. 子章节和小节要细致划分，像真实学术书籍一样详细

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
            "target_words": {chapter_target},
            "summary": "本章内容概要（100字左右）",
            "subchapters": [
                {{
                    "subchapter_number": "1.1",
                    "title": "第一节标题",
                    "target_words": {chapter_target // 3},
                    "summary": "本节概要",
                    "sections": [
                        {{
                            "section_number": "1.1.1",
                            "title": "第一小节标题",
                            "target_words": {chapter_target // 6},
                            "summary": "小节概要",
                            "key_points": ["要点1", "要点2"]
                        }}
                    ],
                    "key_points": ["要点1", "要点2"]
                }}
            ],
            "key_points": ["要点1", "要点2", "要点3"]
        }}
    ],
    "total_words": {total_words},
    "style": "{style}"
}}

【重要提示】
- 每个章必须有3-4个子章节（二级标题）
- 每个子章节必须有2-3个小节（三级标题）
- 层级结构要清晰，像真实出版的学术书籍一样
- 标题要具体，能准确反映内容"""
        
        try:
            response = self.client.chat(prompt, system_prompt, temperature=0.7)
            
            json_str = self._extract_json(response)
            if not json_str:
                raise ValueError("无法从响应中提取JSON")
            
            data = json.loads(json_str)
            outline = self._validate_and_fix_outline(data, total_chapters, chapter_target)
            
            return outline
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
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
        """验证并修复大纲数据"""
        title = data.get('title', '未命名书籍')
        subtitle = data.get('subtitle', '')
        preface_summary = data.get('preface_summary', '本书是基于原始素材重新整理而成的作品。')
        style = data.get('style', 'plain')
        
        chapters_data = data.get('chapters', [])
        chapters: List[ChapterOutline] = []
        
        for i, ch_data in enumerate(chapters_data[:expected_chapters], 1):
            subchapters_data = ch_data.get('subchapters', [])
            subchapters: List[SubChapterOutline] = []
            
            if subchapters_data:
                for j, sub_data in enumerate(subchapters_data, 1):
                    sections_data = sub_data.get('sections', [])
                    sections: List[SectionOutline] = []
                    
                    if sections_data:
                        for k, sec_data in enumerate(sections_data, 1):
                            sections.append(SectionOutline(
                                section_number=sec_data.get('section_number', f'{i}.{j}.{k}'),
                                title=sec_data.get('title', f'第{k}小节'),
                                target_words=sec_data.get('target_words', target_words // 6),
                                summary=sec_data.get('summary', '小节概要'),
                                key_points=sec_data.get('key_points', ['要点'])
                            ))
                    
                    subchapters.append(SubChapterOutline(
                        subchapter_number=sub_data.get('subchapter_number', f'{i}.{j}'),
                        title=sub_data.get('title', f'第{j}节'),
                        target_words=sub_data.get('target_words', target_words // 3),
                        summary=sub_data.get('summary', '本节概要'),
                        sections=sections if sections else [
                            SectionOutline(
                                section_number=f'{i}.{j}.1',
                                title='第一小节',
                                target_words=target_words // 6,
                                summary='小节概要',
                                key_points=['要点']
                            )
                        ],
                        key_points=sub_data.get('key_points', ['要点'])
                    ))
            
            if not subchapters:
                for j in range(1, 4):
                    sections = []
                    for k in range(1, 3):
                        sections.append(SectionOutline(
                            section_number=f'{i}.{j}.{k}',
                            title=f'第{j}.{k}小节',
                            target_words=target_words // 6,
                            summary='小节概要',
                            key_points=['要点']
                        ))
                    
                    subchapters.append(SubChapterOutline(
                        subchapter_number=f'{i}.{j}',
                        title=f'第{j}节',
                        target_words=target_words // 3,
                        summary=f'第{j}节概要',
                        sections=sections,
                        key_points=['要点']
                    ))
            
            chapters.append(ChapterOutline(
                chapter_number=ch_data.get('chapter_number', i),
                title=ch_data.get('title', f'第{i}章'),
                target_words=ch_data.get('target_words', target_words),
                summary=ch_data.get('summary', f'本章主要讲述相关内容。'),
                subchapters=subchapters,
                key_points=ch_data.get('key_points', ['要点待补充'])
            ))
        
        while len(chapters) < expected_chapters:
            i = len(chapters) + 1
            subchapters = []
            for j in range(1, 4):
                sections = []
                for k in range(1, 3):
                    sections.append(SectionOutline(
                        section_number=f'{i}.{j}.{k}',
                        title=f'第{j}.{k}小节',
                        target_words=target_words // 6,
                        summary='小节概要',
                        key_points=['要点']
                    ))
                subchapters.append(SubChapterOutline(
                    subchapter_number=f'{i}.{j}',
                    title=f'第{j}节',
                    target_words=target_words // 3,
                    summary=f'第{j}节概要',
                    sections=sections,
                    key_points=['要点']
                ))
            
            chapters.append(ChapterOutline(
                chapter_number=i,
                title=f'第{i}章',
                target_words=target_words,
                summary=f'本章为第{i}章，将深入探讨相关内容。',
                subchapters=subchapters,
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
        """创建默认大纲"""
        chapters: List[ChapterOutline] = []
        
        for i in range(1, total_chapters + 1):
            subchapters: List[SubChapterOutline] = []
            for j in range(1, 4):
                sections: List[SectionOutline] = []
                for k in range(1, 3):
                    sections.append(SectionOutline(
                        section_number=f'{i}.{j}.{k}',
                        title=f'第{j}.{k}小节',
                        target_words=target_words // 6,
                        summary='小节概要',
                        key_points=['要点']
                    ))
                
                subchapters.append(SubChapterOutline(
                    subchapter_number=f'{i}.{j}',
                    title=f'第{j}节',
                    target_words=target_words // 3,
                    summary=f'第{j}节概要',
                    sections=sections,
                    key_points=['要点']
                ))
            
            chapters.append(ChapterOutline(
                chapter_number=i,
                title=f'第{i}章 主题内容',
                target_words=target_words,
                summary=f'本章将详细探讨第{i}部分的核心内容。',
                subchapters=subchapters,
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
        """保存大纲到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_outline(self, filepath: str) -> BookOutline:
        """从JSON文件加载大纲"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return BookOutline.from_dict(data)
