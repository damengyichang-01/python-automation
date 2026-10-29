"""Excel 数据清洗工具 —— 去重、补空、统一日期格式。

用法：
    # 基本用法
    python clean_excel.py "原始数据.xlsx" -o 清洗结果.xlsx

    # 只看会清洗成什么样，不写文件
    python clean_excel.py "原始数据.xlsx" --dry-run

    # 指定只对某些列补空
    python clean_excel.py "原始数据.xlsx" -o 结果.xlsx --fill-cols 客户,金额

    # 指定日期列（不指定就自动找列名里带"日期""时间"的列）
    python clean_excel.py "原始数据.xlsx" -o 结果.xlsx --date-cols 日期,下单时间

    # 指定去重依据（默认整行完全相同才删）
    python clean_excel.py "原始数据.xlsx" -o 结果.xlsx --dedup-by 订单号
"""
import argparse
import sys
from pathlib import Path

import pandas as pd


def to_date_series(series: pd.Series) -> pd.Series:
    """把乱七八糟的日期字符串统一成 2026-10-17 这种格式。

    处理顺序：
      1. 中文日期 2026年10月17日 -> 2026-10-17
      2. 各种分隔符统一成 -
      3. 用 pandas format="mixed" 逐行推断格式（能处理月-日-年这种）
      4. 仍失败的按「月/日/年」再试一次（10-20-2026 -> 2026-10-20）
      5. 彻底解析失败的保留原值，不会变成空
    """
    s = series.astype(str).str.strip()

    # 中文日期
    s = s.str.replace("年", "-", regex=False)
    s = s.str.replace("月", "-", regex=False)
    s = s.str.replace("日", "", regex=False)
    s = s.str.replace("/", "-", regex=False)
    s = s.str.replace(".", "-", regex=False)

    # 第一轮：让 pandas 逐行推断格式（pandas >= 2.0 支持 mixed）
    try:
        parsed = pd.to_datetime(s, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        parsed = pd.to_datetime(s, errors="coerce")

    # 第二轮：对仍失败的尝试 月-日-年
    if parsed.isna().any():
        retry = pd.to_datetime(s, errors="coerce", format="%m-%d-%Y")
        parsed = parsed.fillna(retry)

    result = parsed.dt.strftime("%Y-%m-%d")
    result = result.where(parsed.notna(), series.astype(str))
    return result


def find_date_columns(df: pd.DataFrame) -> list:
    """自动找列名里带 日期/时间/date 的列。"""
    keywords = ("日期", "时间", "date", "Date", "DATE")
    return [c for c in df.columns if any(k in str(c) for k in keywords)]


def clean(df: pd.DataFrame, dedup_by=None, fill_cols=None, date_cols=None):
    """执行清洗，返回 (清洗后的 df, 清洗报告 dict)。"""
    report = {}
    rows_before = len(df)

    # ---------- 1. 去重 ----------
    if dedup_by:
        missing = [c for c in dedup_by if c not in df.columns]
        if missing:
            sys.exit(f"去重依据的列不存在：{', '.join(missing)}")
        df = df.drop_duplicates(subset=dedup_by, keep="first").copy()
    else:
        df = df.drop_duplicates(keep="first").copy()
    report["去重"] = rows_before - len(df)

    # ---------- 2. 补空 ----------
    if fill_cols:
        missing = [c for c in fill_cols if c not in df.columns]
        if missing:
            sys.exit(f"补空的列不存在：{', '.join(missing)}")
        targets = fill_cols
    else:
        targets = [c for c in df.columns if df[c].isna().any()]
    filled = 0
    for c in targets:
        n = int(df[c].isna().sum())
        if n:
            # 先转成 object 再填 —— 往 float64 列里填字符串在 pandas 4 会直接报错。
            # 这里本来就要把空值变成"未填"这几个字，转 object 是正确的语义。
            df[c] = df[c].astype(object).fillna("未填")
            filled += n
    report["补空"] = filled

    # ---------- 3. 统一日期 ----------
    if date_cols is None:
        date_cols = find_date_columns(df)
    changed = 0
    for c in date_cols:
        if c in df.columns:
            before = df[c].astype(str).str.strip()
            df[c] = to_date_series(df[c])
            changed += int((before != df[c].astype(str)).sum())
    report["日期归一"] = changed
    report["日期列"] = date_cols

    return df, report


def main():
    p = argparse.ArgumentParser(description="清洗 Excel 数据：去重、补空、统一日期")
    p.add_argument("source", help="要清洗的 Excel 文件")
    p.add_argument("-o", "--output", default="清洗结果.xlsx", help="输出文件名")
    p.add_argument("--dedup-by", default="", help="按这些列去重，逗号分隔；不填=整行相同才去重")
    p.add_argument("--fill-cols", default="", help="只对这些列补空，逗号分隔；不填=所有空值都补")
    p.add_argument("--date-cols", default="", help="指定日期列，逗号分隔；不填=自动识别")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    p.add_argument("--keep-index",action="store_true",help="保留原始行号(默认重排)")
    p.add_argument("--preview-rows",type=int,default=5,help="预览显示行数，默认5")
    args = p.parse_args()

    src = Path(args.source)
    if not src.is_file():
        sys.exit(f"文件不存在: {src}")

    df = pd.read_excel(src)
    print(f"读取：{src.name}")
    print(f"原始数据：{len(df)} 行 × {len(df.columns)} 列")
    print(f"列名：{', '.join(map(str, df.columns))}")

    dedup_by = [c.strip() for c in args.dedup_by.split(",") if c.strip()] or None
    fill_cols = [c.strip() for c in args.fill_cols.split(",") if c.strip()] or None
    date_cols = [c.strip() for c in args.date_cols.split(",") if c.strip()] if args.date_cols else None
        
    cleaned, report = clean(df, dedup_by=dedup_by, fill_cols=fill_cols, date_cols=date_cols)

    if not args.keep_index:
        cleaned = cleaned.reset_index(drop=True)

    print("\n" + "=" * 50)
    print("清洗报告：")
    print(f"  删除重复行：{report['去重']} 行")
    print(f"  填充空值：  {report['补空']} 个单元格")
    print(f"  日期归一：  {report['日期归一']} 个单元格")
    if report["日期列"]:
        print(f"  识别到的日期列：{', '.join(map(str, report['日期列']))}")
    print(f"\n清洗后：{len(cleaned)} 行 × {len(cleaned.columns)} 列")

    if args.dry_run:
        print(f"\n[预览模式] 未写文件。前{args.preview_rows}行：")
        print(cleaned.head(args.preview_rows).to_string())
        return

    out = Path(args.output)
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"已创建输出目录：{out.parent}")
    cleaned.to_excel(out, index=False)
    print(f"\n已保存：{out.resolve()}")


if __name__ == "__main__":
    main()
