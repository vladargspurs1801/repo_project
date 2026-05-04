"""
db_connection.py.
В этом модуле через декоратор создается объект менеджера контекста для подключения к СУБД GreenPlum и Postgres.
"""
import os
import psycopg2 as ps
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()

@contextmanager
def postgres_conn():
    """Возвращает соединение с PostgresSQL."""
    conn = ps.connect(host=os.getenv('HOST_PG'),
                      port=os.getenv('PORT_PG', '5432'),
                      database=os.getenv('DATABASE_PG'),
                      user=os.getenv('USER_PG'),
                      password=os.getenv('PASSWORD_PG')
                    )
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
    return conn

@contextmanager
def greenplum_conn():
    """Возвращает соединение с GreenPlum."""
    conn = ps.connect(host=os.getenv('HOST_GP'),
                      port=os.getenv('PORT_GP', '5432'),
                      database=os.getenv('DATABASE_GP'),
                      user=os.getenv('USER_GP'),
                      password=os.getenv('PASSWORD_GP')
                    )
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
    return conn