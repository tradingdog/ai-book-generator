#!/usr/bin/env python3
"""
基础功能测试脚本

测试程序的核心功能是否正常工作。
"""

import os
import sys

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    try:
        from book_generator import __version__
        from book_generator.config import get_config
        from book_generator.file_reader import FileReader
        from book_generator.doubao_client import DoubaoClient
        from book_generator.outline_generator import OutlineGenerator
        from book_generator.content_generator import ContentGenerator
        from book_generator.doc_exporter import DocExporter
        print(f"✓ 所有模块导入成功，版本: {__version__}")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_config():
    """测试配置加载"""
    print("\n测试配置加载...")
    try:
        from book_generator.config import get_config
        config = get_config()
        
        api_key = config.get_doubao_api_key()
        model = config.get_doubao_model()
        
        # 验证API密钥格式（应该是UUID格式）
        if len(api_key) > 20 and '-' in api_key:
            print(f"✓ API配置正常，模型: {model}")
            return True
        else:
            print(f"✗ API密钥格式异常")
            return False
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False

def test_file_reader():
    """测试文件读取"""
    print("\n测试文件读取...")
    try:
        from book_generator.file_reader import FileReader
        
        # 创建一个测试文件
        test_content = "这是一段测试文本。\n用于测试文件读取功能。\n包含多行内容。"
        test_file = "test_input.txt"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 测试读取
        reader = FileReader(test_file)
        content = reader.read_all()
        stats = reader.get_statistics()
        
        # 清理测试文件
        os.remove(test_file)
        
        if content == test_content:
            print(f"✓ 文件读取正常，字符数: {stats['total_chars']}")
            return True
        else:
            print(f"✗ 文件内容不匹配")
            return False
    except Exception as e:
        print(f"✗ 文件读取失败: {e}")
        return False

def test_doc_export():
    """测试DOC导出"""
    print("\n测试DOC导出...")
    try:
        from book_generator.doc_exporter import DocExporter
        from book_generator.outline_generator import BookOutline, ChapterOutline
        
        # 创建测试大纲
        chapters = [
            ChapterOutline(
                chapter_number=1,
                title="测试章节",
                subsections=["第一节", "第二节"],
                target_words=1000,
                summary="测试章节概要",
                key_points=["要点1"]
            )
        ]
        
        outline = BookOutline(
            title="测试书籍",
            subtitle="副标题",
            preface_summary="自序概要",
            chapters=chapters,
            total_words=1000,
            style="plain"
        )
        
        # 创建测试内容
        content_dict = {
            0: "这是自序内容。",
            1: "第1章 测试章节\n\n这是第一章的内容。\n\n本章小结：总结内容。"
        }
        
        # 导出文档
        exporter = DocExporter()
        exporter.create_document(outline, content_dict)
        
        test_output = "test_output.docx"
        exporter.save(test_output)
        
        # 验证文件存在
        if os.path.exists(test_output):
            file_size = os.path.getsize(test_output)
            os.remove(test_output)
            print(f"✓ DOC导出正常，文件大小: {file_size} 字节")
            return True
        else:
            print(f"✗ 导出文件不存在")
            return False
    except Exception as e:
        print(f"✗ DOC导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_connection():
    """测试API连接"""
    print("\n测试API连接...")
    try:
        from book_generator.doubao_client import DoubaoClient
        
        client = DoubaoClient()
        
        # 发送简单测试请求
        print("  正在发送测试请求...")
        response = client.chat("你好，请回复'测试成功'", max_tokens=20)
        
        if response and len(response) > 0:
            print(f"✓ API连接正常，响应: {response[:30]}...")
            return True
        else:
            print(f"✗ API响应为空")
            return False
    except Exception as e:
        print(f"✗ API连接失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("AI书籍生成器 - 基础功能测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config),
        ("文件读取", test_file_reader),
        ("DOC导出", test_doc_export),
        ("API连接", test_api_connection),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name}测试异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！程序可以正常运行。")
        return 0
    else:
        print("\n⚠️ 部分测试未通过，请检查配置或环境。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
