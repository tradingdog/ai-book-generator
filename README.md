# AI辅助书籍生成器

将大文本文件通过豆包AI重新组织，生成结构完整的书籍（Word文档格式）。

## 功能特性

- 📖 **智能分析**：自动分析文本内容，提取主题和关键信息
- 📝 **大纲生成**：AI自动生成书籍结构和章节规划
- ✍️ **内容创作**：逐章生成内容，保持上下文连贯
- 📄 **Word导出**：生成带目录、自序、格式的专业文档
- ⏸️ **断点续传**：支持中断后从上次进度继续生成
- 🎨 **文风定制**：支持平实朴素、文学性、学术性等多种文风

## 环境要求

- Python 3.8+
- 豆包API密钥（Volces/Ark平台）

## 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/tradingdog/ai-book-generator.git
cd ai-book-generator
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置API密钥
编辑 `config.yaml` 文件，填入你的豆包API密钥：
```yaml
doubao:
  api_key: "你的API密钥"
  model: "doubao-seed-1-8-251228"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
```

## 使用方法

### 方式一：交互式运行

```bash
python -m book_generator.main
```

程序会引导你完成以下步骤：
1. 选择输入文件（.md 或 .txt）
2. 验证API配置
3. 分析文件内容
4. 生成书籍大纲
5. 生成各章节内容
6. 导出Word文档

### 方式二：命令行参数

```bash
# 直接指定输入文件
python -m book_generator.main your_file.md

# 指定输出文件
python -m book_generator.main your_file.md -o output.docx

# 从上次中断处继续
python -m book_generator.main --resume
```

## 配置说明

编辑 `config.yaml` 文件可以自定义生成参数：

```yaml
# 生成配置
generation:
  style: "plain"              # 文风：plain(平实朴素)、literary(文学性)、academic(学术性)
  chapter_target_words: 35000 # 每章目标字数
  total_chapters: 15          # 总章节数
  generate_preface: true      # 是否生成自序
  output_filename: "generated_book.docx"  # 默认输出文件名

# 处理配置
processing:
  chunk_size: 4000            # 文本分块大小
  chunk_overlap: 500          # 分块重叠大小
  request_interval: 1         # API请求间隔（秒）
  save_intermediate: true     # 是否保存中间结果
  temp_dir: "./temp"          # 临时文件目录

# 文档格式
document:
  body_font: "宋体"           # 正文字体
  body_size: 12               # 正文字号
  title_font: "黑体"          # 标题字体
  line_spacing: 1.5           # 行距
```

## 项目结构

```
ai-book-generator/
├── book_generator/          # 主程序目录
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── file_reader.py       # 文件读取模块
│   ├── doubao_client.py     # API调用模块
│   ├── outline_generator.py # 大纲生成模块
│   ├── content_generator.py # 内容生成模块
│   ├── doc_exporter.py      # DOC导出模块
│   └── main.py              # 主程序入口
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖列表
└── README.md                # 项目说明
```

## 处理流程

1. **文件读取**：读取.md或.txt文件，支持大文件分块处理
2. **内容分析**：使用AI分析文本主题、结构和关键信息
3. **大纲生成**：根据分析结果生成书籍结构和章节规划
4. **内容生成**：逐章生成内容，保持上下文连贯性
5. **文档导出**：生成带目录、自序、格式的Word文档

## 注意事项

- API调用需要消耗Token，请确保账户余额充足
- 大文本处理可能需要较长时间，请耐心等待
- 生成过程中会自动保存进度，支持中断后继续
- 建议在生成过程中保持网络连接稳定

## 常见问题

**Q: 如何处理50万字以上的大文件？**  
A: 程序会自动将大文件分块处理，无需特殊配置。

**Q: 生成过程中断怎么办？**  
A: 重新运行程序，选择从上次中断处继续即可。

**Q: 可以修改已生成的大纲吗？**  
A: 可以编辑 `temp/book_outline.json` 文件修改大纲后重新生成。

**Q: 如何调整生成内容的字数？**  
A: 修改 `config.yaml` 中的 `chapter_target_words` 参数。

## 版本历史

### v1.0.0 (2026-03-26)
- 初始版本发布
- 支持文件读取、AI分析、大纲生成、内容生成、DOC导出
- 支持断点续传功能

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交Issue或Pull Request。
