"""跑一条 SQL 并把结果打印成表格。

用法：
    py -3.12 learn_sql/run.py "SELECT * FROM sales LIMIT 5"
    py -3.12 learn_sql/run.py -f learn_sql/my_query.sql

也可以用 -v 看这条 SQL 用了多久：
    py -3.12 learn_sql/run.py "SELECT count(*) FROM sales" -v
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

DB = Path(__file__).resolve().parent / "demo.db"


def print_table(rows, cols):
    if not rows:
        print("（查询成功，但没有数据）")
        return
    # 每列按最长的内容对齐
    widths = []
    for i, c in enumerate(cols):
        w = len(str(c))
        for r in rows:
            w = max(w, len(str(r[i])))
        widths.append(min(w, 30))

    def line(char="─"):
        return "┼".join(char * (w + 2) for w in widths)

    print("│ " + " │ ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)) + " │")
    print(line())
    for r in rows:
        cells = []
        for i, v in enumerate(r):
            s = str(v) if v is not None else "NULL"
            if len(s) > widths[i]:
                s = s[: widths[i] - 1] + "…"
            cells.append(s.ljust(widths[i]))
        print("│ " + " │ ".join(cells) + " │")
    print(f"\n共 {len(rows)} 行")


def main():
    p = argparse.ArgumentParser(description="跑一条 SQL")
    p.add_argument("sql", nargs="?", default="", help="SQL 语句")
    p.add_argument("-f", "--file", default="", help="从文件读取 SQL")
    p.add_argument("-v", "--verbose", action="store_true", help="显示耗时")
    args = p.parse_args()

    sql = args.sql
    if args.file:
        sql = Path(args.file).read_text(encoding="utf-8")
    if not sql.strip():
        sys.exit('请给一条 SQL，例如：run.py "SELECT * FROM sales LIMIT 5"')

    if not DB.exists():
        sys.exit(f"数据库不存在：{DB}\n请先运行：py -3.12 learn_sql/setup_db.py")

    con = sqlite3.connect(DB)
    try:
        start = time.perf_counter()
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        cost = (time.perf_counter() - start) * 1000
    except sqlite3.Error as e:
        sys.exit(f"SQL 出错：{e}")
    finally:
        con.close()

    if cols:
        print_table(rows, cols)
    if args.verbose:
        print(f"耗时 {cost:.1f} ms")


if __name__ == "__main__":
    main()
