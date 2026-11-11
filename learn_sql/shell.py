"""交互式 SQL 练习环境。

用法：
    py -3.12 learn_sql/shell.py

进去以后直接敲 SQL，以分号结尾就执行：
    sql> SELECT * FROM sales LIMIT 5;

其他命令：
    .tables    看有哪些表
    .schema    看表结构
    .help      看帮助
    .quit      退出
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "demo.db"


def print_table(rows, cols):
    if not rows:
        print("（查询成功，但没有数据）")
        return
    widths = []
    for i, c in enumerate(cols):
        w = len(str(c))
        for r in rows:
            w = max(w, len(str(r[i])))
        widths.append(min(w, 30))

    print("│ " + " │ ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)) + " │")
    print("┼".join("─" * (w + 2) for w in widths))
    for r in rows:
        cells = []
        for i, v in enumerate(r):
            s = str(v) if v is not None else "NULL"
            if len(s) > widths[i]:
                s = s[: widths[i] - 1] + "…"
            cells.append(s.ljust(widths[i]))
        print("│ " + " │ ".join(cells) + " │")
    print(f"共 {len(rows)} 行")


def run(con, sql):
    try:
        cur = con.execute(sql)
        if cur.description:
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            print_table(rows, cols)
        else:
            con.commit()
            print(f"执行成功，影响 {cur.rowcount} 行")
    except sqlite3.Error as e:
        print(f"❌ SQL 出错：{e}")


def show_tables(con):
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print("表：" + "、".join(r[0] for r in cur.fetchall()))


def show_schema(con):
    cur = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
    for (sql,) in cur.fetchall():
        print(sql + ";")


def show_help():
    print("""
用法：
  · 直接敲 SQL，以分号 ; 结尾就会执行
  · 一条 SQL 可以分好几行敲，敲完分号再回车

命令：
  .tables   看有哪些表
  .schema   看表结构
  .help     看这个帮助
  .quit     退出

试试这几条：
  SELECT * FROM sales LIMIT 5;
  SELECT 客户, sum(金额) AS 总额 FROM sales GROUP BY 客户 ORDER BY 总额 DESC;
""")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not DB.exists():
        sys.exit(f"数据库不存在：{DB}\n请先运行：py -3.12 learn_sql/setup_db.py")

    con = sqlite3.connect(DB)
    print("=" * 52)
    print("  SQL 练习环境  （.help 看帮助，.quit 退出）")
    print("=" * 52)
    show_tables(con)
    print()

    buf = []
    try:
        while True:
            prompt = "sql> " if not buf else " ...> "
            try:
                line = input(prompt)
            except EOFError:
                print()
                break

            # 粘贴进来或从文件重定向时可能带 BOM，去掉它，否则第一条命令会被当 SQL
            line = line.replace("\ufeff", "")
            stripped = line.strip()

            if not buf:
                if stripped in (".quit", ".exit", "quit", "exit"):
                    break
                if stripped == ".help":
                    show_help()
                    continue
                if stripped == ".tables":
                    show_tables(con)
                    continue
                if stripped == ".schema":
                    show_schema(con)
                    continue
                if not stripped:
                    continue

            buf.append(line)

            if stripped.endswith(";"):
                sql = "\n".join(buf).strip().rstrip(";")
                buf = []
                if sql:
                    run(con, sql)
                    print()
    finally:
        con.close()
        print("已退出。")


if __name__ == "__main__":
    main()
