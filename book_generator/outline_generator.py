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
请根据提供的内容分析，设计一部书籍的完整大纲。

【强制要求】
1. 必须返回纯JSON格式，不要包含任何markdown标记（如```json）
2. 不要添加任何JSON之外的文字说明
3. 确保JSON格式完全正确，所有字符串使用双引号
4. 所有字段必须填写，不能留空
5. 标题必须基于原文内容提炼，不能是占位符

文风要求：平实朴素，逻辑清晰，避免华丽辞藻。"""
        
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

【标题要求 - 非常重要】
- 章节标题必须基于原文主题内容提炼，例如："捭阖之道"、"反应之术"、"内楗之理"
- 不能使用"第X章 主题内容"这样的占位符
- 标题要具体、有意义，读者一看就知道本章讲什么
- 子章节和小节标题同样要具体，反映实际内容

【输出格式】
必须返回纯JSON，格式如下：
{{
    "title": "基于原文主题的书籍标题",
    "subtitle": "副标题",
    "preface_summary": "自序概要（100字左右）",
    "chapters": [
        {{
            "chapter_number": 1,
            "title": "具体章节标题（如：捭阖之道）",
            "target_words": {chapter_target},
            "summary": "本章内容概要（100字左右）",
            "subchapters": [
                {{
                    "subchapter_number": "1.1",
                    "title": "具体子章节标题",
                    "target_words": {chapter_target // 3},
                    "summary": "本节概要",
                    "sections": [
                        {{
                            "section_number": "1.1.1",
                            "title": "具体小节标题",
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
- 只返回JSON，不要有任何其他文字
- 所有标题必须基于原文内容，不能是占位符
- 确保JSON格式正确，可以被Python json.loads()解析"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat(prompt, system_prompt, temperature=0.7)
                
                json_str = self._extract_json(response)
                if not json_str:
                    raise ValueError("无法从响应中提取JSON")
                
                data = json.loads(json_str)
                outline = self._validate_and_fix_outline(data, total_chapters, chapter_target)
                
                # 检查是否使用了占位符标题
                if self._has_placeholder_titles(outline):
                    if attempt < max_retries - 1:
                        print(f"警告：AI使用了占位符标题，正在重试 ({attempt + 1}/{max_retries})...")
                        continue
                
                return outline
                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("正在重试...")
                    continue
                else:
                    print("所有重试失败，使用默认大纲")
                    return self._create_default_outline(total_chapters, chapter_target, content_analysis)
            except Exception as e:
                print(f"生成大纲失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("正在重试...")
                    continue
                else:
                    print("所有重试失败，使用默认大纲")
                    return self._create_default_outline(total_chapters, chapter_target, content_analysis)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON字符串
        
        尝试多种方法提取有效的JSON：
        1. 直接提取花括号包裹的内容
        2. 尝试修复常见的JSON格式错误
        3. 使用正则表达式提取JSON对象
        """
        import re
        
        # 方法1: 直接提取花括号内容
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            
            # 尝试解析，如果成功直接返回
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                # 尝试修复常见的JSON错误
                fixed = self._fix_common_json_errors(json_str)
                try:
                    json.loads(fixed)
                    return fixed
                except json.JSONDecodeError:
                    pass
        
        # 方法2: 尝试查找所有可能的JSON对象
        # 匹配最外层的花括号对
        json_pattern = r'\{[\s\S]*?\}'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                # 尝试修复
                fixed = self._fix_common_json_errors(match)
                try:
                    json.loads(fixed)
                    return fixed
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _fix_common_json_errors(self, json_str: str) -> str:
        """修复常见的JSON格式错误
        
        Args:
            json_str: 可能有格式错误的JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        import re
        
        fixed = json_str
        
        # 1. 移除多余的逗号（在}或]之前的逗号）
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # 2. 修复缺失的逗号（在""之间或}{之间）
        fixed = re.sub(r'"\s*"', '", "', fixed)
        fixed = re.sub(r'\}\s*\{', '}, {', fixed)
        
        # 3. 修复单引号为双引号
        fixed = fixed.replace("'", '"')
        
        # 4. 修复末尾多余的逗号
        fixed = re.sub(r',(\s*\])', r'\1', fixed)
        fixed = re.sub(r',(\s*\})', r'\1', fixed)
        
        return fixed
    
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
    
    def _has_placeholder_titles(self, outline: BookOutline) -> bool:
        """检查大纲是否使用了占位符标题"""
        placeholder_patterns = ['主题内容', '第1节', '第2节', '第3节', '第1.1小节', '第1.2小节']
        
        for chapter in outline.chapters:
            # 检查章节标题
            if any(pattern in chapter.title for pattern in placeholder_patterns):
                return True
            # 检查子章节标题
            for sub in chapter.subchapters:
                if any(pattern in sub.title for pattern in placeholder_patterns):
                    return True
                # 检查小节标题
                for sec in sub.sections:
                    if any(pattern in sec.title for pattern in placeholder_patterns):
                        return True
        return False
    
    def _create_default_outline(
        self,
        total_chapters: int,
        target_words: int,
        content_analysis: Dict[str, Any] = None
    ) -> BookOutline:
        """创建默认大纲（当AI生成失败时使用）
        
        尝试从content_analysis中提取主题信息生成更有意义的标题
        """
        # 尝试从分析结果中提取主题
        themes = []
        if content_analysis:
            if 'main_theme' in content_analysis:
                themes.append(content_analysis['main_theme'])
            if 'key_points' in content_analysis and isinstance(content_analysis['key_points'], list):
                themes.extend(content_analysis['key_points'][:total_chapters])
        
        # 如果没有提取到足够主题，使用通用主题
        while len(themes) < total_chapters:
            themes.append(f"主题{len(themes) + 1}")
        
        chapters: List[ChapterOutline] = []
        
        for i in range(1, total_chapters + 1):
            chapter_theme = themes[i - 1] if i <= len(themes) else f"主题{i}"
            subchapters: List[SubChapterOutline] = []
            
            for j in range(1, 4):
                sections: List[SectionOutline] = []
                for k in range(1, 3):
                    sections.append(SectionOutline(
                        section_number=f'{i}.{j}.{k}',
                        title=f'{chapter_theme}之{k}',
                        target_words=target_words // 6,
                        summary=f'探讨{chapter_theme}的深层内涵',
                        key_points=['核心要点']
                    ))
                
                subchapters.append(SubChapterOutline(
                    subchapter_number=f'{i}.{j}',
                    title=f'{chapter_theme}层面{j}',
                    target_words=target_words // 3,
                    summary=f'从层面{j}分析{chapter_theme}',
                    sections=sections,
                    key_points=['核心要点']
                ))
            
            chapters.append(ChapterOutline(
                chapter_number=i,
                title=f'{chapter_theme}',
                target_words=target_words,
                summary=f'本章深入探讨{chapter_theme}的核心要义与实践价值。',
                subchapters=subchapters,
                key_points=['核心概念', '实践方法', '应用价值']
            ))
        
        # 尝试从分析结果中提取书名
        title = '重构之作'
        subtitle = '基于原始素材的全新呈现'
        if content_analysis:
            if 'main_theme' in content_analysis:
                main_theme = content_analysis['main_theme']
                title = f'{main_theme}研究'
                subtitle = f'基于{main_theme}的深度解读'
        
        return BookOutline(
            title=title,
            subtitle=subtitle,
            preface_summary='本书是基于原始素材重新整理而成的作品，力求以平实朴素的语言呈现内容精髓。',
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
