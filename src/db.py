from __future__ import annotations

import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator

import pandas as pd
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "consumer_finance_analysis"),
    "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
}


def get_connection(local_infile: bool = False):
    return pymysql.connect(
        **DB_CONFIG,
        cursorclass=pymysql.cursors.DictCursor,
        local_infile=local_infile,
        autocommit=False,
    )


@contextmanager
def connection(local_infile: bool = False) -> Iterator[pymysql.connections.Connection]:
    conn = get_connection(local_infile=local_infile)
    try:
        yield conn
    finally:
        conn.close()


def query_df(sql: str, params: tuple | list | None = None) -> pd.DataFrame:
    with connection() as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, Decimal)).any():
            frame[column] = frame[column].astype(float)
    return frame


def execute(sql: str, params: tuple | list | None = None) -> None:
    with connection() as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
        conn.commit()

