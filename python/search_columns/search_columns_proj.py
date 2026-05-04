"""
Модуль search_columns_proj.py.
В этом модуле написана программа, которая помогает выполнять миграцию объектов (таблиц и представлений) из СУБД GreenPlum в СУБД Postgresql.
В программе выполняется сверка столбцов и их типов данных таблиц и представлений из обеих СУБД, введенных пользователем.
Результат сверки записывается в файл эксель, который в качестве вложения прикладывается к электронному письму Outlook. Электронное письмо отправляется
указанным адресатам. Каждый инструмент реализуется через отдельный класс. И затем с применением композиции все инструменты внедряются в общий класс,
реализуя тем самым интерфейс программы. Я старался при написании каждого инструмента соблюдать принципы SOLID.
"""
from abc import ABC, abstractmethod
import psycopg2 as ps
import pandas as pd
import win32com.client as win32
from pywintypes import com_error
from user_logging.general_logger import MyCustomLogger
from logging import Logger
import os, re
from db_connection import greenplum_conn, postgres_conn

class AbcDatabaseData(ABC):
    """Этот абстрактный суперкласс будет определять способ получения и обработки данных, полученных их СУБД."""
    def __init__(self, p_cur):
        self.cur = p_cur

    @abstractmethod
    def get_data(self): pass

class DatabaseDataGp(AbcDatabaseData):
    """Класс для получения и обработки данных, полученных из СУБД GreenPlum."""
    def __init__(self, p_cur, p_owner_name:str, p_table_name:str, p_logger:Logger):
        AbcDatabaseData.__init__(self, p_cur)
        self.__owner_name = p_owner_name
        self.__table_name = p_table_name
        self._logger = p_logger

    def get_data(self) -> dict:
        """
        Метод отправляет select запрос на выполнение СУБД GreenPlum. В select выполняется обращение к метаданным information_schema.columns для получения
        столбцов с типами, относящихся к указанной пользователем таблицы или представления. Выполняется обработка данных.
        """
        try:
            self._logger.info("Начинаем выполнять select с обращением к метаданным объекта в GreenPlum.")

            query = """SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s and table_name = %s"""
            self.cur.execute(query, [self.__owner_name, self.__table_name])
            gp_data = {column_name:data_type for column_name, data_type in self.cur.fetchall()}

            self._logger.info("Метаданные GreenPlum получены успешно.")
            return gp_data

        except ps.DataError:
            self._logger.error("Ошибка в получении данных из GreenPlum.", exc_info=True)
        except ps.DatabaseError:
            self._logger.error("Ошибка в работе GreenPlum.", exc_info=True)
        except KeyError:
            self._logger.error("Ошибка в обработке данных.", exc_info=True)
        except Exception:
            self._logger.error("Прочая ошибка.", exc_info=True)

class DatabaseDataPg(AbcDatabaseData):
    """Класс для получения и обработки данных, полученных из СУБД PostgresSQL."""
    def __init__(self, p_cur, p_owner_name:str, p_table_name:str, p_logger:Logger):
        AbcDatabaseData.__init__(self, p_cur)
        self.__owner_name = p_owner_name
        self.__table_name = p_table_name
        self._logger = p_logger

    def get_data(self) -> dict:
        """
        Метод отправляет select запрос на выполнение СУБД PostgresSQL. В select выполняется обращение к метаданным information_schema.columns для получения
        столбцов с типами, относящихся к указанной пользователем таблицы или представления. Выполняется обработка данных.
        """
        try:
            self._logger.info("Начинаем выполнять select с обращением к метаданным объекта в PostgresSQL.")

            query = """SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s and table_name = %s"""
            self.cur.execute(query, [self.__owner_name, self.__table_name])
            gp_data = {column_name:data_type for column_name, data_type in self.cur.fetchall()}

            self._logger.info("Метаданные PostgresSQL получены успешно.")
            return gp_data

        except ps.DataError:
            self._logger.error("Ошибка в получении данных из PostgresSQL.", exc_info=True)
        except ps.DatabaseError:
            self._logger.error("Ошибка в работе PostgresSQL.", exc_info=True)
        except KeyError:
            self._logger.error("Ошибка в обработке данных.", exc_info=True)
        except Exception:
            self._logger.error("Прочая ошибка.", exc_info=True)

class AbcSearchColumn(ABC):
    """
    Абстрактный суперкласс, который представляет собой абстрактную оболочку для создания инструментов по сверке атрибутного состава (столбцы и их типы
    данных) таблиц и представлений.
    """
    def __init__(self, p_gp_attribute, p_pg_attribute):
        self.gp_attribute = p_gp_attribute
        self.pg_attribute = p_pg_attribute

    @abstractmethod
    def get_lose_columns(self): pass

class SearchColumn(AbcSearchColumn):
    """
    Класс реализует инструмент сверки атрибутного состава (столбцы и их типы данных) таблицы и представлений из СУБД GreenPlum и PostgresSQL. И записывает
    результат сверки в Excel файл.
    """
    def __init__(self, p_gp_attribute:dict, p_pg_attribute:dict, p_logger:Logger):
        AbcSearchColumn.__init__(self, p_gp_attribute, p_pg_attribute)
        self.file_path = os.path.join(os.path.dirname(os.path.abspath((__file__))), 'lost_cols.xlsx')
        self._logger = p_logger

    def get_lose_columns(self):
        """
        Метод выполняет сверку атрибутного состава (столбцы и их типы данных) таблиц и представлений из СУБД GreenPlum И PostgresSQL. Результат сверки
        представляет собой наборы недостающих столбцов и их типов, которые есть в таблице или представлении GreenPlum, но отсутствуют в таблице или
        представлении PostgresSQL. Затем списки со столбцами и их типами данных записываются в файл Excel.
        """
        try:
            self._logger.info('Начинаем сверку таблицы или представления из GreenPlum с PostgresSQL.')

            diff_cols = self.gp_attribute.items() - self.pg_attribute.items()
            lost_cols = []
            cols_type = []

            for col, data_type in diff_cols:
                lost_cols.append(col)
                # Приводим типы данных столбцов в удобочитаемый и информативный вид.
                match data_type:
                    case x if x == 'bigint':
                        cols_type.append('int8')
                    case x if x == 'smallint':
                        cols_type.append('int2')
                    case x if x == 'integer':
                        cols_type.append('int4')
                    case x if x == 'character varying':
                        cols_type.append('varchar')
                    case _:
                        cols_type.append(data_type)

            df = pd.DataFrame(data={'ColumnNme':lost_cols, 'DataType':cols_type})

            with pd.ExcelWriter(path=self.file_path, engine='xlsxwriter') as writer_excel:
                df.to_excel(excel_writer=writer_excel, sheet_name='Result', index=False)

                # Получаем доступ к вкладке excel файла.
                worksheet = writer_excel.sheets['Result']

                # Получаем количество строк и столбцов в датафрейме.
                (max_row, max_col) = df.shape

                # Создаем фильтр на таблицу.
                worksheet.autofilter(0, 0, max_row, max_col-1)
            self._logger.info('Сверка таблиц выполнена')

        except IOError:
            self._logger.error('Ошибка в создании excel файла', exc_info=True)
        except ValueError:
            self._logger.error('Ошибка в записи значений в excel файл', exc_info=True)
        except Exception:
            self._logger.error("Прочая ошибка.", exc_info=True)

class AbcEmailMessage(ABC):
    """
    Этот абстрактный суперкласс выступает в качестве абстрактной оболочки для реализации инструмента по созданию и отправке электронного письма.
    """
    def __init__(self, p_emails:str):
        self.emails = re.split(pattern=r"(?:\s|,|;)\s*", string=p_emails)

    @abstractmethod
    def send_email(self): pass

class EmailMessage(AbcEmailMessage):
    """Класс, который создает инструмент для формирования и отправки электронного письма почты Outlook."""
    def __init__(self, p_emails:str, p_logger:Logger):
        AbcEmailMessage.__init__(self, p_emails)
        self._logger = p_logger

    def send_email(self, p_owner_gp:str, p_table_gp:str, p_owner_pg:str, p_table_pg:str, p_attach:str):
        """Метод создает электронное письмо с файлом Excel в качестве вложения. И отправляет это письмо указанным получателям."""
        try:
            self._logger.info('Подключаемся к Outlook. Создаем электронное письмо.')

            outlook = win32.Dispatch('Outlook.Application')
            newmail = outlook.CreateItem(0)
            newmail.Subject = f'Недостающие столбцы в таблице {p_owner_pg} в СУБД PostgresSQL.'
            newmail.Body = f"""Привет.
                               В файле хранятся недостающие столбцы с типами данных, которые есть в {p_owner_gp}.{p_table_gp} в GreenPlum.
                               Но нет в {p_owner_pg}.{p_table_pg} в PostgresSQL.
                            """

            newmail.To = self.emails
            newmail.Attachments.Add(p_attach)
            newmail.Send()

            self._logger.info(f'Электронное письмо создано и отправлено получателям => {self.emails}.')

        except com_error:
            self._logger.error("Ошибка в работе с Microsoft Outlook.", exc_info=True)
        except re.PatternError:
            self._logger.error("Ошибка в получении адресатов электронных почт.", exc_info=True)
        except Exception:
            self._logger.error("Прочая ошибка.", exc_info=True)

class MigrationObjects:
    """
    Класс реализует программу для миграции таблиц и представлений из СУБД GreenPlum в СУБД PostgresSQL. Класс создает свой интерфейс путем внедрения
    других объектов.
    """
    def __init__(self, p_emails:str, p_gp_owner:str, p_gp_table:str, p_pg_owner:str, p_pg_table:str):
        try:
            self.emails = p_emails
            self.gp_owner = p_gp_owner
            self.gp_table = p_gp_table
            self.pg_owner = p_pg_owner
            self.pg_table = p_pg_table

            # Для логгирования.
            self._logger = MyCustomLogger(p_logger_name='column_logger', p_file_name='search_column.log')

        except Exception:
            self._logger.error('Ошибка в инициализации управляющего класса', exc_info=True)

    def scan_columns(self):
        """Метод реализует интерфейс программы по миграции таблиц и представлений из СУБД GreenPlum в СУБД PostgresSQL."""
        try:
            self._logger.info('Начинаем создавать интерфейс программы по миграции таблиц и представлений.')

            # Выполняем подключение к PostgresSQL.
            with postgres_conn() as pg_conn:
                # Получаем результат запроса обращения к метаданным таблицы или представления PostgresSQL.
                pg_columns_obj = DatabaseDataPg(p_cur=pg_conn.cursor(), p_owner_name=self.pg_owner, p_table_name=self.pg_table, p_logger=self._logger)
                pg_attribute = pg_columns_obj.get_data()

            # Выполняем подключение к GreenPlum.
            with greenplum_conn() as gp_conn:
                # Получаем результат запроса обращения к метаданным таблицы или представления GreenPlum.
                gp_columns_obj = DatabaseDataGp(p_cur=gp_conn.cursor(), p_owner_name=self.gp_owner, p_table_name=self.gp_table, p_logger=self._logger)
                gp_attribute = gp_columns_obj.get_data()

            # Для выполнения сверки таблиц или представлений обеих СУБД.
            search_obj = SearchColumn(p_gp_attribute=gp_attribute, p_pg_attribute=pg_attribute, p_logger=self._logger)
            search_obj.get_lose_columns()

            # Создаем и отправляем получателям электронное письмо.
            email_obj = EmailMessage(p_emails=self.emails, p_logger=self._logger)
            email_obj.send_email(p_attach=search_obj.file_path, p_owner_gp=self.gp_owner, p_table_gp=self.gp_table, p_owner_pg=self.pg_owner,
                                 p_table_pg=self.pg_table)

            self._logger.info('Интерфейс программы по миграции таблиц и представлений создан.')

        except Exception:
            self._logger.error('Ошибка в создании интерфейса программы по миграции объектов', exc_info=True)
