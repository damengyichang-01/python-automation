"""生成 SQL 练习用的 SQLite 数据库。

运行：
    py -3.12 learn_sql/setup_db.py

生成 learn_sql/demo.db，两张表：
    sales      销售记录（订单号、日期、客户、金额、产品、数量）
    customers  客户资料（客户、城市、等级）

数据是为练习生成的示例，结构和你项目里的真实表一致：
拿到真实数据后，把 load_sales() 换成读 Excel 就行。
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parent / "demo.db"

CUSTOMERS = [
    ("甲公司", "北京", "A"),
    ("乙公司", "上海", "B"),
    ("丙公司", "北京", "A"),
    ("丁公司", "广州", "C"),
    ("戊公司", "上海", "B"),
    ("己公司", "深圳", "C"),
    ("庚公司", "广州", "B"),
    ("辛公司", "北京", "A"),
]

PRODUCTS = [("A款", 1200), ("B款", 850), ("C款", 500), ("D款", 3000)]


def load_customers():
    return pd.DataFrame(CUSTOMERS, columns=["客户", "城市", "等级"])


def load_sales(n=60, seed=42):
    """生成 n 笔销售记录。用固定随机种子，保证每次生成的数据一样。"""
    rnd = random.Random(seed)
    start = date(2026, 1, 1)
    rows = []
    for i in range(1, n + 1):
        name, _, level = rnd.choice(CUSTOMERS)
        product, unit = rnd.choice(PRODUCTS)
        qty = rnd.choice([1, 1, 1, 2, 2, 3, 5])
        # A 级客户通常买得多一点
        if level == "A":
            qty += rnd.choice([0, 1, 2])
        amount = unit * qty
        d = start + timedelta(days=rnd.randint(0, 364))
        rows.append({
            "订单号": f"S{i:03d}",
            "日期": d.isoformat(),
            "客户": name,
            "产品": product,
            "数量": qty,
            "金额": amount,
        })
    return pd.DataFrame(rows)


def main():
    sales = load_sales()
    customers = load_customers()

    if DB.exists():
        DB.unlink()

    con = sqlite3.connect(DB)
    try:
        sales.to_sql("sales", con, index=False)
        customers.to_sql("customers", con, index=False)
    finally:
        con.close()

    print(f"已生成：{DB}")
    print(f"  sales       {len(sales)} 行  列：{', '.join(sales.columns)}")
    print(f"  customers   {len(customers)} 行  列：{', '.join(customers.columns)}")
    print()
    print("sales 前 5 行：")
    print(sales.head().to_string(index=False))
    print()
    print("customers 全部：")
    print(customers.to_string(index=False))
    print()
    print("说明：这些数据是为练习生成的示例。结构和你的真实 Excel 一致，")
    print("     换成真实数据只需把 load_sales() 改成读 Excel 文件。")


if __name__ == "__main__":
    main()
