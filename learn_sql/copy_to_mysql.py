"""把本地 SQLite 练习库的数据复制到 MariaDB（或 MySQL）。

用法：
    py -3.12 learn_sql/copy_to_mysql.py
    py -3.12 learn_sql/copy_to_mysql.py --dsn "mysql+pymysql://root:密码@127.0.0.1:3306/practice?charset=utf8mb4"

默认连接串（本机 MariaDB，root 空密码）：
    mysql+pymysql://root:@127.0.0.1:3306/practice?charset=utf8mb4

复制完成后，可以用同一个 db.py 查询两种数据库，SQL 完全一样。
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent
SQLITE_DB = HERE / "demo.db"

DEFAULT_DSN = "mysql+pymysql://root:@127.0.0.1:3306/practice?charset=utf8mb4"
TABLES = ["sales", "customers", "sys_orders", "manual_orders"]


def main():
    p = argparse.ArgumentParser(description="把 SQLite 练习数据复制到 MySQL/MariaDB")
    p.add_argument("--dsn", default=DEFAULT_DSN, help="目标数据库连接串")
    p.add_argument("--db-name", default="practice", help="目标库名")
    args = p.parse_args()

    if not SQLITE_DB.exists():
        sys.exit(f"找不到 SQLite 练习库：{SQLITE_DB}\n请先运行：py -3.12 learn_sql/setup_db.py")

    # 先连到服务器（不带库名），把库建出来
    server_dsn = args.dsn.split("?")[0].rsplit("/", 1)[0] + "/?charset=utf8mb4"
    server = create_engine(server_dsn)
    try:
        with server.connect() as con:
            con.execute(text(
                f"CREATE DATABASE IF NOT EXISTS {args.db_name} "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            ))
            con.commit()
        print(f"数据库已就绪：{args.db_name}")
    except Exception as e:
        sys.exit(f"连不上数据库：{e}\n\n检查：\n"
                 f"  · MariaDB 有没有在运行（端口 3306）\n"
                 f"  · 用户名密码对不对\n"
                 f"  · 连接串格式：mysql+pymysql://用户:密码@主机:3306/库名")
    finally:
        server.dispose()

    target = create_engine(args.dsn)
    lite = sqlite3.connect(SQLITE_DB)
    try:
        for name in TABLES:
            df = pd.read_sql_query(f"SELECT * FROM {name}", lite)
            df.to_sql(name, target, index=False, if_exists="replace")
            print(f"  {name:15} {len(df):>3} 行")
    finally:
        lite.close()
        target.dispose()

    print()
    print("复制完成。现在可以用同一个 SQL 查两种数据库：")
    print(f'  py -3.12 learn_sql/db.py                         # SQLite')
    print(f'  py -3.12 learn_sql/db.py "{args.dsn}"            # MariaDB')


if __name__ == "__main__":
    main()
