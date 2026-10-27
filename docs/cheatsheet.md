# 概念速查表

> **不用背。** 忘了就打开这份表，按「文件:行号」跳过去看当时的写法。
> 记忆不可靠，索引可靠。

## 怎么跳过去看

**VS Code 里**：

| 快捷键 | 作用 |
|---|---|
| `Ctrl + P` | 输入 `menu.py:26` 直接跳到第 26 行 |
| `Ctrl + G` | 在当前文件跳到指定行 |
| `Ctrl + Shift + F` | 全项目搜索关键词 |
| `F12` | 跳到函数定义处 |

**命令行里**：

```bash
python tools/index_code.py     # 重新生成 docs/code-index.md，查函数在第几行
```

---

## 一、排序

| 我要做什么 | 去哪看 | 关键写法 |
|---|---|---|
| 按文件名 / 修改时间排序 | `tools/batch_rename.py:13` | `key = lambda f: f.stat().st_mtime` |
| 自然排序（1,2,10 而不是 1,10,2） | `tools/pdf_merge.py:24` | `natural_key()` 函数 |
| 正则里保留分隔符 | `tools/pdf_merge.py:34` | `re.split(r"(\d+)", name)` —— 括号不能省 |

**判断标准**：`sorted()` 不报错但顺序不对，一定是 `key` 写错了。

---

## 二、pandas

| 我要做什么 | 去哪看 | 关键写法 |
|---|---|---|
| 找出「只在 A 表不在 B 表」 | `tools/reconcile.py:27` | `df_a[~df_a[key].isin(keys_b)]` |
| 两表按列拼接，右边加后缀 | `tools/reconcile.py:30` | `merge(on=key, suffixes=("_系统","_手工"))` |
| 比较两列，空值算相同 | `tools/reconcile.py:14` | `~(sa == sb) \| (sa.isna() & sb.isna())` |
| 标注哪些字段不一样 | `tools/reconcile.py:51` | 新增「差异字段」列 |
| 去重且不出现警告 | `tools/clean_excel.py:77` | `drop_duplicates(...).copy()` |
| 补空值 | `tools/clean_excel.py:54` | `df[c].fillna("未填")` |
| 重排行号 | `tools/clean_excel.py:141` | `reset_index(drop=True)` |
| 统一各种日期格式 | `tools/clean_excel.py:26` | `to_date_series()` |
| 只读表头拿列名（快） | `menu.py:158` | `pd.read_excel(path, nrows=0)` |

---

## 三、程序结构

| 我要做什么 | 去哪看 | 说明 |
|---|---|---|
| 写一个命令行工具 | `tools/reconcile.py:57` | `argparse.ArgumentParser()` |
| 启动快（延迟导入） | `menu.py:26` | `load_tool()` —— 菜单先出，pandas 后用 |
| 统一处理错误和退出 | `menu.py:122` | `except SystemExit` / `FileNotFoundError` / `KeyError` |
| 输入流结束不崩 | `menu.py:76` | `except EOFError` 返回 None |
| 把长列表分行显示 | `menu.py:107` | `print_columns()` |

---

## 四、打包成 exe

| 我要做什么 | 去哪看 |
|---|---|
| 打单文件版 / 文件夹版 | `build_exe.bat` |
| 排除用不到的包（省 11 MB） | `build_exe.bat` 里的 `--exclude-module` |
| 查找某函数在第几行 | `python tools/index_code.py` |

**关键数字**：单文件 31 MB / 启动 2 秒；文件夹版 78 MB / 启动 0.2 秒。

---

## 五、踩过的坑（最值钱的一节）

| 坑 | 报错长什么样 | 解法 | 出处 |
|---|---|---|---|
| 变量先用后定义 | `UnboundLocalError: ... referenced before assignment` | 先赋值再用 | `reconcile.py` 早期 |
| `True` 写成 `true` | 也是 `UnboundLocalError`（误导） | Python 的 True/False 必须大写 | 改 `reset_index` 时 |
| 往切片里写值 | `SettingWithCopyWarning` | 加 `.copy()` | `clean_excel.py:77` |
| 输出文件被提交进仓库 | 仓库越来越大 | 加进 `.gitignore` | `.gitignore` |
| 文件名排序错 | 顺序变成 1, 10, 2 | `natural_key` | `pdf_merge.py:24` |
| 文件带 BOM 解析失败 | `invalid character in identifier` | 读文件用 `utf-8-sig` | `index_code.py` |
| 提交消息里有中文引号 | `error: pathspec ... did not match` | 命令行里避免中文标点 | 提交时 |
| Python 3.8 装不了新库 | `TypeError: 'usedforsecurity' is an invalid keyword argument` | 降版本，如 `reportlab<4` | 装 PDF 库时 |
| 打包后找不到模块 | `ModuleNotFoundError: No module named 'batch_rename'` | 把目录变成包（加 `__init__.py`） | 第一次打 exe |
| 改了路径却没生效 | 相对路径找不到文件 | 先 `cd` 到项目目录 | 跑 reconcile 时 |

---

## 六、每次卡住时的固定流程

1. **读报错的第一行和最后一行** —— 中间是调用链，不用全看
2. **看报错里的行号** —— 直接 `Ctrl+P` 跳过去
3. **猜一下再改一个变量试** —— 比直接问快
4. **还不行就把报错原文贴给 AI**，要求它解释原因，不要直接给答案
5. **修完记一行到这个表末尾** —— 下次就不用再查一遍

---

## 七、这条最重要

> **不需要记住怎么写，只需要知道去哪查。**
>
> 这份表之所以存在，就是因为背下来会忘，而查表只要 10 秒。
