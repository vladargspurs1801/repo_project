"""
В этом модуле реализованы конкретные примеры источников для получения данных. Все источники наследуют базовый интерфейс, определенный в
абстрактном суперклассе source_abc.DataSource.
"""

from source_abc import DataSource
from log.general_logger import MyCustomLogger
import erros_structure as err
import csv
import json
import os
import dotenv
import psycopg as ps
import psycopg.sql as ps_sql
import psycopg.rows as ps_row
import typing
import uuid
dotenv.load_dotenv()

class CSVSource(DataSource):
    """Подкласс, реализующий подключение к источнику csv и возвращение содержимого."""
    _logger = MyCustomLogger(p_logger_name='source_logger', p_file_name='source')

    def __init__(self, p_delimiter:str=','):
        """
        :param p_delimiter: - разделитель для csv.
        """
        self.file = os.getenv('path_file_csv') # Получаем имя файла.
        self.delimiter = p_delimiter # Получаем разделитель для csv.
        self.flg_open = False # Флаг, который мешает повторному открытию соединения.
        self.data_source = None
        self.columns = None # Столбцы источника для метаданных.
        self.data = None

    def connect(self):
        """Метод, открывающий соединение с источником csv."""
        self._logger.info('Начинаем подключение к источнику csv.')

        if not self.file:
            self._logger.error('Файл не задан в конфиге .env', exc_info=True)
            raise err.ConnectError(p_source_name='csv', p_msg='Файл не задан в конфиге .env')

        if not self.flg_open:
            self.data_source = open(file=self.file, encoding='UTF-8')
            self.flg_open = True
            self._logger.info('Подключение для csv выполнилось')

    def read(self) -> list[dict]:
        """
        Метод, реализующий чтение и возвращение содержимого файла.
        :return: - возвращает содержимое csv файла.
        """
        self._logger.info('Выполняем получение данных из csv.')

        if self.data is not None:
            return self.data

        if self.data_source is None or self.data_source.closed:
            self._logger.error('Файл закрыт. Чтение файла невозможно.', exc_info=True)
            raise err.ReadError(p_source_name='csv', p_msg='Файл закрыт. Чтение файла невозможно.')

        csv_dict_r = csv.DictReader(f=self.data_source, delimiter=self.delimiter)
        self.columns = csv_dict_r.fieldnames
        self.data = list(csv_dict_r)

        if not self.data:
            self._logger.warning('Источник пустой.', exc_info=True)
            raise err.ReadError(p_source_name='csv', p_msg='Источник пустой.')
        else:
            self._logger.info('Данные из csv получены успешно.')

        return self.data

    def close(self):
        """Метод, выполняющий закрытие соединения с источником csv."""
        if self.data_source is not None and not self.data_source.closed:
            self.data_source.close()
            self.flg_open = False
            self.data_source = None
            self._logger.info('Соединение с источником csv закрыто')
        else:
            self._logger.error('Попытка закрыть файл, который еще не был открыт.', exc_info=True)
            raise err.CloseError(p_source_name='csv', p_msg='Попытка закрыть файл, который еще не был открыт.')

    def metadata(self) -> dict:
        """
        :return: - возвращает описание источника.
        """
        return {'type':'csv', 'path':os.path.basename(self.file) if self.file else None, 'columns':[] if self.columns is None else self.columns}

    @property
    def name(self) -> str:
        """
        :return: - динамически возвращает имя источника.
        """
        return f'{os.path.basename(self.file) if self.file else "<unknown>"}'

class JSONSource(DataSource):
    """Подкласс, реализующий подключение к источнику json и возвращение содержимого."""
    _logger = MyCustomLogger(p_logger_name='source_logger', p_file_name='source')

    def __init__(self):
        self.file = os.getenv('path_file_json')
        self.flg_open = False
        self.data_source = None
        self.columns = None
        self.data = None

    def connect(self):
        """Метод, выполняющий подключение к источнику json"""
        self._logger.info('Выполняем подключение к истотчнику json.')

        if not self.file:
            self._logger.error('Файл не задан в конфиге .env', exc_info=True)
            raise err.ConnectError(p_source_name='json', p_msg='Файл не задан в конфиге .env')

        if not self.flg_open:
            self.data_source = open(file=self.file, encoding='UTF-8')
            self.flg_open = True
            self._logger.info('Подключение для json выполнилось')

    def read(self) -> list[dict]:
        """
        Метод, реализующий чтение и возвращение содержимого файла.
        :return: - возвращает содержимое json.
        """
        self._logger.info('Выполняем получение данных из json.')

        if self.data is not None:
            return self.data

        if self.data_source is None or self.data_source.closed:
            self._logger.error('Файл уже закрыт. Чтение файла невозможно.', exc_info=True)
            raise err.ReadError(p_source_name='json', p_msg='Файл уже закрыт. Чтение файла невозможно.')

        try:
            self.data = json.load(self.data_source)
        except json.decoder.JSONDecodeError:
            self._logger.warning('Передан пустой json.', exc_info=True)
            raise err.ReadError(p_source_name='json', p_msg='Передан пустой json.')

        if not isinstance(self.data, list):
            self._logger.warning(f'Ожидался list[dict], получен {type(self.data).__name__}', exc_info=True)
            raise err.ReadError(p_source_name='json', p_msg=f'Ожидался list[dict], получен {type(self.data).__name__}')
        if self.data and not all(isinstance(x, dict) for x in self.data):
            self._logger.warning('Не все элементы — словари', exc_info=True)
            raise err.ReadError(p_source_name='json', p_msg='Не все элементы — словари')

        if not self.data:
            self._logger.warning('Источник пустой.', exc_info=True)
            raise err.ReadError(p_source_name='json', p_msg='Источник пустой.')
        else:
            self._logger.info('Данные из json получены успешно.')

        self.columns = list(self.data[0].keys()) if self.data else []
        return self.data

    def close(self):
        """Метод, закрывающий соединение с источником json."""
        self._logger.info('Закрываем соединение с источником json.')
        if self.data_source is not None and not self.data_source.closed:
            self.data_source.close()
            self.flg_open = False
            self.data_source = None
            self._logger.info('Соединение с источником json закрыто')
        else:
            self._logger.error('Попытка закрыть файл, который еще не был открыт.', exc_info=True)
            raise err.CloseError(p_source_name='json', p_msg='Попытка закрыть файл, который еще не был открыт.')

    def metadata(self) -> dict:
        """
        :return: - возвращает описание источника.
        """
        return {'type': 'json', 'path':os.path.basename(self.file) if self.file else None, 'columns': [] if self.columns is None else self.columns}

    @property
    def name(self) -> str:
        """
        :return: - динамически возвращает имя источника.
        """
        return f'{os.path.basename(self.file) if self.file else "<unknown>"}'

class DBSource(DataSource):
    """Подкласс, реализующий подключение к источнику БД и возвращение содержимого таблицы через select."""
    _logger = MyCustomLogger(p_logger_name='source_logger', p_file_name='source')

    def __init__(self, p_table: str, p_owner: str):
        """
        :param p_table: - имя целевой таблицы-источника.
        :param p_owner: - имя схемы.
        """
        self.db_name = os.getenv('db_name')
        self.user = os.getenv('user_db')
        self.password = os.getenv('password_db')
        self.host = os.getenv('host')
        self.port = os.getenv('port')
        self.conn = None
        self.cur = None
        self.owner = p_owner
        self.table = p_table
        self.flg_open = False
        self.columns = None

    def connect(self):
        """Метод, выполняющий подключение к источнику БД."""
        self._logger.info('Выполняем подключение к БД')
        if not self.flg_open:
            try:
                if not all((self.db_name, self.user, self.password, self.host, self.port)):
                    self._logger.error('Не все конфиги для подключения к БД заполнены', exc_info=True)
                    raise err.ConnectError(p_source_name='db', p_msg='Не все конфиги для подключения к БД заполнены')

                self.conn = ps.connect(dbname=self.db_name, user=self.user, password=self.password, host=self.host, port=self.port)
                self.cur = self.conn.cursor(row_factory=ps_row.dict_row)
                self.flg_open = True
                self._logger.info('Подключение к БД выполнено')
            except ps.Error as db_err:
                self.conn = None
                self.cur = None
                self.flg_open = False
                self._logger.error('Подключение к БД завершилось с ошибкой.', exc_info=True)
                raise err.ConnectError(p_source_name='db', p_msg=f'Ошибка при создании соединения => {db_err}') from db_err

    def read(self) -> list[dict]:
        """
        Метод, реализующий чтение содержимого таблицы через select и возвращающий результат.
        :return: - возвращаем содержимое таблицы.
        """
        self._logger.info('Выполняем select к таблице.')

        if self.conn is None or self.conn.closed:
            self._logger.error('Соединение с базой закрыто или не установлено. Выполнять работу с БД нельзя.', exc_info=True)
            raise err.ReadError(p_source_name='db', p_msg='Соединение с базой закрыто или не установлено. Выполнять работу с БД нельзя.')
        if self.cur is None or self.cur.closed:
            self._logger.error('Курсор не создан или закрыт', exc_info=True)
            raise err.ReadError(p_source_name='db', p_msg='Курсор не создан или закрыт')

        try:
            query_get_columns = "SELECT column_name FROM information_schema.columns WHERE table_name = %s and table_schema = %s ORDER BY ordinal_position"
            self.cur.execute(query_get_columns, (self.table, self.owner))
            self.columns = [col['column_name'] for col in self.cur.fetchall()]
            if not self.columns:
                self._logger.error('Целевая таблица/схема не создана. Или неверно указана.', exc_info=True)
                raise err.ReadError(p_source_name='db', p_msg='Целевая таблица/схема не создана. Или неверно указана.')

            cols_sql = ps_sql.SQL(", ").join(ps_sql.Identifier(col) for col in self.columns)
            query = ps_sql.SQL("""SELECT {} FROM {}.{}""").format(cols_sql, ps_sql.Identifier(self.owner), ps_sql.Identifier(self.table))
            self.cur.execute(query)
            result_query = self.cur.fetchall()

            if not result_query:
                self._logger.warning('В целевой таблице нет данных.', exc_info=True)
                raise err.ReadError(p_source_name='db', p_msg='В целевой таблице нет данных.')

            self._logger.info('Данные таблицы получены.')
            return result_query

        except ps.Error as err_db:
            self._logger.error('При выполнении select произошла ошибка.', exc_info=True)
            raise err.ReadError(p_source_name='db', p_msg=f'Ошибка при выполнении select к таблице: {err_db}') from err_db

    def close(self):
        """Метод для закрытия подключения к БД."""
        self._logger.info('Закрываем соединение с БД.')

        if self.cur is not None and not self.cur.closed:
            self.cur.close()
            self.cur = None
            self._logger.info('Закрыли курсор')
        if self.conn is not None and not self.conn.closed:
            self.conn.close()
            self.conn = None
            self._logger.info('Закрыли соединение')
        else:
            self._logger.error('При закрытии соединения с БД произошла ошибка.', excinfo=True)
            raise err.CloseError(p_source_name='db', p_msg='Попытка закрыть соединение с БД, которое еще не было открыто.')

        self.flg_open = False

    def metadata(self) -> dict:
        """
        :return: - возвращает описание источника.
        """
        return {'type': 'db', 'owner_table': (self.owner, self.table) if all((self.owner, self.table)) else None, 'columns': [] if self.columns is None else self.columns}

    @property
    def name(self) -> str:
        """
        :return: - динамически возвращает имя источника.
        """
        return f'{(self.owner,self.table) if all((self.owner, self.table)) else "<unknown>"}'

class CompositeSource(DataSource):
    """
    Этот класс:
    1. Объединяет получение данных из нескольких источников в единый поток данных.
    2. Не выполняет чтение данных сам. Он делегирует это переданным источникам.
    3. Он работает с каждым источником как с автономным инструментом. Он не знает их внутреннюю реализацию.
    """
    _logger = MyCustomLogger(p_logger_name='source_logger', p_file_name='source')

    def __init__(self, p_sources: list[DataSource], *, p_target_fields: typing.Optional[set[str]]=None, p_name: str=f'composite_{uuid.uuid4().hex[:8]}'):
        """
        :param p_sources: - это набор источников.
        :param p_target_fields: - это список обязательных столбцов для всех источников.
        :param p_name: - это имя объединенного источника.
        """
        self._name = p_name
        self._sources = p_sources
        self.flg_open = False
        self._composite_data = []
        self.target_fields = p_target_fields
        self.all_fields = set() # Для хранения всех столбцов полученных данных.
        self._num_pipeline = uuid.uuid4().hex[:8]

    def connect(self):
        """
        Он не выполняет подключение. Он делегирует операцию подключения переданным источникам.
        """
        self._logger.info(f'Выполняем подключение к источникам контейнера {self._name}')

        try:
            if not self._sources:
                self._logger.error('Для работы контейнера нужно передать хотя бы один источник.', exc_info=True)
                raise err.ConnectError(p_source_name=self._name, p_msg='Для работы контейнера нужно передать хотя бы один источник.')

            if not all([isinstance(obj, DataSource) for obj in self._sources]):
                self._logger.error('Для корректной работы контейнера нужно, чтобы каждый переданный источник поддерживал интерфейс DataSource.', exc_info=True)
                raise err.ConnectError(p_source_name=self._name, p_msg='Для корректной работы контейнера нужно, чтобы каждый переданный источник поддерживал интерфейс DataSource.')

            # Повторное подключение не должно выполнять подключение.
            # Выполняем подключение для каждого источника.
            if not self.flg_open:
                    for source in self._sources:
                        try:
                            source.connect()
                        except (err.SourceException, OSError) as err_con:
                            err_obj_con = err.SourceError(
                                                                     source_name=str(source),
                                                                     stage=err.SourceErrorStage.CONNECT,
                                                                     exception_type=err_con.__class__.__name__,
                                                                     message=str(err_con)
                                                                   )
                            if err_obj_con.severity in ('error', 'warning'):
                                self.log_error(err_obj_con)
                            continue
                    self.flg_open = True

        except err.SourceException as err_source:
            err_obj = err.SourceError(
                                                source_name=self._name,
                                                stage=err.SourceErrorStage.CONNECT,
                                                exception_type=err_source.__class__.__name__,
                                                message=str(err_source),
                                                severity=err.SourceErrorSeverity.CRITICAL
                                             )
            self.flg_open = False
            self.log_error(err_obj)
            self._logger.critical('Критическая остановка работы pipeline.', exc_info=True)
            if err_obj.severity == 'critical':
                raise RuntimeError('Критическая остановка работы pipeline.')

    def read(self) -> list[dict]:
        """
        CompositeSource НЕ получает данные из источников сам. Он делегирует это полученным источникам.
        :return: - возвращает данные из всех переданных источников. В случае возникновения ошибки возвращает пустой список. Это нужно для соответствия
        аннотации в возвращаемом типе абстрактного базового суперкласса-интерфейса.
        """
        self._logger.info(f'Выполняем получение данных из источников контейнера {self._name}')

        try:
            # Получение данных не должно выполняться перед созданием подключения.
            if not self.flg_open:
                self._logger.error('Получение данных в контейнере не должно выполняться перед созданием подключения.', exc_info=True)
                raise err.ReadError(p_source_name=self._name, p_msg='Получение данных в контейнере не должно выполняться перед созданием подключения.')

            # При повторном запуске должны быть возвращены данные, полученные во время первого запуска.
            if self._composite_data:
                return self._composite_data

            for source in self._sources:
                try:
                    data = source.read() # Данные, полученные из источника.
                    self.check_fields(p_source=source, p_data=data, p_required_fields=self.target_fields)
                    self._composite_data.extend(data) # Добавляем данные из источника.
                except err.SourceException as err_read:
                    err_obj_read = err.SourceError(
                                                                source_name=str(source),
                                                                stage=err.SourceErrorStage.READ,
                                                                exception_type=err_read.__class__.__name__,
                                                                message=str(err_read)
                                                            )
                    if err_obj_read.severity in ('error', 'warning'):
                        self.log_error(err_obj_read)
                    continue

            if not self._composite_data:
                self._logger.error('Контейнер не получил данные.', exc_info=True)
                raise err.ReadError(p_source_name=self._name, p_msg='Контейнер не получил данные.')

            # Добавляем к данным недостающие столбцы со значениями None.
            for row in self._composite_data:
                self.update_data_records(p_record=row, p_all_fields=self.all_fields)

            return self._composite_data
        except err.SourceException as err_source:
            err_obj = err.SourceError(
                                                    source_name=self._name,
                                                    stage=err.SourceErrorStage.READ,
                                                    exception_type=err_source.__class__.__name__,
                                                    message=str(err_source),
                                                    severity=err.SourceErrorSeverity.CRITICAL
                                                )
            self.log_error(err_obj)
            self._logger.critical('Критическая остановка работы pipeline.', exc_info=True)
            if err_obj.severity == 'critical':
                raise RuntimeError('Критическая остановка работы pipeline.')
            return []

    def check_fields(self, p_source: DataSource, p_data: list[dict], p_required_fields: typing.Optional[set[str]]):
        """
        Метод, который выполняет проверку на наличие в данных источника обязательных столбцов.
        :param p_source: - это источник.
        :param p_data: - это данные источника.
        :param p_required_fields: - это обязательные столбцы, которые должен содержать каждый источник.
        """
        try:
            if not p_data:
                self._logger.error(f'Источник {p_source.name} пустой', exc_info=True)
                raise err.ReadError(p_source_name=self._name, p_msg=f'Источник {p_source.name} пустой')

            fields = p_data[0].keys()  # Столбцы, которые содержит источник.
            # Проверка, что источник содержит обязательные столбцы.
            if p_required_fields is not None:
                diff_field = p_required_fields.difference(fields)
                if diff_field:
                    self._logger.error(f'Данные из источника {p_source} не содержат обязательные столбцы: {diff_field}', exc_info=True)
                    raise err.CheckFieldError(p_source_name=self._name, p_msg=f'Данные из источника {p_source} не содержат обязательные столбцы: {diff_field}')

            self.all_fields.update(fields)  # Получаем все столбцы.
        except err.CheckFieldError as err_check:
            err_obj = err.SourceError(
                                                    source_name=str(p_source),
                                                    stage=err.SourceErrorStage.READ,
                                                    exception_type=err_check.__class__.__name__,
                                                    message=str(err_check),
                                                    severity=err.SourceErrorSeverity.CRITICAL
                                                 )
            self.log_error(err_obj)
            self._logger.critical('Критическая остановка работы pipeline.', exc_info=True)
            if err_obj.severity == 'critical':
                raise RuntimeError('Критическая остановка работы pipeline.')

    @staticmethod
    def update_data_records(p_record: dict, p_all_fields: set):
        """
        Метод, который дополняет данные недостающими столбцами со значением None.
        :param p_record: - это запись из данных.
        :param p_all_fields: - это столбцы, которые содержат все источники.
        """
        upd_field = p_all_fields.difference(p_record.keys())  # Столбцы, которых нет в данных из источника.
        p_record.update({field: None for field in upd_field})  # Эти столбцы будут добавлены со значением None.

    def close(self):
        """
        Контейнер не закрывает соединение сам. Он делегирует это переданным источникам.
        """
        self._logger.info(f'Закрываем соединение с источниками контейнера {self._name}.')
        try:
            if not self.flg_open:
                self._logger.error('У источников контейнера еще не было открыто соединение. Нельзя их закрыть.', exc_info=True)
                raise err.CloseError(p_source_name=self._name, p_msg='У источников контейнера еще не было открыто соединение. Нельзя их закрыть.')

            for source in self._sources:
                try:
                    source.close()
                except err.SourceException as err_close:
                    err_obj_close = err.SourceError(
                                                                source_name=str(source),
                                                                stage=err.SourceErrorStage.CLOSE,
                                                                exception_type=err_close.__class__.__name__,
                                                                message=str(err_close)
                                                             )
                    if err_obj_close.severity in ('error', 'warning'):
                        self.log_error(err_obj_close)
                    continue

            self.flg_open = False

        except err.SourceException as err_source:
            err_obj = err.SourceError(
                                                    source_name=self._name,
                                                    stage=err.SourceErrorStage.CLOSE,
                                                    exception_type=err_source.__class__.__name__,
                                                    message=str(err_source),
                                                    severity=err.SourceErrorSeverity.CRITICAL
                                                )
            self.log_error(err_obj)
            if err_obj.severity == 'critical':
                self._logger.critical('Критическая остановка работы pipeline.', exc_info=True)
                raise RuntimeError('Критическая остановка работы pipeline.')

    def metadata(self) -> dict:
        """:return: - возвращает описание источника."""
        return {
                  'type': 'composite',
                  'name': self._name,
                  'source': [src.metadata() for src in self._sources],
                  'columns': self.all_fields if self.all_fields else None
               }

    @property
    def name(self) -> str:
        """
        Свойство, которое динамически возвращает имя источника. Обладает только геттером.
        """
        return f"{self._name}: {', '.join(source.name for source in self._sources)}"

    def log_error(self, p_error_obj: err.SourceError):
        """
        Метод для записи ошибок с категориями warning, error, critical в отдельный файл. Будет записана ошибка со структурой erros_structureюSourceError.
        Каждая сериализованная ошибка представляет собой строку-json. Сериализация будет выполняться в файл с расширением jsonl.
        :param p_error_obj: - это объект сгенерированного пользовательского исключения.
        """
        file_path = os.getenv('dir_log')

        error_items = {
                         'source_name':p_error_obj.source_name,
                         'stage':p_error_obj.stage.value,
                         'exception_type':p_error_obj.exception_type,
                         'message':p_error_obj.message,
                         'severity':p_error_obj.severity.value
                     }

        os.makedirs(file_path, exist_ok=True)

        with open(file=os.path.join(file_path, f'log_error_{self._num_pipeline}.jsonl'), mode='a', encoding='utf-8') as f_w:
            f_w.write(json.dumps(obj=error_items, ensure_ascii=False) + '\n')
