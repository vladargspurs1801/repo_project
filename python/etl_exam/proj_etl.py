"""
Программа создает ETL-инструмент.
Extract => Выполняется извлечение непрочитанных писем от Жизнь-Марта из электронной почты.
Каждое электронное письмо содержит информацию о товарном чеке приобретенных товаров.
Transform => Выполняется парсинг содержимого электронных писем для извлечения даты покупки, наименования товара,
стоимости за единицу, количества и общей стоимости.
Load => Выполняется загрузка извлеченных данных в таблицу в БД PostgreSQL.
"""
import bs4 # Для парсинга HTML.
import csv # Для сохранения данных и массовой вставки в таблицу БД Postgre.
import imaplib # Реализует протокол IMAP для взаимодействия с серверами электронной почты.
import email # Нужен для работы с электронными письмами из почты.
import config.user_config as mc # Настройки для подключения к почтовому серверу IMAP и БД Postgre.
import re # Регулярные выражения используются для валидации входящих данных.
from collections import namedtuple # Именованный кортеж будет контейнером для хранения извлеченных данных.
import psycopg2 as ps # Для подключения к БД Postgre и работы с ней.
import logging as log # Для выполнения логгирования.

def main():
    """
    Строки документации для атрибута __doc__.
    Функция выполняет подключение в почтовому серверу IMAP. Извлекает все непрочитанные письма из выбранной папки.
    Запоминает ИД последнего непрочитанного письма. Затем функция вызывает другие функции, реализующие все этапы ETL.
    """
    try:
        # Получить логгер.
        us_logger = crt_log(p_mode='w')

        # Создаем коллекцию для хранения извлеченных данных.
        Check = namedtuple(typename='Check', field_names=['orderdate', 'product_name', 'price_per_unit', 'count', 'total_price_inventory'],
                               defaults=[[], [], [], [], []])
        Check.__doc__ += "Данные совершенных покупок в магазине Жизнь-Март"
        Check.orderdate.__doc__ = "Дата совершенной покупки"
        Check.product_name.__doc__ = "Наименование товара"
        Check.price_per_unit.__doc__ = "Цена за единицу"
        Check.count.__doc__ = "Кол-во"
        Check.total_price_inventory.__doc__ = "Общая стоимость покупки"
        check = Check()

        # Подключение к почтовому серверу IMAP.
        imap = imaplib.IMAP4_SSL(mc.imap_server, mc.port)
        imap.login(user=mc.username, password=mc.mail_pass)
        us_logger.info("Подключение к почтовому серверу выполнено успешно")

        # Выбираем папку с входящими письмами для работы.
        imap.select(mailbox="Inbox", readonly=False)

        # Извлекаем ИД непрочитанных писем.
        unseen_mails = imap.search(None, "UNSEEN")
        unseen_mails_str = str(unseen_mails[1])
        lst_email = (item for item in unseen_mails_str if item.isdigit())

        for item in lst_email:
            res, msg_bt = imap.fetch(message_set=item, message_parts='(RFC822)')

            # Преобразуем зашированное htlm-содержимое электронного письма в байты.
            msg = email.message_from_bytes(msg_bt[0][1])

            us_logger.info("Выполняем дешифровку содержимого электронного письма.")
            text_email = get_decode_email(p_msg=msg)

            us_logger.info("Выполняем парсинг содержимого электронного письма.")
            get_transform_data(p_letter=text_email, p_collec=check)

        us_logger.info("Выполняем загрузку данных в таблицу БД Postgre.")
        load_data(p_collec=check)

    except Exception:
        us_logger.error("Ошибка в функции main", exc_info=True)

    else:
        us_logger.info("Функция main() успешно выполнилась. Все этапы ETL выполнены.")

def get_decode_email(p_msg) -> str:
    """
    Строки документации для атрибута __doc__. Этап - Extract.
    Функции в качестве аргумента присваивается зашифрованное содержимое письма.
    Выполняется дешифровка. Возвращается дешифрованное содержимое письма в байтах.
    """
    try:
        us_logger = crt_log(p_mode="a")

        # Проверяем, является ли объект-сообщение многокомпонентным.
        if p_msg.is_multipart():
            for item in p_msg.walk():

                # Нужно найти основную часть письма. У основной части письма тип - text/html. Декодируем содержимое.
                if item.get_content_type() == "text/html":
                    text_email = item.get_payload(decode=True).decode()

        else:
            text_email = p_msg.get_payload(decode=True).decode()
        return text_email

    except Exception:
        us_logger.error("Ошибка в функции get_decode_email", exc_info=True)

    else:
        us_logger.info("Функция get_decode_email успешно выполнилась. Содержимое письма раскодировано.")

def get_transform_data(p_letter:str, p_collec:namedtuple):
    """
    Строки документации для атрибута __doc__. Этап - Transform.
    Функции в качестве аргумента присваивается декодированное содержимое письма и именованный кортеж.
    Выполняется парсинг html содержимого письма. Заполняется именованный кортеж данными: дата покупки, количество,
    стоимость за единицу, общая стоимость, наименование товара.
    """
    try:
        us_logger = crt_log(p_mode="a")

        # Обрабатываем письма только от жизнь-марта.
        if '@lifemart.ru' in re.findall(pattern=r'@\w+.ru', string=p_letter):
            soup = bs4.BeautifulSoup(p_letter, "html.parser")

            # Получаем наименование товара, стоимость за единицу, кол-во, общую стоимость.
            cnt_soap = 1
            for sp in soup.find_all(("strong", "span")):
                if re.search(pattern="\d+.00",string=sp.text): break
                p_collec[cnt_soap].append(re.sub(pattern=r"\d\W\s", repl="", string=sp.text))
                cnt_soap += 1
                if cnt_soap > 4: cnt_soap = 1

            us_logger.info("Извлекли наименование товара, стоимость за единицу, кол-во, общую стоимость")

            # Получаем дату заказа.
            for td in soup.find_all("td"):
                if td.text.strip().startswith("Приход"):
                    # Оператор повторения используется для того случая, если в товарном чеке несколько товаров. Но дата
                    # только одна.
                    p_collec[0].extend(re.findall(pattern="\d{2}.\d{2}.\d{4}", string=td.text) * len(p_collec.product_name))
                    break

            us_logger.info("Извлекли дату заказа")

    except Exception:
        us_logger.error("Ошибка в функции get_transform_data", exc_info=True)

    else:
        us_logger.info("Функция get_transform_data отработала. Парсинг и заполнение коллекции выполнены")

def load_data(p_collec:namedtuple):
    """
    Строки документации для атрибута __doc__. Этап - Load.
    Функции в качестве аргумента присваивается именованный кортеж. Выполняется запись данных в csv. Создается
    подключение к СУБД Postgre. Совершается массовая вставка в таблицу в БД.
    """
    try:
        us_logger = crt_log(p_mode="a")
        # Включаем автоматическое сохранение всех совершенных dml-операций.
        mc.conn.autocommit = True

        # Создаем файловый объект и записываем данные именованного кортежа в csv.
        with open(file="march_sales.csv", mode="w", newline="") as csv_file:
            file_writer = csv.DictWriter(csv_file, delimiter=";", fieldnames=p_collec._fields)
            for index in range(len(p_collec.product_name)):
                file_writer.writerow({key: value[index] for (key, value) in p_collec._asdict().items()})

        with open(file="march_sales.csv", newline="") as csv_file:
            # Выполнить массовую вставку данных из csv в таблицу БД.
            mc.cur.copy_from(file=csv_file, table='livemarch_sales', sep=';')
            rows = mc.cur.rowcount

    except ps.DatabaseError:
        us_logger.error(f"Ошибка при выполнении массовой вставки в таблицу в Postgre", exc_info=True)

    except Exception:
        us_logger.error("Ошибка в функции load_data", exc_info=True)

    else:
        us_logger.info(f"Функция load_data выполнилась. Вставлено строк => {rows}.")

# Создать логгер.
def crt_log(p_mode:str) -> log.Logger:
    "Функция настраивает и выполняет логирование."
    try:
        # Создаем объект-регистратор логов. Задаем минимальный уровень логирования. Создаем обработчик и форматировщик.
        log_obj = log.getLogger(__name__)
        log_obj.setLevel(log.INFO)

        file_handler = log.FileHandler(filename=mc.__dict__["__file__"].replace("__init__.py","etl_log.log"), mode=p_mode, encoding='UTF-8')

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

# Вызвать управляющую функцию.
if __name__ == "__main__":
    main()