"""
В этом модуле содержатся конфигурационные настройки.
"""
import psycopg2 as ps, os

mail_pass = ''
username = ''
port = ""
db_name = ''
user_db = ''
password_db = ''
port_db = ''
host_db = ''
imap_server = "imap.yandex.ru"

with ps.connect(user=user_db, password=password_db, host=host_db, port=port_db, database=db_name) as conn:
    cur = conn.cursor()