"""工具之间共用的小函数。"""
import re
from pathlib import Path


def natural_key(name):
    """让 1.pdf、2.pdf、10.pdf 按人眼习惯排序。

    直接 sorted() 会排成 1、10、2 —— 因为字符串是逐字符比较的，
    '1' < '2'，但 '10' 的第二位 '0' 比 '2' 小，所以 10 跑到 2 前面。

    这个函数把文件名切成"文字/数字"交替的片段，数字转成 int 再比，
    于是 10 会被当作数字十，自然排在 2 后面。
    """
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", name)]


def unique_path(path, limit=999):
    """如果文件已存在，自动改成 名字(2).xlsx、名字(3).xlsx …

    为什么需要：pandas / openpyxl / pypdf 写文件时会**直接覆盖**，不给任何提示。
    客户的原始数据可能就这么被同一份结果覆盖掉了。
    这里保证"永远不覆盖已有文件"，最多试 limit 次。
    """
    p = Path(path)
    if not p.exists():
        return p

    stem, suffix = p.stem, p.suffix
    for i in range(2, limit + 2):
        candidate = p.with_name(f"{stem}({i}){suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"同名文件太多了，换个文件名吧：{p}")


def unique_dir(path, limit=999):
    """如果目录已存在，自动改成 名字(2)、名字(3) …

    用于"输出一堆文件"的场景（拆分 PDF、批量替换 Word），
    避免第二次运行时悄悄覆盖上一次的结果。
    """
    p = Path(path)
    if not p.exists():
        return p

    for i in range(2, limit + 2):
        candidate = p.with_name(f"{p.name}({i})")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"同名文件夹太多了，换个名字吧：{p}")
