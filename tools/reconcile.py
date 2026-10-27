"""两表对账 —— 找出只在A、只在B、以及字段值不一致的记录。

用法：
    python reconcile.py 系统表.xlsx 手工表.xlsx --key 订单号
    python reconcile.py a.xlsx b.xlsx --key 订单号 --compare 金额,客户
"""
import argparse
import sys
from pathlib import Path

import pandas as pd


def field_differs(sa, sb):
    """两列逐行比较，返回"这一行该字段是否不同"的布尔序列。

    两边都是空值算相同 —— 否则每个空单元格都会被报成差异。
    """
    return ~((sa == sb) | (sa.isna() & sb.isna()))


def reconcile(df_a, df_b, key, compare_cols):
    """返回三个 DataFrame：(只在一表, 只在二表, 值不同)。"""
    keys_a = set(df_a[key])
    keys_b = set(df_b[key])

    only_a = df_a[~df_a[key].isin(keys_b)]
    only_b = df_b[~df_b[key].isin(keys_a)]

    both = df_a.merge(df_b, on=key, suffixes=("_系统", "_手工"))

    mask = None
    for c in compare_cols:
        m = field_differs(both[f"{c}_系统"], both[f"{c}_手工"])
        mask = m if mask is None else (mask | m)

    diff = both[mask].copy() if mask is not None else both.iloc[0:0].copy()

    # 告诉客户到底哪个字段对不上，而不是只给一堆列
    if len(diff):
        def which(r):
            out = []
            for c in compare_cols:
                a, b = r[f"{c}_系统"], r[f"{c}_手工"]
                if pd.isna(a) and pd.isna(b):
                    continue
                if a != b:
                    out.append(c)
            return "、".join(out)

        diff.insert(1, "差异字段", diff.apply(which, axis=1))

    return only_a, only_b, diff


def main():
    p = argparse.ArgumentParser(description="两表对账")
    p.add_argument("file_a", help="表 A（比如系统导出）")
    p.add_argument("file_b", help="表 B（比如手工记录）")
    p.add_argument("--key", default="订单号", help="用来匹配的列名，默认 订单号")
    p.add_argument("--compare", default="金额",
                   help="要比对的列名，默认 金额；多列用逗号隔开，如 金额,客户")
    p.add_argument("-o", "--output", default="对账结果.xlsx", help="输出文件名")
    args = p.parse_args()

    for path, name in ((args.file_a, "表 A"), (args.file_b, "表 B")):
        if not Path(path).is_file():
            sys.exit(f"{name} 的文件不存在：{path}")

    df_a = pd.read_excel(args.file_a)
    df_b = pd.read_excel(args.file_b)
    print(f"A 表：{len(df_a)} 行，B 表：{len(df_b)} 行")

    compare_cols = [c.strip() for c in args.compare.split(",") if c.strip()]
    if not compare_cols:
        sys.exit("--compare 至少要指定一列")

    # 列名写错时给出可用列，别让用户对着 KeyError 猜
    for df, name in ((df_a, "表 A"), (df_b, "表 B")):
        cols = [str(c) for c in df.columns]
        if args.key not in cols:
            sys.exit(f"{name} 里没有「{args.key}」这一列。\n"
                     f"可用列：{', '.join(cols)}\n"
                     f"用 --key 指定正确的列名。")
        absent = [c for c in compare_cols if c not in cols]
        if absent:
            sys.exit(f"{name} 里没有这几列：{'、'.join(absent)}\n"
                     f"可用列：{', '.join(cols)}\n"
                     f"用 --compare 指定正确的列名，多列用逗号隔开。")

    print(f"比对字段：{'、'.join(compare_cols)}")

    only_a, only_b, diff = reconcile(df_a, df_b, args.key, compare_cols)

    print(f"\n只在 A 表：{len(only_a)} 条")
    print(f"只在 B 表：{len(only_b)} 条")
    print(f"值不同：  {len(diff)} 条")
    if len(diff) and "差异字段" in diff.columns:
        print("\n不一致的记录：")
        for _, row in diff.head(10).iterrows():
            parts = []
            for c in compare_cols:
                a, b = row[f"{c}_系统"], row[f"{c}_手工"]
                if pd.isna(a) and pd.isna(b):
                    continue
                if a == b:
                    continue
                parts.append(f"{c} {a} → {b}")
            print(f"  {row[args.key]}：{'，'.join(parts)}")
        if len(diff) > 10:
            print(f"  …… 还有 {len(diff) - 10} 条，见结果文件")

    out = Path(args.output)
    with pd.ExcelWriter(out) as w:
        only_a.to_excel(w, sheet_name="只在A表", index=False)
        only_b.to_excel(w, sheet_name="只在B表", index=False)
        diff.to_excel(w, sheet_name="值不同", index=False)
    print(f"\n已保存：{out.resolve()}")


if __name__ == "__main__":
    main()