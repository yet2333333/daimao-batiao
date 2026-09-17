# 智能桌面化工伴侣猫 · Smart Chem Cat

> 一只住在桌面上的白色小猫，右键菜单里塞满了化工工程师真正会用到的工具。

---

## 这是什么

一个用 Python + Tkinter 写的 **Windows 桌面效率工具**。表面是桌面宠物，实际是六个工程小工具的集合体：

化工设计要反复查手册、算管径、填周报、翻 SOP——这些事单件都很小，但一天下来能啃掉两小时。
于是我把它们全部塞进一只猫的右键菜单，点一下就出来，用完就收。

**作者是化工工艺工程师，不是专职程序员。这个项目解决的是他自己每天遇到的真实问题。**

---

## 功能

| 模块 | 说明 |
|------|------|
| 🐱 **桌面宠物** | 无边框透明窗口，9 种心情表情，可拖拽并带物理弹跳，闲置 15 秒自动睡觉 / 散步 / 撒娇 |
| 🔍 **化工知识库检索** | 本地 Markdown 知识库全文检索，支持中文提问自动映射英文关键词 |
| 🤖 **AI 对话** | 接入任意 OpenAI 兼容接口，可问专业问题、做计算、查资料 |
| 📐 **管线流计算** | 管径 / 流速 / 压降的工程计算，带参数校验 |
| ✅ **待办 + 日程** | 编号分组、颜色标记、风险提示、周视图 |
| 📊 **周报导出** | 一键把待办和进度导出成 Excel，套用公司周报模板 |
| 📁 **SOP 查看** | 直接读取本地 SOP 文档目录，不用再翻资源管理器 |

---

## 环境要求

- Windows 10 / 11
- **Python 3.10+**，请使用 [python.org 官方安装包](https://www.python.org/downloads/)，安装时勾选 `Add python.exe to PATH`
  - ⚠️ 不建议使用 Microsoft Store 版 Python
- 界面基于 tkinter，官方安装包默认自带，无需单独安装

## 快速开始

```bash
git clone https://github.com/yet2333333/smart-chem-cat.git
cd smart-chem-cat

pip install -r requirements.txt

cp .env.example .env     # 然后编辑 .env 填入自己的配置
python main.py
```

> 只依赖 `openpyxl` 一个第三方库，其余全部使用 Python 标准库。
> 需要 Python 3.8+（Windows）。

---

## 配置

所有本机相关的配置都在 `.env` 里，**不填也能跑**，只是对应功能会关闭。

| 变量 | 作用 | 留空时 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | AI 对话密钥 | AI 对话不可用 |
| `DEEPSEEK_API_BASE` | 接口地址，默认 DeepSeek 官方 | 同上 |
| `MODEL_NAME` | 模型名，默认 `deepseek-chat` | 同上 |
| `KB_ROOT` | 知识库 Markdown 根目录 | 关闭知识库检索 |
| `RAG_DB` | SQLite FTS5 索引文件 | 关闭知识库检索 |
| `USER_DISPLAY_NAME` | 周报署名 | 显示「我」 |
| `COMPANY_NAME` | 周报表头公司名 | 单元格留空 |
| `REPORT_DIR` | 周报输出目录 | 桌面 / `<署名>周报` |
| `SOP_DIR` | SOP 文档目录 | 自动查找 程序目录/sop 等 |
| `DATA_DIR` | 待办 / 日程 / 统计存放目录 | 程序目录下的 `data/` |

> **周报导出**以 `data/每周进度反馈模板.xlsx` 为基底文件填充。
> 仓库自带一份**通用空白模板**，你可以直接换成自己的模板——
> 只要保持「第 4 行表头、第 5 行起写数据、共 12 列」的结构就不会错行。

---

## 技术要点

几个值得单独说的地方：

**1. 中英双语检索映射**

最大的坑：知识库里 Perry's Handbook、FRI 报告这些权威资料全是英文，但工程师习惯用中文提问。
直接搜「分布器」什么都查不到。

解决办法是建一张同义词表，中文提问时自动展开成英文关键词一起检索：

```python
BILINGUAL_MAP = {
    '分布器': 'distributor', '分布管': 'distributor pipe',
    '糠醛': 'furfural',      '糠醇': 'furfuryl alcohol',
    '换热器': 'heat exchanger', ...
}
```

**2. SQLite FTS5 全文检索**

用 FTS5 建倒排索引，BM25 算法排序，再对精确匹配加权。几十万段落的查询在毫秒级完成，不依赖任何外部服务。

**3. Tkinter 无边框透明窗口**

`overrideredirect` 去掉标题栏 + `transparentcolor` 抠掉背景色，配合 `ctypes` 设置窗口分层，实现猫能浮在任何窗口之上。拖拽用简单的速度衰减模拟物理弹跳。

**4. 零外部服务依赖**

检索走本地 SQLite，界面走标准库 Tkinter，整个应用离线可用。

---

## 项目结构

```
smart-chem-cat/
├── main.py                  # 入口：宠物窗口 + 知识库检索 + AI 对话
├── modules/
│   ├── todos.py             # 待办数据层
│   ├── todo_dialog.py       # 待办界面 + 周报 Excel 导出
│   ├── scheduler.py         # 日程
│   ├── pipe_calc.py         # 管线流计算
│   ├── sop_viewer.py        # SOP 文档查看
│   ├── stats.py             # 使用统计
│   └── notifilter.py        # 通知过滤
├── assets/                  # 猫的图标（ico / png）
├── data/                    # 运行时数据；个人数据不入库，仅保留周报模板
│   └── 每周进度反馈模板.xlsx
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## 打包成 exe

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=assets/cat_icon.ico main.py
```

产物在 `dist/`。若 slim 版 Python 缺少 tkinter，用环境变量 `DAIMAO_TKINTER_PATH` 指定 tkinter 目录。

---

## 隐私说明

- 所有密钥走 `.env`，仓库中不含任何密钥
- `.gitignore` 已排除 `data/`，个人待办、日程、公司模板不会入库
- AI 对话默认直连你自己在 `.env` 里配置的接口，请求不经过任何第三方中转

---

## License

[MIT](LICENSE) — 随便用，改坏了别找我 😼
