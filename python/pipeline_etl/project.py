import psycopg as ps
import psycopg.sql as ps_sql
import pydantic
import datetime as dt
import enum
import re
import csv
import os
import operator as op
import itertools as it
import dotenv
import log.general_logger as log
from structure_data.structure import Structure

def get_path_env() -> str:
    """
    Функция для создания файлового пути к env конфигу.
    :return: - возвращает файловый путь к env конфигу.
    """
    for item in os.listdir():
        if item == 'config' and os.path.isdir(item):
            return os.path.join(os.getcwd(),item, ".env")

dotenv.load_dotenv(get_path_env())

class WorkDb(Structure):
    """
    Класс, в котором выполняется работа в БД Postgres.
    """
    _logger = log.MyCustomLogger('pipeline_logger', 'pipeline') # Для логирования
    _fields = ['table_core', 'table_stg', 'schema']
    db_name = os.getenv('db_name')
    user = os.getenv('user_db')
    password = os.getenv('password_db')
    host = os.getenv('host')
    port = os.getenv('port')

    def __enter__(self):
        """
        Один из двух обязательных методов для поддержки протокола диспетчера контекста. Отслеживает вход в оператор with.
        Возвращает свой же экземпляр.
        """
        self._logger.info('Начинаем подключение к Postgres.')
        try:
            self.conn = ps.connect(dbname=self.db_name, user=self.user, password=self.password, host=self.host, port=self.port)
            self.conn.autocommit = False
            self.cur = self.conn.cursor()
            self._logger.info('Подключение к Postgres выполнили')
            return self
        except ps.OperationalError as db_err:
            self._logger.error('Ошибка с подключением к Postgres', exc_info=True)
            raise ps.OperationalError('Ошибка с подключением к Postgres') from db_err

    def get_date_modify_file(self, p_file_name:str) -> tuple[str]:
        """
        Метод для получения даты и времени модификации файла из watermark.
        :param p_file_name: - это имя файла.
        :return: - это дата и время модификации файла.
        """
        self._logger.info('Получаем timestamp изменения файла из watermark.')
        query = """SELECT modified_file FROM PUBLIC.STORAGE_LOAD_FILE WHERE FILE_NAME = %s"""
        self.cur.execute(query, (p_file_name,))
        return self.cur.fetchone()

    def load_watermark(self, p_file_name:str, p_timestamp_modify_file:dt.datetime, p_date_operation:dt.date=dt.datetime.now().date()):
        """
        Метод для вставки новой записи или обновления существующей в watermark.
        :param p_file_name: - это имя файла для загрузки записей.
        :param p_timestamp_modify_file: - это дата и время модификации файла для загрузки записей.
        :param p_date_operation: - это дата, когда выполняется работа с watermark.
        """
        self._logger.info('Загружаем информацию об обновлении файла в watermark.')
        query = """
                INSERT INTO PUBLIC.STORAGE_LOAD_FILE (file_name, modified_file, date_operation) VALUES (%s, %s, %s)
                ON CONFLICT (file_name) DO UPDATE
                SET modified_file = EXCLUDED.modified_file,
                    date_operation = EXCLUDED.date_operation
                """

        self.cur.execute(query, (p_file_name, p_timestamp_modify_file, p_date_operation))
        self._logger.info('Информация об обновлении файла добавлена в watermark.')

    def load_table_stg(self, p_rows:list[dict]):
        """
        Метод для очистки и массовой загрузки записей в промежуточную таблицу в слое stg. Метод copy используется в целях сохранения производительности,
        поскольку будет загружено много записей.
        :param p_rows: - это записи для массовой загрузки.
        """
        #self.rows = p_rows
        if not p_rows:
            self._logger.warning('Нет записей для вставки')
            return
        else:
            query = ps_sql.SQL("""truncate table {}.{}""").format(ps_sql.Identifier(self.schema),
                                                                  ps_sql.Identifier(self.table_stg))
            self._logger.info(f'Начинаем очищать содержимое таблицы {self.schema}.{self.table_stg}')
            self.cur.execute(query)
            self._logger.info('Содержимое таблицы очищено')

            columns = list(p_rows[0].keys())
            cols_sql = ps_sql.SQL(", ").join(ps_sql.Identifier(col) for col in columns)

            self._logger.info('Начинаем выполнять массовую вставку')
            with self.cur.copy(ps_sql.SQL("COPY {}.{} ({}) FROM STDIN").format(ps_sql.Identifier(self.schema), ps_sql.Identifier(self.table_stg), cols_sql)) as copy:
                for row in p_rows:
                    copy.write_row(tuple(row[col] for col in columns))
            self._logger.info('Выполнили массовую вставку')

    def load_table_core(self, p_unique_column):
        """
        Метод для загрузки записей в целевую таблицу в слое core. Для загрузки используется конструкция insert ... select ... on conflict ...do update
        для поддержки идемпотентности.
        :param p_unique_column: - это ключ, по которому будет выполняться обновление существующих записей в целевой core таблицы во избежание дубликатов.
        """
        query_get_columns = """SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s"""
        self.cur.execute(query_get_columns, (self.table_core, self.schema))
        columns = [col[0] for col in self.cur.fetchall()]

        if not columns:
            self._logger.warning('Целевая таблица в слое core не создана')
        else:
            self._logger.info('Начинаем заполнять целевую таблицу в слое core.')

            cols_sql = ps_sql.SQL(", ").join(ps_sql.Identifier(col) for col in columns)
            columns.pop(columns.index('order_id')) # Мы исключаем уникальный столбец order_id из выражения присваивания set в update.

            # Для поддержки универсальности: программа должна работать с любой таблицей и разным атрибутным составом.
            set_upd = ', '.join(['{} = EXCLUDED.{}'.format(col, col) for col in columns])
            query_load = ps_sql.SQL("""
                                    INSERT INTO {owner_core}.{table_core} ({cols_core})
                                    SELECT {cols_stg} FROM {owner_stg}.{table_stg}
                                    ON CONFLICT ({unique_column})
                                    DO UPDATE
                                    set {upd_assignment}
                                    """).format(owner_core=ps_sql.Identifier(self.schema),
                                                table_core=ps_sql.Identifier(self.table_core),
                                                cols_core=cols_sql,
                                                cols_stg=cols_sql,
                                                owner_stg=ps_sql.Identifier(self.schema),
                                                table_stg=ps_sql.Identifier(self.table_stg),
                                                unique_column=ps_sql.Identifier(p_unique_column),
                                                upd_assignment=ps_sql.SQL(set_upd)
                                                )

            self.cur.execute(query_load)

            self._logger.info('Целевая таблица в слое core заполнена.')

    def __exit__(self, ex_type, ex_val, tb):
        """
        Второй из двух обязательных методов для поддержки протокола диспетчера контекста. Отслеживает выход из оператора with.
        :param ex_type: - это тип исключения.
        :param ex_val: - это значение исключения.
        :param tb: - это трассировка стека.
        """
        try:
            if ex_type is None:
                self._logger.info('Работа с базой проведена без ошибок. Сохраняем изменения.')
                self.conn.commit()
            else:
                self._logger.error('В работе с базой возникла ошибка. Откатываем изменения.', exc_info=True)
                self.conn.rollback()
        finally:
                self._logger.info('Закрываем соединение.')
                self.conn.close()

        return False

class StatusCheck(str, enum.Enum):
    """
    Класс используется для перечисления всех доступных статусов заказа. Если входные записи будут содержать другой статус, такая запись будет считаться
    невалидной.
    """
    completed = 'completed'
    shipped = 'shipped'
    transit = 'transit'

class CheckTypeModel(pydantic.BaseModel):
    """
    Класс-модель для валидации входных значений.
    Валидируем:
    1. Пропуски.
    2. Некорректные даты.
    3. Регистры.
    4. Лишние пробелы.
    В декораторах-валидаторах используем режим 'before', чтобы декораторы-валидаторы могли редактировать входящие значения в процессе валидации до аннотации.
    Затем будет выполняться валидации типов с помощью аннотаций.
    """
    order_id: int = pydantic.Field(gt=0, description='ID заказа')
    order_date: dt.date = pydantic.Field(gt=dt.date(year=2000, month=12, day=31) ,description='дата заказа')
    customer_id: str = pydantic.Field(description='ID клиента')
    product_name: str = pydantic.Field(description='Название товара')
    category: str = pydantic.Field(default='Прочее', description='Категория товара')
    quantity: int = pydantic.Field(description='Количество товаров')
    price: int|float = pydantic.Field(gt=0, description='Цена за единицу')
    country: str = pydantic.Field(pattern=r'[А-ЯA-Z]\w*', description='Страна')
    status: StatusCheck = pydantic.Field(description='Статус заказа')

    # Ниже определим дополнительные валидаторы для входящих значений
    @pydantic.field_validator('order_date', mode='before')
    @classmethod
    def validate_order_date(cls, p_value:str) -> dt.date:
        if p_value:
            pat = re.compile(pattern=r'-|\.|:|/')
            if re.search(pattern=r'\d{4}(-|\.|:|/)\d*(-|\.|:|/)\d*', string=p_value):
                date_obj = dt.date(*[int(item) for item in pat.split(string=p_value)])
            elif re.search(pattern=r'\d*(-|\.|:|/)\d*(-|\.|:|/)\d{4}', string=p_value):
                day, month, year = pat.split(string=p_value)
                date_obj = dt.date(year=int(year), month=int(month), day=int(day))
            else:
                raise ValueError(f'Перед неверный формат даты: {p_value}')

            if date_obj.month > 12 or date_obj.day > 31:
                raise ValueError(f'Неверная дата: {date_obj}')

            return date_obj

    @pydantic.field_validator('country', mode='before')
    @classmethod
    def validate_country(cls, p_value:str) -> str:
        if p_value:
            thirst_al = p_value[0].upper()
            return thirst_al + p_value[1:]

    @pydantic.field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, p_value:str) -> str:
        if p_value: return p_value.lower()

    @pydantic.field_validator('product_name', mode='before')
    @classmethod
    def validate_product_name(cls, p_value:str) -> str:
        if p_value: return p_value.strip()

    @pydantic.field_validator('customer_id', mode='before')
    @classmethod
    def validate_customer_id(cls, p_value:str) -> str:
        if p_value: return p_value.strip()

    @pydantic.field_validator('category', mode='before')
    @classmethod
    def validate_category(cls, p_value: str) -> str:
        if p_value: return p_value.strip()

class CsvWork(Structure):
    """
    Этот класс будет выполнять работу с csv.
    """
    _logger = log.MyCustomLogger('pipeline_logger', 'pipeline') # Для логирования
    _fields = ['Validation_model']
    success_row_thirst_validation = []
    success_row_second_validation = []
    _failed_row = {}

    def validation_csv(self, p_path, p_group_field):
        """
        Выполняет несколько этапов валидации входящих записей.
        Этап 1 -> с использованием модели pydantic.
        Этап 2 -> удаление дубликатов с использованием предварительной сортировки и последующей группировки. Валидной будет считаться последняя запись в
        дублирующейся группе.
        :param p_path: - это путь до исходного файла csv для загрузки.
        :param p_group_field: - это ключ-поле, по которому будет выполняться сортировка и группировка записей для исключения дубликатов.
        """
        self.success_row_thirst_validation.clear()
        self.success_row_second_validation.clear()
        # Этап 1 -> с использованием модели pydantic.
        self._logger.info('выполняем 1 этап валидации')
        with open(file=p_path, encoding='UTF-8') as f_r:
            dct_r = csv.DictReader(f_r, delimiter=',') # Разделитель-запятая используется по умолчанию. Потом убрать.
            # Сноска: использование Pydantic ввиду n-го создания экземпляров во время итераций неэффективный подход. Но я его применил из соображений
            # любопытства, эксперимента и интереса. Для прода я бы использовал проверки на основе паттерна CheckColumn, CheckResult с использованием
            # dataframe pandas, а именно выполнял бы векторно операции на pandas.Series.
            for row in dct_r:
                try:
                    self.Validation_model(**row)
                    self.success_row_thirst_validation.append(row)
                except pydantic.ValidationError as val_err:
                    error_info = val_err.errors()
                    column_error = error_info[0]['loc']
                    msg = error_info[0]['msg']
                    self._failed_row[(column_error[0], msg)] = row
        self._logger.info('Первый этап валидации выполнен.')

        # Этап 2 -> валидация дубликатов.
        self._logger.info('выполняем 2 этап валидации')
        self.success_row_thirst_validation.sort(key=op.itemgetter(p_group_field))
        for key_group, rows in it.groupby(iterable=self.success_row_thirst_validation, key=op.itemgetter(p_group_field)):
            last_row = list(rows)[-1]
            self.success_row_second_validation.append(last_row)
        self._logger.info('Второй этап валидации выполнен')

class Main:
    """
    Главный класс. Применим композицию для выполнения работы по загрузке записей.
    """
    _logger = log.MyCustomLogger('pipeline_logger', 'pipeline') # Для логирования

    def __init__(self, p_check_model, p_owner, p_table):
        """
        Применяем композицию для внедрения экземпляров ранее определенных классов. Каждый экземпляр будет выполнять строго отведенную иму роль.
        Атрибут _storage_file будет сохранять историю загруженных файлов.
        :param p_check_model: - это модель Pydantic для выполнения валидации.
        :param p_owner: - это схема таблицы.
        :param p_table: - это имя таблицы.
        """
        self.table_core = p_table + '_core'
        self.table_stg = p_table + '_stg'
        self.obj_sql = WorkDb(schema=p_owner, table_stg=self.table_stg, table_core=self.table_core)
        self.obj_csv = CsvWork(Validation_model=p_check_model)
        self.owner = p_owner

    def work(self, p_path, p_field_group, p_field_unique):
        """
        Метод для выполнения всей работы по загрузке записей в целевую таблицу.
        :param p_path: - это путь до исходного файла с записями.
        :param p_field_group: - это ключ-поле, по которому будет выполняться сортировка и группировка записей для исключения дубликатов.
        :param p_field_unique: - это ключ, по которому будет выполнять insert select on conflict do update.
        """
        self._logger.info('Проверяем, был ли ранее загружен файл')
        with self.obj_sql as db:
            file_name = os.path.basename(p_path)
            timestamp_modify_program = dt.datetime.fromtimestamp(os.path.getmtime(p_path))
            timestamp_modify_watermark = db.get_date_modify_file(p_file_name=file_name)

            if (not timestamp_modify_watermark) or (timestamp_modify_watermark[0] != timestamp_modify_program):
                self._logger.info('Файл ранее не был загружен. Начинаем загрузку записей.')
                db.load_watermark(p_file_name=file_name, p_timestamp_modify_file=timestamp_modify_program)
                self.obj_csv.validation_csv(p_path=p_path, p_group_field=p_field_group)
                db.load_table_stg(p_rows=self.obj_csv.success_row_second_validation)
                db.load_table_core(p_unique_column=p_field_unique)
            else:
                self._logger.info('Файл был ранее загружен')
