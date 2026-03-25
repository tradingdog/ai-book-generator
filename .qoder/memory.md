# AI辅助书籍生成项目 - 项目记忆

## 项目概述
- **项目名称**: AI辅助书籍生成器
- **版本**: v1.0.0
- **创建时间**: 2026-03-26
- **目标**: 将大文本文件（md/txt）通过豆包AI重新组织，生成结构完整的新书籍（DOC格式）

## 核心需求
1. 支持读取md和txt文件
2. 处理50万字级别的大文本
3. 持续性调用豆包API进行内容重组
4. 生成有目录、自序、详细章节的doc文档
5. 文风要求：平实朴素
6. 无语言逻辑错误
7. 最终字数与原文相近

## 技术栈
- **语言**: Python 3.8+
- **API**: 豆包 (Volces/Ark)
- **文档生成**: python-docx
- **配置格式**: YAML

## API配置信息
```yaml
doubao:
  api_key: "7fb7e1ad-ff62-4d30-b19c-82d7b26b3439"
  model: "doubao-seed-1-8-251228"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
```

## 项目结构
```
xiaoshuo/
├── .qoder/
│   └── memory.md          # 项目记忆文件
├── book_generator/        # 主程序目录
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── file_reader.py     # 文件读取模块
│   ├── doubao_client.py   # API调用模块
│   ├── analyzer.py        # 文本分析模块
│   ├── outline_generator.py # 大纲生成模块
│   ├── content_generator.py # 内容生成模块
│   ├── doc_exporter.py    # DOC导出模块
│   └── main.py            # 主程序入口
├── config.yaml            # 用户配置文件
├── requirements.txt       # 依赖列表
└── README.md              # 项目说明
```

## 处理流程
1. 文件读取 → 2. 内容分析 → 3. 大纲生成 → 4. 逐章生成 → 5. 审核优化 → 6. DOC输出

## 版本历史

### v1.0.0 (2026-03-26)
- 初始版本
- 实现基础功能框架
- 支持文件读取、API调用、DOC生成
- 所有基础测试通过

## 待办事项
- [x] 创建项目基础架构
- [x] 实现配置文件管理
- [x] 实现文件读取模块（支持大文件）
- [x] 实现豆包API客户端
- [x] 实现大纲生成模块
- [x] 实现内容生成模块
- [x] 实现DOC导出模块
- [x] 实现主程序交互界面
- [x] 编写测试脚本并验证
- [x] 创建GitHub仓库并推送代码
- [ ] 优化API调用效率
- [ ] 添加更多文风选项
- [ ] 支持PDF导出
- [ ] 添加图形界面

## 注意事项
- API调用需要控制频率，避免触发限制
- 大文本需要分块处理
- 每次生成后需要保存进度，支持断点续传
