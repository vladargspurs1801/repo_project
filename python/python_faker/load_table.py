"""
Файл load_table.py.
В этом модуле реализована программа, которая выполняет:
1. Генерацию тестовых данных для всех таблиц, используемых во всех заданиях.

1.1. Генерация тестовых данных выполняется с помощью внешней библиотеки faker.
1.2. Генерация тестовых данных выполняется индивидуально для каждой таблицы в разных функциях. Одна функция отвечает за генерацию данных для одной таблицы.
Это позволяет реализовать принцип единственной ответственности. P.S: SOLID обычно применяется к ООП. Но принцип единственной ответственности подойдет
и для функционального программирования.
1.3: Для решения задания, в котором требуется использовать данные за майские праздники, принято решение загрузить справочник праздничных дней. В
отдельной функции создаются праздничные дни, относящиеся к заданному году или годам.

2. загрузку сгенерированных тестовых данных в таблицы в PostgresSQL для всех заданий.
2.1. Сперва сгенерированные тестовые данные загружаются в csv файл в отдельной функции. Это позволит выполнить массовую вставку данных в таблицу без
написания dml insert.
2.2: Затем в отдельной функции csv файл загружается в таблицы в PostgresSQL через массовую вставку.

3. Также в модуле реализованы другие инструменты в отдельных функциях:
3.1: Подключение к PostgresSQL выполнено с помощью декоратора контекстного менеджера для управления подключением.
3.2: Логирование.
"""

from contextlib import contextmanager
from dotenv import load_dotenv
import faker, csv, faker_commerce, os, datetime, holidays as hol, logging as log, psycopg2 as ps
from faker.exceptions import BaseFakerException, UniquenessException

@contextmanager
def postgres_conn():
    """Возвращает соединение с PostgresSQL."""
    try:
        us_logger = crt_log('a')
        us_logger.info('Подключаемся к Postgres')

        conn = ps.connect(host=os.getenv('HOST_PG'),
                          port=os.getenv('PORT_PG', '5432'),
                          database=os.getenv('DATABASE_PG'),
                          user=os.getenv('USER_PG'),
                          password=os.getenv('PASSWORD_PG')
                        )
        us_logger.info('Подключение к Postgres выполнено')
    except ps.DatabaseError:
        us_logger.error('Проблема с подключением к Postgres')
    except Exception:
        us_logger.error('Прочая ошибка')

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
    return conn

def generate_customer_data(p_faker_obj, p_num:int=10) -> dict:
        """
        Генерирует и возвращает тестовые данные для таблицы customer.
        p_faker_obj - это экземпляр, созданный от класса faker.Faker
        p_num - это кол-во генерируемых данных.
        """
        try:
            # Получаем объект-логгер для записи логов.
            us_logger = crt_log(p_mode="a")
            us_logger.info('Начинаем генерировать тестовые данные для таблицы customer')

            customer = {
                          'customer_key': [num for num in range(1, p_num+1)],
                          'fio': [p_faker_obj.unique.name() for _ in range(p_num+1)],
                          'age': [p_faker_obj.random_int(min=6, max=18) for _ in range(p_num+1)]
                      }
            us_logger.info('Создали тестовые данные для таблицы customer')

            return customer

        except UniquenessException:
            us_logger.error('Ошибка в создании уникальных тестовых данных', exc_info=True)
        except BaseFakerException:
            us_logger.error('Ошибка в создании тестовых данных', exc_info=True)
        except Exception:
            us_logger.error('Прочая ошибка', exc_info=True)


def generate_product_category_data(p_faker_obj, p_num:int=5) -> dict:
    """
    Генерирует и возвращает тестовые данные для таблицы product_category.
    p_faker_obj - это экземпляр, созданный от класса faker.Faker
    p_num - это кол-во генерируемых данных.
    """
    try:
        us_logger = crt_log(p_mode="a")
        us_logger.info('Начинаем генерировать тестовые данные для таблицы product_category')

        category_name = ('Машинки', 'Куклы', 'Комиксы', 'Мягкие игрушки', 'Лего')
        product_category = {
                              'category_key': [num for num in range(1, p_num+1)],
                              'category': [p_faker_obj.unique.random_element(category_name) for _ in range(p_num)]
                            }
        us_logger.info('Создали тестовые данные для таблицы product_category')

        return product_category

    except UniquenessException:
        us_logger.error('Ошибка в создании уникальных тестовых данных', exc_info=True)
    except BaseFakerException:
        us_logger.error('Ошибка в создании тестовых данных', exc_info=True)
    except Exception:
        us_logger.error('Прочая ошибка', exc_info=True)

def generate_product_data(p_faker_obj, p_num:int=15) -> dict:
    """
    Генерирует и возвращает тестовые данные для таблицы product.
    p_faker_obj - это экземпляр, созданный от класса faker.Faker
    p_num - это кол-во генерируемых данных.
    """
    try:
        us_logger = crt_log(p_mode="a")
        us_logger.info('Начинаем генерировать тестовые данные для таблицы product')

        product = {
                     'product_key': [num for num in range(1, p_num+1)],
                     'category_key': [p_faker_obj.random_int(min=1, max=5) for _ in range(1, p_num+1)],
                     'name': [p_faker_obj.ecommerce_name() for _ in range(1,p_num+1)],
                     'price': [p_faker_obj.pydecimal(left_digits=5, right_digits=2, positive=True, min_value=100, max_value=30000) for _ in range(1,p_num+1)]
                   }
        us_logger.info('Создали тестовые данные для таблицы product')

        return product

    except UniquenessException:
        us_logger.error('Ошибка в создании уникальных тестовых данных', exc_info=True)
    except BaseFakerException:
        us_logger.error('Ошибка в создании тестовых данных', exc_info=True)
    except Exception:
        us_logger.error('Прочая ошибка', exc_info=True)

def generate_purchase_data(p_faker_obj, p_num:int=1000) -> dict:
    """
    Генерирует и возвращает тестовые данные для таблицы purchase.
    p_faker_obj - это экземпляр, созданный от класса faker.Faker
    p_num - это кол-во генерируемых данных.
    """
    try:
        us_logger = crt_log(p_mode="a")
        us_logger.info('Начинаем генерировать тестовые данные для таблицы purchase')
        s_date = datetime.date(year=2018, month=1, day=1)
        e_date = datetime.date(year=2019, month=12, day=31)

        purchase = {
                      'purchase_key': [num for num in range(1, p_num+1)],
                      'customer_key': [p_faker_obj.random_int(min=1, max=10) for _ in range(1, p_num+1)],
                      'product_key': [p_faker_obj.random_int(min=1, max=15) for _ in range(1, p_num+1)],
                      'qty': [p_faker_obj.random_int(min=1, max=7) for _ in range(1, p_num+1)],
                      'date': [p_faker_obj.date_between_dates(date_start=s_date, date_end=e_date) for _ in range(1, p_num+1)]
                  }
        us_logger.info('Создали тестовые данные для таблицы purchase')

        return purchase

    except UniquenessException:
        us_logger.error('Ошибка в создании уникальных тестовых данных', exc_info=True)
    except BaseFakerException:
        us_logger.error('Ошибка в создании тестовых данных', exc_info=True)
    except Exception:
        us_logger.error('Прочая ошибка', exc_info=True)

def generate_holiday_data(p_year:list) -> dict:
    """
    Генерирует даты, относящиеся к государственным праздникам РФ.
    p_year - один год или несколько лет, за которые нужно получить государственные праздники.
    """
    try:
        us_logger = crt_log(p_mode="a")
        us_logger.info(f'Начинаем генерировать данные праздничных дней в России за год {p_year}')

        holiday_obj = hol.RU(years=p_year)
        holiday_data = {
                            'Дата праздника': list(holiday_obj.keys()),
                            'Название праздника': list(holiday_obj.values())
                      }

        us_logger.info(f'Создали данные о праздничных днях в России за год {p_year}')
        return holiday_data

    except Exception:
        us_logger.error('Прочая ошибка', exc_info=True)

def load_file(p_data:dict, p_table_name:str, p_file:str):
    """
    Создает csv файл и загружает в него сгенерированные тестовые данные.
    p_data - сгенерированные тестовые данные.
    p_table_name - имя таблицы, для которой были созданы тестовые данные.
    p_file - файловый путь до csv файла.
    """
    try:
        us_logger = crt_log(p_mode="a")
        us_logger.info(f'Создаем csv файл с данными для загрузки в таблицу => {p_table_name}')

        with open(file=p_file, mode="w", newline="") as csv_file:
            file_writer = csv.DictWriter(csv_file, delimiter=";", fieldnames=tuple(p_data.keys()))
            for index in range(len(p_data[list(p_data)[0]])):
                file_writer.writerow({key: value[index] for (key, value) in p_data.items()})

        us_logger.info(f'csv файл с данными для загрузки в таблицу => {p_table_name} создан')

    except IOError:
        us_logger.error('Файловый путь указан не верно. Файл не найден', exc_info=True)
    except csv.Error:
        us_logger.error('Ошибка в работе с csv', exc_info=True)
    except KeyError:
        us_logger.error('При обращении к словарю с тестовыми данными указан неверный ключ', exc_info=True)
    except Exception:
        us_logger.error('Прочая ошибка', exc_info=True)

def load_table_db(p_table_name:str, p_file:str, p_conn):
    """
    Каскадно очищает таблицы. И загружает csv файл, содержащий сгенерированные тестовые данные, в таблицы в PostgresSQL через массовую вставку.
    p_table_name - имя таблицы, в которую будет выполняться загрузка тестовых данных.
    p_file - файловый путь до csv файла.
    p_conn - экземпляр класса psycopg2.connect, определяющий подключение к СУБД PostgreSQl.
    """
    try:
        us_logger = crt_log(p_mode="a")
        query_trunc = f'truncate table public.{p_table_name} cascade'

        with open(file=p_file, newline="") as csv_file:
            cur = p_conn.cursor()
            p_conn.autocommit = True
            us_logger.info(f'Очищаем таблицу => {p_table_name}')
            cur.execute(query_trunc)
            us_logger.info(f'Загружаем тестовые данные в таблицу => {p_table_name}')
            cur.copy_from(file=csv_file, table=p_table_name, sep=';', null='')
            rows = cur.rowcount

        us_logger.info(f'Тестовые данные загружены в таблицу => {p_table_name}. Загружено строк => {rows}')

    except ps.DatabaseError:
        us_logger.error(f"Ошибка в работе Postgres", exc_info=True)
    except ps.DataError:
        us_logger.error(f"Ошибка при выполнении массовой вставки в таблицу", exc_info=True)
    except IOError:
        us_logger.error('Файловый путь указан не верно. Файл не найден', exc_info=True)
    except Exception:
        us_logger.error("Прочая ошибка", exc_info=True)

def crt_log(p_mode:str) -> log.Logger:
    """
    Функция настраивает, выполняет логирование и возвращает логгер.
    p_mode - режим использования файла логирования.
    """
    try:
        # Создаем объект-регистратор логов. Задаем минимальный уровень логирования. Создаем обработчик и форматировщик.
        log_obj = log.getLogger(__name__)
        log_obj.setLevel(log.INFO)

        file_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'load.log')
        file_handler = log.FileHandler(filename=file_log, mode=p_mode, encoding='UTF-8')

        formatter = log.Formatter('%(name)s %(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s')

        # Добавляем объект-форматировщик к объекту-обработчику.
        file_handler.setFormatter(formatter)

        # Проверяем, содержит ли объект-регистратор обработчики. Если содержит, нужно удалить. И добавить новый.
        if log_obj.hasHandlers():

            log_obj.handlers.clear()

        # Добавляем объект-обработчик к объекту-регистратору.
        log_obj.addHandler(file_handler)
        return log_obj

    except Exception:
        log_obj.error('Ошибка в настройке конфигуратора логов', exc_info=True)

def main():
    """Главная функция, объединяющая воедино все компоненты и реализующая программу в целом."""
    try:
        us_logger = crt_log(p_mode='w')

        fake_ru = faker.Faker('ru_RU')
        fake_ru.add_provider(faker_commerce.Provider)

        file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.csv')

        # С помощью zip будем итерировать по обоим спискам, тем самым создав пару: функция для генерации данных и имя таблицы.
        func_generate = [generate_product_category_data, generate_customer_data, generate_product_data, generate_purchase_data, generate_holiday_data]
        table_name = ['product_category', 'customer', 'product', 'purchase', 'holiday_days']

        us_logger.info('Начинаем генерацию тестовых данных и заполнение таблиц')
        # Загружаем конфигурационные параметры для подключения к Postgres из файла .env
        load_dotenv()
        with postgres_conn() as pg_conn:
            for func, table in zip(func_generate, table_name):
                # Получаем словарь сгенерированных данных.
                if func.__name__ == 'generate_holiday_data':
                    data = func(p_year=[2018, 2019])
                else:
                    data = func(p_faker_obj=fake_ru)
                # Создаем csv файл, в который загружаем сгенерированные данные.
                load_file(p_data=data, p_table_name=table, p_file=file_name)
                # Загружаем данные в таблицу БД.
                load_table_db(p_table_name=table, p_conn=pg_conn, p_file=file_name)

        us_logger.info('Закончили генерацию тестовых данных и заполнение таблиц')

    except Exception:
        us_logger.error('Прочая ошибка', exc_info=True)

if __name__ == '__main__':
    main()