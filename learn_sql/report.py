"""月度对账报表生成器 —— SQL 查询 + Excel 输出。

用法：
    py -3.12 learn_sql/report.py
    py -3.12 learn_sql/report.py -o 我的对账报表.xlsx

输出三个工作表：
    月度汇总   每个月系统/手工的笔数、总额、差额
    差异明细   三类差异（只在系统、只在手工、金额不符）合成一张表
    漏记统计   按月份统计系统有、手工没有的订单数

这就是"客户给你两张表，你给他一份报表"的最小实现。
把 SQL 换成客户真实的表名和列名，就能直接用。
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE / "demo.db"
OUT = HERE / "月度对账报表.xlsx"

SQL_MONTHLY = """
SELECT COALESCE(s.月份, m.月份) AS 月份,
       COALESCE(s.笔数, 0) AS 系统笔数,
       COALESCE(s.总额, 0) AS 系统总额,
       COALESCE(m.笔数, 0) AS 手工笔数,
       COALESCE(m.总额, 0) AS 手工总额,
       COALESCE(m.总额, 0) - COALESCE(s.总额, 0) AS 差额
FROM (SELECT strftime('%Y-%m', 日期) AS 月份, count(*) AS 笔数, sum(金额) AS 总额
      FROM sys_orders GROUP BY 月份) s
FULL OUTER JOIN
     (SELECT strftime('%Y-%m', 日期) AS 月份, count(*) AS 笔数, sum(金额) AS 总额
      FROM manual_orders GROUP BY 月份) m
  ON s.月份 = m.月份
ORDER BY 月份
"""

SQL_DIFF = """
SELECT '只在系统' AS 类型, s.订单号, s.日期, s.客户, s.金额 AS 系统金额, NULL AS 手工金额, NULL AS 差额
FROM sys_orders s
LEFT JOIN manual_orders m ON s.订单号 = m.订单号
WHERE m.订单号 IS NULL

UNION ALL

SELECT '只在手工', m.订单号, m.日期, m.客户, NULL, m.金额, NULL
FROM manual_orders m
LEFT JOIN sys_orders s ON m.订单号 = s.订单号
WHERE s.订单号 IS NULL

UNION ALL

SELECT '金额不符', s.订单号, s.日期, s.客户, s.金额, m.金额, m.金额 - s.金额
FROM sys_orders s
JOIN manual_orders m ON s.订单号 = m.订单号
WHERE s.金额 != m.金额
"""

SQL_MISSING = """
SELECT strftime('%Y-%m', s.日期) AS 月份, count(*) AS 漏记单数
FROM sys_orders s
LEFT JOIN manual_orders m ON s.订单号 = m.订单号
WHERE m.订单号 IS NULL
GROUP BY 月份
ORDER BY 月份
"""


def run_query(con, sql):
    return pd.read_sql_query(sql, con)


def main():
    p = argparse.ArgumentParser(description="生成月度对账报表")
    p.add_argument("-o", "--output", default=str(OUT), help="输出文件名")
    args = p.parse_args()

    if not DB.exists():
        sys.exit(f"数据库不存在：{DB}\n请先运行：py -3.12 learn_sql/setup_db.py")

    con = sqlite3.connect(DB)
    try:
        monthly = run_query(con, SQL_MONTHLY)
        diff = run_query(con, SQL_DIFF)
        missing = run_query(con, SQL_MISSING)
    finally:
        con.close()

    out = Path(args.output)
    with pd.ExcelWriter(out) as w:
        monthly.to_excel(w, sheet_name="月度汇总", index=False)
        diff.to_excel(w, sheet_name="差异明细", index=False)
        missing.to_excel(w, sheet_name="漏记统计", index=False)

    total_sys = int(monthly["系统总额"].sum())
    total_manual = int(monthly["手工总额"].sum())
    bad_months = monthly[monthly["差额"] != 0]

    print(f"报表已生成：{out.resolve()}")
    print()
    print(f"系统总额 : {total_sys:,}")
    print(f"手工总额 : {total_manual:,}")
    print(f"总差额   : {total_manual - total_sys:+,}")
    print()
    print(f"有差异的月份：{len(bad_months)} 个")
    for _, r in bad_months.iterrows():
        print(f"  {r['月份']}  系统 {int(r['系统总额']):>6,}  手工 {int(r['手工总额']):>6,}  差额 {int(r['差额']):>+6,}")
    print()
    print(f"差异订单：{len(diff)} 条")
    for t, n in diff["类型"].value_counts().items():
        print(f"  {t}：{n} 条")
    if len(missing):
        print()
        print("漏记月份：")
        for _, r in missing.iterrows():
            print(f"  {r['月份']}  漏记 {int(r['漏记单数'])} 单")


if __name__ == "__main__":
    main()
