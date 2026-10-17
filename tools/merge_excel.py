"""多张 Excel/CSV 合并成一张 —— 按列名对齐，自动加来源列。

用法：
    # 基本用法：合并目录下所有文件
    python merge_excel.py "数据目录" -o 合并结果.xlsx

    # 只保留需要的列
    python merge_excel.py "数据目录" -o 结果.xlsx --keep 日期,金额,客户

    # 只看会合并成什么样，不写文件
    python merge_excel.py "数据目录" --dry-run

    # 按列位置对齐（各表列名不一致但顺序一致时用）
    python merge_excel.py "数据目录" -o 结果.xlsx --align position

    # 每个文件所有工作表都读（默认只读第一个）
    python merge_excel.py "数据目录" -o 结果.xlsx --all-sheets
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

EXCEL_SUFFIXES = {".xlsx", ".xlsm"}
CSV_SUFFIXES = {".csv"}


def collect_files(folder: Path):
    """找出目录下所有 Excel / CSV 文件，按文件名排序保证结果稳定。"""
    files = []
    for f in sorted(folder.iterdir(), key=lambda p: p.name):
        if not f.is_file():
            continue
        if f.suffix.lower() in EXCEL_SUFFIXES | CSV_SUFFIXES:
            files.append(f)
    return files


def read_one(path: Path, all_sheets: bool):
    """读一个文件，返回 [(工作表名, DataFrame), ...]。"""
    suffix = path.suffix.lower()
    if suffix in CSV_SUFFIXES:
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="gbk")
        return [(path.stem, df)]

    sheets = pd.read_excel(path, sheet_name=None if all_sheets else 0)
    if isinstance(sheets, pd.DataFrame):
        return [(path.stem, sheets)]
    return [(name, sheet) for name, sheet in sheets.items()]


def merge(frames, align: str):
    """合并多个 DataFrame。

    align="name"     : 按列名对齐，缺失列填 NaN，多出来的列也保留
    align="position" : 按列的先后位置对齐，强制套用第一张表的列名
    """
    if not frames:
        return None

    if align == "position":
        ref_cols = list(frames[0][1].columns)
        aligned = []
        for source, df in frames:
            df = df.copy()
            df.columns = ref_cols[: len(df.columns)] if len(df.columns) <= len(ref_cols) \
                else ref_cols + [f"列{i}" for i in range(len(ref_cols), len(df.columns))]
            df.insert(0, "_来源文件", source)
            aligned.append(df)
        return pd.concat(aligned, ignore_index=True, sort=False)

    prepared = []
    for source, df in frames:
        df = df.copy()
        df.insert(0, "_来源文件", source)
        prepared.append(df)
    return pd.concat(prepared, ignore_index=True, sort=False)


def main():
    p = argparse.ArgumentParser(description="把多张 Excel/CSV 合并成一张表")
    p.add_argument("folder", help="存放要合并文件的目录")
    p.add_argument("-o", "--output", default="合并结果.xlsx", help="输出文件名，默认 合并结果.xlsx")
    p.add_argument("--align", choices=["name", "position"], default="name",
                   help="对齐方式：name=按列名（默认），position=按列位置")
    p.add_argument("--keep", default="", help="只保留这些列，逗号分隔，例如 日期,金额")
    p.add_argument("--all-sheets", action="store_true", help="读取每个文件的所有工作表")
    p.add_argument("--no-source", action="store_true", help="不添加 _来源文件 列")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    args = p.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"目录不存在: {folder}")

    files = collect_files(folder)
    if not files:
        sys.exit(f"在 {folder} 里没找到 .xlsx / .xlsm / .csv 文件")

    print(f"找到 {len(files)} 个文件：")
    frames = []
    for f in files:
        try:
            parts = read_one(f, args.all_sheets)
        except Exception as e:
            print(f"  [跳过] {f.name} —— 读取失败：{e}")
            continue
        for sheet_name, df in parts:
            source = f.name if not args.all_sheets else f"{f.name} › {sheet_name}"
            frames.append((source, df))
            print(f"  [读取] {source}  {len(df)} 行 × {len(df.columns)} 列")

    if not frames:
        sys.exit("没有任何文件读取成功")

    # 预览各文件列名差异
    all_cols = []
    for _, df in frames:
        for c in df.columns:
            if c not in all_cols:
                all_cols.append(c)
    print(f"\n全部列名（共 {len(all_cols)} 个）：{', '.join(map(str, all_cols))}")

    merged = merge(frames, args.align)
    if merged is None:
        sys.exit("合并失败：没有可用数据")

    if args.keep:
        keep = [c.strip() for c in args.keep.split(",") if c.strip()]
        missing = [c for c in keep if c not in merged.columns]
        if missing:
            sys.exit(f"这些列在合并结果里不存在：{', '.join(missing)}")
        merged = merged[keep]

    if args.no_source and "_来源文件" in merged.columns:
        merged = merged.drop(columns=["_来源文件"])

    print(f"\n{'=' * 50}")
    print(f"合并结果：{len(merged)} 行 × {len(merged.columns)} 列")
    if "_来源文件" in merged.columns:
        print("\n各文件贡献行数：")
        for name, cnt in merged["_来源文件"].value_counts().items():
            print(f"  {name}: {cnt} 行")

    if args.dry_run:
        print("\n[预览模式] 未写文件。前 5 行：")
        print(merged.head().to_string())
        return

    out = Path(args.output)
    # 输出目录不存在就自动建，别让用户为这种事卡住
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"已创建输出目录：{out.parent}")
    merged.to_excel(out, index=False)
    print(f"\n已保存：{out.resolve()}")


if __name__ == "__main__":
    main()
