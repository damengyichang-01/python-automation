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


def load_orders(n=30, seed=7):
    """生成两张要对账的订单表。

    sys_orders    系统导出的表
    manual_orders 手工记的表

    故意埋了三种差异，用来练对账：
      · 只在系统表：SO005、SO017
      · 只在手工表：MX001、MX002
      · 金额不一致：SO003、SO011、SO024
    """
    rnd = random.Random(seed)
    names = [c[0] for c in CUSTOMERS]
    amounts = [500, 800, 1200, 1500, 3000]
    start = date(2026, 1, 1)

    sys_rows = []
    for i in range(1, n + 1):
        sys_rows.append({
            "订单号": f"SO{i:03d}",
            "日期": (start + timedelta(days=rnd.randint(0, 364))).isoformat(),
            "客户": rnd.choice(names),
            "金额": rnd.choice(amounts) * rnd.choice([1, 1, 2]),
        })
    sys_df = pd.DataFrame(sys_rows)

    # 手工表：以系统表为底，删 2 条、改 3 条金额、加 2 条新单
    manual = sys_df.copy()
    manual = manual[~manual["订单号"].isin(["SO005", "SO017"])].copy()

    for oid, amt in {"SO003": 999, "SO011": 1, "SO024": 8888}.items():
        manual.loc[manual["订单号"] == oid, "金额"] = amt

    extra = pd.DataFrame([
        {"订单号": "MX001", "日期": "2026-03-15", "客户": rnd.choice(names), "金额": 700},
        {"订单号": "MX002", "日期": "2026-12-08", "客户": rnd.choice(names), "金额": 2500},
    ])
    manual = pd.concat([manual, extra], ignore_index=True)
    manual = manual.sort_values("日期").reset_index(drop=True)
    return sys_df, manual



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
    sys_orders, manual_orders = load_orders()

    # 不删库文件 —— 如果 SQL 环境还开着，删文件会报"正在被使用"。
    # 直接重建表更稳，表结构变了也能刷新。
    con = sqlite3.connect(DB)
    try:
        for name in ("sales", "customers", "sys_orders", "manual_orders"):
            con.execute(f"DROP TABLE IF EXISTS {name}")
        con.commit()
        sales.to_sql("sales", con, index=False)
        customers.to_sql("customers", con, index=False)
        sys_orders.to_sql("sys_orders", con, index=False)
        manual_orders.to_sql("manual_orders", con, index=False)
    finally:
        con.close()

    print(f"已生成：{DB}")
    print(f"  sales          {len(sales):>3} 行  列：{', '.join(sales.columns)}")
    print(f"  customers      {len(customers):>3} 行  列：{', '.join(customers.columns)}")
    print(f"  sys_orders     {len(sys_orders):>3} 行  列：{', '.join(sys_orders.columns)}")
    print(f"  manual_orders  {len(manual_orders):>3} 行  列：{', '.join(manual_orders.columns)}")
    print()
    print("对账练习用 sys_orders 和 manual_orders 这两张表，")
    print("里面故意埋了三种差异（只在系统、只在手工、金额不一致）。")
    print()
    print("其他说明：数据是为练习生成的示例，结构和你项目里的真实表一致。")


if __name__ == "__main__":
    main()
