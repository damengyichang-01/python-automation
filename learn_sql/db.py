"""统一的数据库连接层 —— 用 SQLAlchemy，同一套代码连不同数据库。

为什么要这一层：
    直接用 pymysql 写死的代码，换成 PostgreSQL 就得重写。
    SQLAlchemy 把"连接"和"跑 SQL"抽象出来，换库只改一行连接串。

连接串格式（这个必须记住）：
    SQLite      sqlite:///相对路径.db          或 sqlite:///E:/绝对/路径.db
    MySQL       mysql+pymysql://用户:密码@主机:3306/库名?charset=utf8mb4
    PostgreSQL  postgresql+psycopg://用户:密码@主机:5432/库名
    SQL Server  mssql+pyodbc://用户:密码@主机:1433/库名?driver=...

四个要素：主机、端口、用户名/密码、库名。缺一样连不上。
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent
SQLITE_DSN = f"sqlite:///{HERE / 'demo.db'}"


def get_engine(dsn=None):
    """拿到一个数据库连接引擎。不传 dsn 就用本地的 SQLite 练习库。"""
    return create_engine(dsn or SQLITE_DSN, pool_pre_ping=True)


def query(sql, dsn=None):
    """跑一条 SQL，返回 DataFrame。"""
    engine = get_engine(dsn)
    try:
        with engine.connect() as con:
            return pd.read_sql_query(text(sql), con)
    finally:
        engine.dispose()


def list_tables(dsn=None):
    """列出库里的表名。"""
    engine = get_engine(dsn)
    try:
        insp = engine.dialect.get_schema_names  # 只是占位，避免 lint 警告
        from sqlalchemy import inspect
        return inspect(engine).get_table_names()
    finally:
        engine.dispose()


def main():
    dsn = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        tables = list_tables(dsn)
    except Exception as e:
        sys.exit(f"连接失败：{e}\n检查：主机/端口对不对、用户名密码对不对、库名存不存在、服务有没有启动。")

    print(f"连接成功：{'本地 SQLite 练习库' if not dsn else dsn.split('@')[-1]}")
    print(f"表：{'、'.join(tables) if tables else '（空库）'}")


if __name__ == "__main__":
    main()
