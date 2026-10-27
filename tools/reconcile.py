"""两表对账 —— 找出只在A、只在B、以及金额不符的记录。

用法：
    python reconcile.py 系统表.xlsx 手工表.xlsx --key 订单号
"""
import argparse
import sys
from pathlib import Path

import pandas as pd


def reconcile(df_a, df_b, key, compare):
    """返回三个 DataFrame：(只在一表, 只在二表, 值不同)。"""
    keys_a = set(df_a[key])
    keys_b = set(df_b[key])

    # TODO 1：只在一表的记录
    only_a = df_a[~df_a[key].isin(keys_b)]
    # TODO 2：只在二表的记录
    only_b = df_b[~df_b[key].isin(keys_a)]
    # TODO 3：两边都有，但 compare 列的值不同
    both = df_a.merge(df_b,on=key,suffixes=("_系统","_手工"))
    diff = both[both[f"{compare}_系统"] != both[f"{compare}_手工"]]

    return only_a, only_b, diff


def main():
    p = argparse.ArgumentParser(description="两表对账")
    p.add_argument("file_a", help="表 A（比如系统导出）")
    p.add_argument("file_b", help="表 B（比如手工记录）")
    p.add_argument("--key", default="订单号", help="用来匹配的列名，默认 订单号")
    p.add_argument("--compare", default="金额", help="要比对的列名，默认 金额")
    p.add_argument("-o", "--output", default="对账结果.xlsx", help="输出文件名")
    args = p.parse_args()

    for path, name in ((args.file_a, "表 A"), (args.file_b, "表 B")):
        if not Path(path).is_file():
            sys.exit(f"{name} 的文件不存在：{path}")

    df_a = pd.read_excel(args.file_a)
    df_b = pd.read_excel(args.file_b)
    print(f"A 表：{len(df_a)} 行，B 表：{len(df_b)} 行")

    # 列名写错时给出可用列，别让用户对着 KeyError 猜
    for df, name in ((df_a, "表 A"), (df_b, "表 B")):
        cols = [str(c) for c in df.columns]
        if args.key not in cols:
            sys.exit(f"{name} 里没有「{args.key}」这一列。\n"
                     f"可用列：{', '.join(cols)}\n"
                     f"用 --key 指定正确的列名。")
        if args.compare not in cols:
            sys.exit(f"{name} 里没有「{args.compare}」这一列。\n"
                     f"可用列：{', '.join(cols)}\n"
                     f"用 --compare 指定正确的列名。")

    only_a, only_b, diff = reconcile(df_a, df_b, args.key, args.compare)

    print(f"\n只在 A 表：{len(only_a)} 条")
    print(f"只在 B 表：{len(only_b)} 条")
    print(f"值不同：  {len(diff)} 条")

    out = Path(args.output)
    with pd.ExcelWriter(out) as w:
        only_a.to_excel(w, sheet_name="只在A表", index=False)
        only_b.to_excel(w, sheet_name="只在B表", index=False)
        diff.to_excel(w, sheet_name="值不同", index=False)
    print(f"\n已保存：{out.resolve()}")


if __name__ == "__main__":
    main()