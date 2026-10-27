# 办公自动化工具包

把日常重复的表格、文件操作变成一条命令，省下的是时间。

## 快速使用（不用懂命令行）

**双击 `办公自动化工具包.exe`** —— 不需要安装 Python，拿到就能用。

如果 exe 打不开，也可以双击 `启动工具包.bat`（需要电脑已装 Python）。详细步骤见 [使用说明.md](使用说明.md)。

## 打包成 exe

```bash
build_exe.bat        # 单文件版（交付用，约 31 MB）
build_exe.bat fast   # 文件夹版（启动快 10 倍，自己用）
```

构建脚本会自动装 PyInstaller、清理旧产物、排除用不到的包（matplotlib / PIL / scipy / tkinter）、重命名。

两种打包方式对比：

| | 单文件版 `onefile` | 文件夹版 `onedir` |
|---|---|---|
| 体积 | **30.8 MB**（单个文件） | 78 MB（749 个文件） |
| 启动 | 2.13 秒 | **0.20 秒** |
| 交付 | 发一个 exe，双击即用 | 打包成 zip，客户解压后双击 |
| 风险 | 无 | 客户误删文件夹里的文件就跑不起来 |

**为什么单文件版慢**：`--onefile` 每次启动都要把内容解压到系统临时目录，这部分开销跑不掉。

**为什么启动还快了不少**：`menu.py` 改成延迟导入 —— 菜单先显示，pandas 等到选了具体功能才加载。源码模式下菜单启动从约 1 秒降到 **0.11 秒**。

> 打包后的 exe 首次启动约 3-5 秒，因为它要先把自己解压到临时目录（`--onefile` 的代价）。

## 工具列表

| 工具 | 作用 | 用法 |
|---|---|---|
| `tools/batch_rename.py` | 批量重命名文件，可加序号和前缀 | `python tools/batch_rename.py "目录" --ext .png --prefix 图片 --dry-run` |
| `tools/merge_excel.py` | 多张 Excel/CSV 合并成一张，按列名自动对齐 | `python tools/merge_excel.py "数据目录" -o 合并结果.xlsx` |
| `tools/clean_excel.py` | 清洗 Excel：去重、补空、统一日期格式 | `python tools/clean_excel.py "数据.xlsx" -o 结果.xlsx` |
| `tools/reconcile.py` | 两表对账：找出只在A、只在B、字段不符的记录（支持多列比对） | `python tools/reconcile.py a.xlsx b.xlsx --key 订单号 --compare 金额,客户` |
| `tools/pdf_merge.py` | PDF 合并 / 拆分成单页 / 抽取指定页 | `python tools/pdf_merge.py "PDF文件夹" -o 合并结果.pdf` |
| `menu.py` | 菜单式入口，供不熟悉命令行的人使用 | 双击 `启动工具包.bat` |

### batch_rename.py

批量给文件加序号和前缀，支持预览模式。`--dry-run` 只预览不改名，建议先跑一次确认再真正执行。

```bash
python tools/batch_rename.py "目标目录" --ext .png --prefix 图片 --dry-run  # 先预览
python tools/batch_rename.py "目标目录" --ext .png --prefix 图片            # 真正执行
```

### merge_excel.py

把目录下所有 Excel / CSV 合并成一个表，**按列名对齐**（列顺序不同也能合），并自动加一列 `_来源文件` 方便溯源。

```bash
# 基本用法
python tools/merge_excel.py "数据目录" -o 合并结果.xlsx

# 先看看会合成什么样，不写文件
python tools/merge_excel.py "数据目录" --dry-run

# 只保留需要的列
python tools/merge_excel.py "数据目录" -o 结果.xlsx --keep 日期,金额,客户

# 读取每个文件的所有工作表
python tools/merge_excel.py "数据目录" -o 结果.xlsx --all-sheets

# 各表列名不一致但顺序一致时，按位置对齐
python tools/merge_excel.py "数据目录" -o 结果.xlsx --align position
```

**为什么按列名对齐很重要**：真实业务里，A 同事的表是「日期 / 客户 / 金额」，B 同事的表是「日期 / 金额 / 客户」，按位置合并会把金额和客户错位。这个工具按列名匹配，列序乱了也不会错位。

### clean_excel.py

清洗一张脏表：**去重、补空、统一日期格式**，并输出清洗报告（删了几行、填了几个空、改了几个日期）。

```bash
# 先预览，不写文件
python tools/clean_excel.py "脏数据.xlsx" --dry-run

# 按订单号去重并保存
python tools/clean_excel.py "脏数据.xlsx" --dedup-by 订单号 -o 清洗结果.xlsx

# 只对客户、金额两列补空
python tools/clean_excel.py "数据.xlsx" --fill-cols 客户,金额 -o 结果.xlsx

# 手动指定日期列（自动识别失效时用）
python tools/clean_excel.py "数据.xlsx" --date-cols 日期,下单时间 -o 结果.xlsx

# 保留原始行号（默认重排成连续行号）
python tools/clean_excel.py "数据.xlsx" -o 结果.xlsx --keep-index
```

**它能处理的日期格式**：`2026/10/17`、`2026年10月18日`、`2026.10.19`、`10-20-2026`、`2026-10-21`，统一输出成 `2026-10-17`。解析失败的保留原值，不会悄悄变成空。

**两个设计取舍**：
- 默认**重排索引**，因为客户看到行号跳号会以为漏了数据；需要追溯原始行号时加 `--keep-index`。
- 日期解析失败**保留原值**而不是填空，因为空值不会报错，但会让对账直接对不上。

## 环境

```bash
python -m pip install -r requirements.txt
```

## 学习计划

- [12 周技术英语学习计划](docs/english-plan.md) —— 每天 30 分钟，只练"读懂技术文档"，附 150 个高频词和官方文档清单
- [概念速查表](docs/cheatsheet.md) —— 学过的每个知识点对应到「文件:行号」，忘了直接查
- [代码索引](docs/code-index.md) —— 自动生成，列出每个函数在第几行

## 开发进度

- [x] 第 1 周：批量重命名、多表合并
- [x] 第 1 周：pandas 数据清洗
- [x] 第 1 周：两表对账（支持多列比对、差异字段标注）
- [x] 第 2 周：打包成可交付的工具包（菜单 + 双击启动 + 单文件 exe）
- [x] 第 2 周：PDF 合并 / 拆分 / 抽取页面
- [ ] 第 2 周：Word 批量处理
- [ ] 第 3 周：上架试卖，拿到第一笔收入

## 测试数据

`demo_data/` 里有 5 个故意做得很刁钻的文件（列顺序不同、列数不同、多工作表、CSV、脏数据），用来验证各个工具。

```bash
# 测合并
python tools/merge_excel.py demo_data -o demo_output/合并结果.xlsx

# 测清洗（脏数据里有中文日期、重复行、空值）
python tools/clean_excel.py "demo_data/脏数据.xlsx" --dedup-by 订单号 --dry-run
```
