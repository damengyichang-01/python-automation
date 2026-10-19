# 办公自动化工具包

把日常重复的表格、文件操作变成一条命令，省下的是时间。

## 工具列表

| 工具 | 作用 | 用法 |
|---|---|---|
| `tools/batch_rename.py` | 批量重命名文件，可加序号和前缀 | `python tools/batch_rename.py "目录" --ext .png --prefix 图片 --dry-run` |
| `tools/merge_excel.py` | 多张 Excel/CSV 合并成一张，按列名自动对齐 | `python tools/merge_excel.py "数据目录" -o 合并结果.xlsx` |
| `tools/clean_excel.py` | 清洗 Excel：去重、补空、统一日期格式 | `python tools/clean_excel.py "数据.xlsx" -o 结果.xlsx` |

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

## 开发进度

- [x] 第 1 周：批量重命名、多表合并
- [x] 第 1 周：pandas 数据清洗
- [ ] 第 1 周：两表对账
- [ ] 第 2 周：Word/PDF 处理
- [ ] 第 3 周：打包成客户能直接用的工具包

## 测试数据

`demo_data/` 里有 5 个故意做得很刁钻的文件（列顺序不同、列数不同、多工作表、CSV、脏数据），用来验证各个工具。

```bash
# 测合并
python tools/merge_excel.py demo_data -o demo_output/合并结果.xlsx

# 测清洗（脏数据里有中文日期、重复行、空值）
python tools/clean_excel.py "demo_data/脏数据.xlsx" --dedup-by 订单号 --dry-run
```
