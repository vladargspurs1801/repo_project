"""
Модуль check_type.py.
В этом модуле реализуется проверка типов передаваемых аргументов в функцию. Если проверка выполняется успешно, то тестируемая функцию будет запущена.
Иначе будет инициализирована ошибка с предупреждением о том, что вызываемой функции был передан аргумент не того типа, который она ожидает получить.
"""
import logging as log
from inspect import signature

def check_func(p_func, *args, **kwargs):
    """
    Функция check_func будет выполнять для переданной p_func проверку соответствия типов присваиваемых объектов.
    """
    try:
        us_logger = crt_log()

        # Выполняем интроспекцию проверяемой функции. Получаем сопоставление имен аргументов с фактическими объектами.
        math_args = signature(p_func).bind(*args, **kwargs).arguments

        # Получаем аннотацию имен аргументов проверяемой функции.
        annot = p_func.__annotations__
        us_logger.info('Выполняем проверку соответствия типов')

        # Перебираем словарь со сопоставленными именами аргументов и фактическими присвоенными объектами.
        for (arg,obj) in math_args.items():
            if not isinstance(obj, annot[arg]):
                us_logger.error(f"Проверка функции {p_func.__name__}. Тип присваиваемого объекта {obj} => {type(obj)}" +
                                f" не соответствует типу аргумента {arg} из аннотации => {annot[arg]}", exc_info=True)
                raise TypeError("Передан аргумент не того типа, который ожидает получить функция. Смотри логи.")

        # Если проверка на соответствия типов прошла успешно, то вызываем проверяемую функцию.
        p_func(*args, **kwargs)

    except Exception:
        us_logger.error("Ошибка в функции check_type", exc_info=True)

def crt_log() -> log.Logger:
    """Функция настраивает и выполняет логирование."""
    try:
        # Создаем объект-регистратор логов. Задаем минимальный уровень логирования. Создаем обработчик и форматировщик.
        log_obj = log.getLogger(__name__)
        log_obj.setLevel(log.INFO)

        file_handler = log.FileHandler(filename=f'{__name__}.log', mode="a", encoding='UTF-8')

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