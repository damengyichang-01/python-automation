"""工具之间共用的小函数。"""
import re


def natural_key(name):
    """让 1.pdf、2.pdf、10.pdf 按人眼习惯排序。

    直接 sorted() 会排成 1、10、2 —— 因为字符串是逐字符比较的，
    '1' < '2'，但 '10' 的第二位 '0' 比 '2' 小，所以 10 跑到 2 前面。

    这个函数把文件名切成"文字/数字"交替的片段，数字转成 int 再比，
    于是 10 会被当作数字十，自然排在 2 后面。
    """
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", name)]
