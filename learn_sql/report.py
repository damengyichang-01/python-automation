"""月度对账报表生成器 —— 支持 SQLite / MySQL / MariaDB / PostgreSQL。

用法：
    # 本地 SQLite 练习库
    py -3.12 learn_sql/report.py

    # 连 MariaDB（本机，root 空密码）
    py -3.12 learn_sql/report.py --dsn "mysql+pymysql://root:@127.0.0.1:3306/practice?charset=utf8mb4"

    # 指定输出文件名
    py -3.12 learn_sql/report.py --dsn "..." -o 客户的报表.xlsx

输出三个工作表：月度汇总、差异明细、漏记统计。

两个跨数据库的关键写法：
  1. 日期格式化每个库都不一样（strftime / DATE_FORMAT / to_char），
     所以按当前连接的数据库类型自动挑函数。
  2. MySQL/MariaDB 不支持 FULL OUTER JOIN，
     所以统一用 LEFT JOIN + UNION + RIGHT JOIN 的写法，四个库都能跑。
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent
SQLITE_DSN = f"sqlite:///{HERE / 'demo.db'}"
DEFAULT_OUT = HERE / "月度对账报表.xlsx"

# 把日期列变成"年-月"的写法，各库不同。
# {col} 会被替换成 日期 或 表别名.日期 —— 避免多表连接时列名歧义。
MONTH_EXPR = {
    "sqlite": "strftime('%Y-%m', {col})",
    "mysql": "DATE_FORMAT({col}, '%Y-%m')",
    "mariadb": "DATE_FORMAT({col}, '%Y-%m')",
    "postgresql": "to_char({col}, 'YYYY-MM')",
    "mssql": "FORMAT(CAST({col} AS date), 'yyyy-MM')",
}


def month_expr(dialect, table_alias=""):
    """生成日期格式化表达式。table_alias 用于多表连接时限定列归属。"""
    tmpl = MONTH_EXPR.get(dialect)
    if not tmpl:
        raise SystemExit(
            f"还不支持 {dialect} 这个数据库。已支持：{', '.join(MONTH_EXPR)}\n"
            f"你需要在 MONTH_EXPR 里加一条它对应的日期格式化写法。"
        )
    col = f"{table_alias}.日期" if table_alias else "日期"
    return tmpl.format(col=col)


def build_monthly_sql(me):
    """按月对账。用 LEFT UNION RIGHT 模拟 FULL OUTER JOIN，兼容 MySQL。"""
    sys_agg = f"SELECT {me} AS 月份, count(*) AS 笔数, sum(金额) AS 总额 FROM sys_orders GROUP BY 月份"
    man_agg = f"SELECT {me} AS 月份, count(*) AS 笔数, sum(金额) AS 总额 FROM manual_orders GROUP BY 月份"
    cols = ("COALESCE(s.月份, m.月份) AS 月份, "
            "COALESCE(s.笔数, 0) AS 系统笔数, COALESCE(s.总额, 0) AS 系统总额, "
            "COALESCE(m.笔数, 0) AS 手工笔数, COALESCE(m.总额, 0) AS 手工总额, "
            "COALESCE(m.总额, 0) - COALESCE(s.总额, 0) AS 差额")
    return f"""
SELECT {cols}
FROM ({sys_agg}) s LEFT JOIN ({man_agg}) m ON s.月份 = m.月份
UNION
SELECT {cols}
FROM ({sys_agg}) s RIGHT JOIN ({man_agg}) m ON s.月份 = m.月份
WHERE s.月份 IS NULL
ORDER BY 月份
"""


def build_diff_sql():
    """三类差异合成一张表。全都是通用写法，不需要按库分支。"""
    return """
SELECT '只在系统' AS 类型, s.订单号, s.日期, s.客户,
       s.金额 AS 系统金额, NULL AS 手工金额, NULL AS 差额
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


def build_missing_sql(me_aliased):
    return f"""
SELECT {me_aliased} AS 月份, count(*) AS 漏记单数
FROM sys_orders s
LEFT JOIN manual_orders m ON s.订单号 = m.订单号
WHERE m.订单号 IS NULL
GROUP BY 月份
ORDER BY 月份
"""


def to_numeric_cols(df, cols):
    """把金额列统一成 float —— 不同数据库 sum() 返回类型不一样（整数 / Decimal）。"""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main():
    p = argparse.ArgumentParser(description="生成月度对账报表（支持多种数据库）")
    p.add_argument("--dsn", default="",
                   help="数据库连接串，不填就用本地 SQLite 练习库。"
                        "例：mysql+pymysql://root:@127.0.0.1:3306/practice?charset=utf8mb4")
    p.add_argument("-o", "--output", default=str(DEFAULT_OUT), help="输出文件名")
    args = p.parse_args()

    dsn = args.dsn or SQLITE_DSN
    engine = create_engine(dsn, pool_pre_ping=True)

    try:
        with engine.connect():
            pass
    except Exception as e:
        sys.exit(f"连不上数据库：{e}\n\n检查四项：主机、端口、用户名密码、库名。")

    dialect = engine.dialect.name
    me = month_expr(dialect)
    me_s = month_expr(dialect, "s")   # 多表连接时用带别名的版本
    print(f"已连接：{dialect}" + ("" if args.dsn else "（本地练习库）"))

    try:
        with engine.connect() as con:
            monthly = pd.read_sql_query(text(build_monthly_sql(me)), con)
            diff = pd.read_sql_query(text(build_diff_sql()), con)
            missing = pd.read_sql_query(text(build_missing_sql(me_s)), con)
    finally:
        engine.dispose()

    monthly = to_numeric_cols(monthly, ["系统总额", "手工总额", "差额"])
    diff = to_numeric_cols(diff, ["系统金额", "手工金额", "差额"])

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
