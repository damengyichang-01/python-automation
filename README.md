# 办公自动化工具包

把日常重复的表格、文件操作变成一条命令，省下的是时间。

## 工具列表

| 工具 | 作用 | 用法 |
|---|---|---|
| `tools/batch_rename.py` | 批量重命名文件，可加序号和前缀 | `python tools/batch_rename.py "目标目录" --ext .png --prefix 图片 --dry-run` |

`--dry-run` 只预览不改名，建议先跑一次确认再真正执行。

## 环境

    python -m pip install -r requirements.txt

## 目标

- 第 1 周：批量重命名、Excel 合并、pandas 清洗
- 第 2 周：Word/PDF 处理、对账工具
- 第 3 周：打包成客户能直接用的工具包
