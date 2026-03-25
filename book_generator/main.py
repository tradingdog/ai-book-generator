"""
AI辅助书籍生成器 - 主程序入口

命令行交互界面，提供完整的文本到书籍的生成流程。
"""

import os
import sys
import json
import time
import argparse
from typing import Optional

# 处理相对导入，支持直接运行和模块导入
if __package__ is None:
    # 直接运行文件时，将上级目录加入路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from book_generator.config import get_config, reload_config
    from book_generator.file_reader import FileReader, get_file_stats
    from book_generator.doubao_client import DoubaoClient
    from book_generator.outline_generator import OutlineGenerator, BookOutline
    from book_generator.content_generator import ContentGenerator, GenerationProgress
    from book_generator.doc_exporter import DocExporter
    from book_generator.full_text_analyzer import FullTextAnalyzer
    from book_generator.logger import get_logger, BookGeneratorLogger
else:
    # 作为模块导入时，使用相对导入
    from .config import get_config, reload_config
    from .file_reader import FileReader, get_file_stats
    from .doubao_client import DoubaoClient
    from .outline_generator import OutlineGenerator, BookOutline
    from .content_generator import ContentGenerator, GenerationProgress
    from .doc_exporter import DocExporter
    from .full_text_analyzer import FullTextAnalyzer
    from .logger import get_logger, BookGeneratorLogger


class BookGeneratorApp:
    """书籍生成器应用程序
    
    提供完整的命令行交互界面，引导用户完成从文本到书籍的生成过程。
    
    Attributes:
        config: 配置对象
        client: API客户端
        outline_generator: 大纲生成器
        content_generator: 内容生成器
    """
    
    def __init__(self) -> None:
        """初始化应用程序"""
        self.config = get_config()
        self.logger: BookGeneratorLogger = get_logger()
        self.client: Optional[DoubaoClient] = None
        self.outline_generator: Optional[OutlineGenerator] = None
        self.content_generator: Optional[ContentGenerator] = None
        self.file_reader: Optional[FileReader] = None
        self.outline: Optional[BookOutline] = None
        self.original_content: str = ""
        self.analysis_result: Optional[dict] = None
        self.source_filename: str = "unknown"
        
    def run(self) -> None:
        """运行应用程序"""
        self._print_banner()
        self.logger.info(f"日志文件: {self.logger.get_log_file_path()}")
        
        try:
            # 步骤1: 选择输入文件
            self.logger.step(1, 6, "选择输入文件")
            self._step_select_file()
            
            # 步骤2: 验证API配置
            self.logger.step(2, 6, "验证API配置")
            self._step_verify_api()
            
            # 步骤3: 分析文件
            self.logger.step(3, 6, "分析文件内容")
            self._step_analyze_file()
            
            # 步骤4: 生成大纲
            self.logger.step(4, 6, "生成书籍大纲")
            self._step_generate_outline()
            
            # 步骤5: 生成内容
            self.logger.step(5, 6, "生成章节内容")
            self._step_generate_content()
            
            # 步骤6: 导出文档
            self.logger.step(6, 6, "导出Word文档")
            self._step_export_document()
            
            self.logger.section("书籍生成完成！")
            self.logger.info(f"输出文件: {self.config.get_output_filename()}")
            
        except KeyboardInterrupt:
            self.logger.warning("用户中断操作")
            self._handle_interrupt()
        except Exception as e:
            self.logger.error(f"程序异常: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            sys.exit(1)
    
    def _print_banner(self) -> None:
        """打印程序横幅"""
        print("=" * 50)
        print("     AI辅助书籍生成器 v1.2.7")
        print("=" * 50)
        print("将大文本文件转换为结构完整的书籍")
        print("-" * 50)
    
    def _step_select_file(self) -> None:
        """步骤1: 选择输入文件"""
        print("\n【步骤1/6】选择输入文件")
        print("-" * 30)
        
        # 如果命令行参数提供了文件路径
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            file_path = sys.argv[1]
            print(f"使用命令行参数指定的文件: {file_path}")
        else:
            # 交互式输入
            while True:
                file_path = input("请输入文本文件路径(.md或.txt): ").strip().strip('"')
                
                if not file_path:
                    print("文件路径不能为空，请重新输入")
                    continue
                
                if not os.path.exists(file_path):
                    print(f"文件不存在: {file_path}")
                    continue
                
                break
        
        # 创建文件读取器
        try:
            self.file_reader = FileReader(file_path)
            # 保存源文件名
            self.source_filename = os.path.basename(file_path)
            stats = self.file_reader.get_statistics()
            
            self.logger.info("文件信息:")
            self.logger.info(f"  路径: {stats['file_path']}")
            self.logger.info(f"  大小: {stats['file_size_kb']} KB")
            self.logger.info(f"  编码: {stats['encoding']}")
            self.logger.info(f"  字符数: {stats['total_chars']:,}")
            self.logger.info(f"  行数: {stats['line_count']:,}")
            self.logger.info(f"  估算字数: {stats['estimated_words']:,}")
            self.logger.info(f"  预估阅读时间: {self.file_reader.estimate_reading_time():.0f} 分钟")
            
            # 读取完整内容
            self.logger.info("正在读取文件内容...")
            self.original_content = self.file_reader.read_all()
            self.logger.info(f"读取完成，共 {len(self.original_content):,} 字符")
            
        except Exception as e:
            raise Exception(f"读取文件失败: {e}")
    
    def _step_verify_api(self) -> None:
        """步骤2: 验证API配置"""
        print("\n【步骤2/6】验证API配置")
        print("-" * 30)
        
        try:
            api_key = self.config.get_doubao_api_key()
            # 隐藏部分API密钥显示
            masked_key = api_key[:8] + "..." + api_key[-4:]
            self.logger.info(f"API密钥: {masked_key}")
            self.logger.info(f"模型: {self.config.get_doubao_model()}")
            self.logger.info(f"基础URL: {self.config.get_doubao_base_url()}")
            
            # 测试API连接
            self.logger.info("正在测试API连接...")
            self.client = DoubaoClient()
            
            # 发送简单测试请求
            test_response = self.client.chat("你好", max_tokens=10)
            self.logger.info("API连接测试成功！")
            
        except ValueError as e:
            self.logger.error(f"API配置错误: {e}")
            print("请检查config.yaml文件中的API配置")
            raise
        except Exception as e:
            print(f"API连接测试失败: {e}")
            print("请检查网络连接和API配置")
            raise
    
    def _step_analyze_file(self) -> None:
        """步骤3: 分析文件内容"""
        self.logger.section("【步骤3/6】全文阅读与分析")
        
        if not self.client:
            raise Exception("API客户端未初始化")
        
        # 使用全文分析器进行完整阅读
        self.logger.info(f"原始文本总长度: {len(self.original_content):,} 字符")
        self.logger.info("重要：现在将分批投喂全文给AI，确保其完整理解原始素材")
        self.logger.info("这可能需要一些时间，请耐心等待...")
        
        try:
            # 创建全文分析器，传入源文件名
            analyzer = FullTextAnalyzer(chunk_size=8000, source_filename=self.source_filename)
            
            # 执行全文分析
            self.analysis_result = analyzer.analyze_full_text(self.original_content)
            
            self.logger.section("全文分析完成！")
            
            self.logger.info("分析结果:")
            if "main_theme" in self.analysis_result:
                self.logger.info(f"  主要主题: {self.analysis_result['main_theme']}")
            if "summary" in self.analysis_result:
                summary = self.analysis_result['summary']
                if len(summary) > 150:
                    summary = summary[:150] + "..."
                self.logger.info(f"  内容摘要: {summary}")
            if "key_points" in self.analysis_result and isinstance(self.analysis_result['key_points'], list):
                self.logger.info("  关键要点:")
                for point in self.analysis_result['key_points'][:5]:
                    self.logger.info(f"    - {point}")
            if "characters" in self.analysis_result:
                self.logger.info(f"  涉及人物/群体: {', '.join(self.analysis_result['characters'][:3])}")
            
            self.logger.info("AI已完成全文阅读，现在可以基于完整理解生成书籍")
            
        except Exception as e:
            self.logger.error(f"全文分析失败: {e}")
            self.logger.info("将使用简化分析继续...")
            # 降级处理：使用简单的片段分析
            sample_content = self.original_content[:8000]
            self.analysis_result = self.client.analyze_content(sample_content, "summary")
    
    def _step_generate_outline(self) -> None:
        """步骤4: 生成书籍大纲"""
        self.logger.section("【步骤4/6】生成书籍大纲")
        
        # 显示配置
        total_chapters = self.config.get_total_chapters()
        chapter_words = self.config.get_chapter_target_words()
        total_words = len(self.original_content)
        
        self.logger.info("生成配置:")
        self.logger.info(f"  章节数: {total_chapters}章")
        self.logger.info(f"  每章字数: 约{chapter_words:,}字")
        self.logger.info(f"  原文总字数: {total_words:,}字")
        
        # 确认或修改（保持终端交互）
        print("\n是否使用以上配置生成大纲？")
        print("  1. 使用默认配置")
        print("  2. 自定义配置")
        
        choice = input("请选择 (1/2): ").strip()
        self.logger.info(f"用户选择: {choice}")
        
        if choice == "2":
            try:
                chapters_input = input(f"章节数 (默认{total_chapters}): ").strip()
                if chapters_input:
                    total_chapters = int(chapters_input)
                    self.logger.info(f"用户设置章节数: {total_chapters}")
                
                words_input = input(f"每章字数 (默认{chapter_words}): ").strip()
                if words_input:
                    chapter_words = int(words_input)
                    self.logger.info(f"用户设置每章字数: {chapter_words}")
            except ValueError:
                self.logger.warning("输入无效，使用默认配置")
        
        self.logger.info("正在生成大纲...")
        self.logger.info(f"开始生成大纲: {total_chapters}章, 每章约{chapter_words}字")
        self.logger.info(f"预计总字数: {total_chapters * chapter_words}")
        self.logger.info("正在调用AI生成三级目录结构(章-节-小节)，这可能需要3-5分钟...")
        
        try:
            self.outline_generator = OutlineGenerator()
            
            # 计算目标总字数
            target_total = total_chapters * chapter_words
            
            self.logger.info("发送请求到豆包API...")
            self.outline = self.outline_generator.generate_outline(
                content_analysis=self.analysis_result,
                total_words=target_total,
                sample_content=self.original_content[:5000],
                total_chapters=total_chapters,
                chapter_target_words=chapter_words
            )
            
            self.logger.info("大纲生成完成！")
            self.logger.info(f"书名: {self.outline.title}")
            print(f"  书名: {self.outline.title}")
            if self.outline.subtitle:
                self.logger.info(f"副标题: {self.outline.subtitle}")
                print(f"  副标题: {self.outline.subtitle}")
            self.logger.info(f"章节数: {len(self.outline.chapters)}章")
            print(f"  章节数: {len(self.outline.chapters)}章")
            self.logger.info("详细目录结构:")
            for ch in self.outline.chapters:
                self.logger.info(f"第{ch.chapter_number}章: {ch.title}")
                for sub in ch.subchapters:
                    self.logger.info(f"  {sub.subchapter_number} {sub.title}")
                    for sec in sub.sections:
                        self.logger.info(f"    {sec.section_number} {sec.title}")
            
            # 保存大纲
            temp_dir = self.config.get_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)
            outline_path = os.path.join(temp_dir, "book_outline.json")
            self.outline_generator.save_outline(self.outline, outline_path)
            self.logger.info(f"大纲已保存到: {outline_path}")
            
        except Exception as e:
            raise Exception(f"生成大纲失败: {e}")
    
    def _step_generate_content(self) -> None:
        """步骤5: 生成书籍内容"""
        self.logger.section("【步骤5/6】生成书籍内容")
        
        if not self.outline:
            raise Exception("大纲未生成")
        
        # 检查是否有未完成的进度
        temp_dir = self.config.get_temp_dir()
        progress_file = os.path.join(temp_dir, "generation_progress.json")
        
        resume = False
        if os.path.exists(progress_file):
            self.logger.info("检测到未完成的生成任务")
            choice = input("是否从上次中断处继续? (y/n): ").strip().lower()
            resume = choice in ('y', 'yes', '是')
            self.logger.info(f"用户选择: {'继续' if resume else '重新开始'}")
        
        self.logger.info(f"开始生成内容，共 {len(self.outline.chapters)} 章需要生成")
        self.logger.info("此过程可能需要较长时间，请耐心等待...")
        
        try:
            # 获取全文理解摘要
            full_understanding = ""
            if hasattr(self, 'analysis_result') and self.analysis_result:
                if 'summary' in self.analysis_result:
                    full_understanding = self.analysis_result['summary']
                # 如果有更详细的理解，也加入
                if 'raw_understanding' in self.analysis_result:
                    full_understanding = self.analysis_result['raw_understanding']
            
            self.logger.info(f"全文理解摘要（前200字）: {full_understanding[:200]}...")
            
            self.content_generator = ContentGenerator(
                original_content=self.original_content,
                full_understanding=full_understanding
            )
            
            # 生成内容并显示进度
            final_progress = None
            for progress in self.content_generator.generate_book(self.outline, resume):
                self._display_progress(progress)
                final_progress = progress
            
            if final_progress and final_progress.status == "completed":
                self.logger.info("内容生成完成！")
            elif final_progress and final_progress.status == "error":
                raise Exception(f"生成失败: {final_progress.error_message}")
                
        except Exception as e:
            raise Exception(f"生成内容失败: {e}")
    
    def _display_progress(self, progress: GenerationProgress) -> None:
        """显示生成进度
        
        Args:
            progress: 进度对象
        """
        percentage = progress.progress_percentage
        bar_length = 30
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        if progress.current_chapter == 0:
            chapter_name = "自序"
        else:
            chapter_name = f"第{progress.current_chapter}章"
        
        print(f"\r进度: [{bar}] {percentage:.1f}% | {progress.completed_chapters}/{progress.total_chapters} | 正在生成: {chapter_name}", end="", flush=True)
    
    def _step_export_document(self) -> None:
        """步骤6: 导出文档"""
        self.logger.section("【步骤6/6】导出Word文档")
        
        if not self.content_generator or not self.outline:
            raise Exception("内容未生成")
        
        # 获取输出路径
        default_output = self.config.get_output_filename()
        output_path = input(f"请输入输出文件路径 (默认: {default_output}): ").strip().strip('"')
        
        if not output_path:
            output_path = default_output
        
        # 确保是.docx扩展名
        if not output_path.endswith('.docx'):
            output_path += '.docx'
        
        self.logger.info(f"正在导出文档到: {output_path}")
        
        try:
            exporter = DocExporter()
            exporter.create_document(
                self.outline,
                self.content_generator.progress.generated_content
            )
            saved_path = exporter.save(output_path)
            
            self.logger.info(f"文档已保存到: {saved_path}")
            
            # 显示统计信息
            total_chars = sum(len(content) for content in self.content_generator.progress.generated_content.values())
            self.logger.info(f"文档总字符数: {total_chars:,}")
            
        except Exception as e:
            raise Exception(f"导出文档失败: {e}")
    
    def _handle_interrupt(self) -> None:
        """处理用户中断"""
        self.logger.info("正在保存当前进度...")
        # 进度会在生成过程中自动保存
        self.logger.info("进度已保存，下次运行时可选择继续")
        sys.exit(0)


def main():
    """程序入口点"""
    # 支持命令行参数
    parser = argparse.ArgumentParser(description='AI辅助书籍生成器')
    parser.add_argument('input_file', nargs='?', help='输入文本文件路径')
    parser.add_argument('-c', '--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--resume', action='store_true', help='从上次中断处继续')
    
    args = parser.parse_args()
    
    # 重新加载配置（如果指定了配置文件）
    if args.config != 'config.yaml':
        reload_config(args.config)
    
    # 运行应用程序
    app = BookGeneratorApp()
    app.run()


if __name__ == "__main__":
    main()
