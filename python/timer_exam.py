"""
Модуль timer_exam.py.
В этом модуле реализовано измерение времени выполнения функции тремя способами.
"""

import time, logging as log, os

# Получили начальное системное время.
timer = time.perf_counter

def total(p_func, *args, **kwargs) -> tuple:
    """
    Функция для измерения общего времени выполнения тестируемой функции.
    p_func => тестируемая функция на измерения общего времени выполнения.
    *args => форма сбора переменного кол-ва не сопоставленных позиционных объектов в кортеж.
    _reps => стандартное значение, регулирующее кол-во раз прогона тестируемой функции. Передается только по ключевому
    слову.
    **kwargs => форма сбора переменного кол-ва не сопоставленных ключевых объектов в словарь.
    Возвращает кортеж, содержащий 2 элемента: общее время выполнения функции для 1000 раз прогона, результирующе значение
    для последнего вызова функции.
    """
    try:
        logger = crt_log('a')
        logger.info("Получим стартовое время.")

        start = timer()
        _reps = kwargs.get("_reps", 1000)

        logger.info("Запустим прогон выполнения тестируемой функции.")
        for i in range(_reps):
            res = p_func(*args, **kwargs)

        logger.info("Измерим общее время выполнения функции.")
        all_time = time.perf_counter() - start
        return f"{all_time:.5f}", res

    except Exception:
        logger.error("Ошибка в измерении общего времени выполнения функции", exc_info=True)

    else:
        logger.info("Получили общее время выполнения тестируемой функции.")

def best_of(p_func, *args, **kwargs) -> tuple:
    """
    Функция измеряет время выполнения тестируемой функции и отбирает наименьшее время.
    *args => форма сбора переменного кол-ва не сопоставленных позиционных объектов в кортеж.
    _reps => стандартное значение, регулирующее кол-во раз прогона тестируемой функции. Передается только по ключевому
    слову.
    **kwargs => форма сбора переменного кол-ва не сопоставленных ключевых объектов в словарь.
    Возвращает кортеж, содержащий 2 элемента: минимальное время выполнения функции для кол-ва раз прогона, результирующе значение
    для последнего вызова функции.
    """
    try:
        logger = crt_log('w')
        logger.info("Получим стартовое время.")

        start = timer()
        _reps = kwargs.get("_reps", 5)

        logger.info("Определим лучшее минимальное время выполнения за ориентир.")
        best_time = 2 ** 32

        logger.info("Выполним прогон тестируемой функции.")
        for i in range(_reps):
            # Вызовем тестируемую функцию.
            res = p_func(*args, **kwargs)

            logger.info("Определим время выполнения.")
            all_time = time.perf_counter() - start

            # Определим, является ли полученное время выполнения меньше, чем заданный ориентир.
            if best_time < all_time: best_time = all_time

        # Вернем лучшее минимальное время выполнения и результирующее значение.
        return best_time, res

    except Exception:
        logger.error("Ошибка в измерении минимального времени выполнения функции", exc_info=True)

    else:
        logger.info("Получили минимальное время выполнения тестируемой функции.")

def best_of_total(p_func, *args, **kwargs) -> tuple:
    """
    Функция измеряет лучшее минимальное общее время выполнения.
    *args => форма сбора переменного кол-ва не сопоставленных позиционных объектов в кортеж.
    _reps_1 => кол-во раз прогона для измерения наименьшего общего времени выполнения. Стандартное значение. Передается
    только по ключевому имени.
    **kwargs => форма сбора переменного кол-ва не сопоставленных ключевых объектов в словарь.
    Возвращает наименьшее общее время выполнения.
    """
    try:
        logger = crt_log("w")
        _reps = kwargs.get("_reps", 5)

        logger.info(f"Получаем минимальное общее время выполнения функции от {_reps} расчета общего времени выполнения функции")

        return min(total(p_func, *args, **kwargs) for i in range(_reps))

    except Exception:
        logger.error("Ошибка в измерении минимального общего времени выполнения функции", exc_info=True)

    else:
        logger.info("Получили минимальное общее время выполнения тестируемой функции.")

def crt_log(p_mode:str) -> log.Logger:
    """Реализация логирования"""
    try:
        log_obj = log.getLogger(__name__)
        log_obj.setLevel(log.INFO)
        file_handler = log.FileHandler(filename=os.path.join(os.getcwd(), "file_log.log"), mode=p_mode, encoding='UTF-8')
        formatter = log.Formatter('%(name)s %(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s')

        file_handler.setFormatter(formatter)
        if log_obj.hasHandlers(): log_obj.handlers.clear()
        log_obj.addHandler(file_handler)

        return log_obj

    except Exception:
        log_obj.error('Ошибка в настройке конфигуратора логов', exc_info=True)