"""
Модуль general_logger.py.
В этом модуле создается пользовательский обработчик логов.
"""
import logging as log
import os

class CustomLogger:
    """Базовый универсальный суперкласс для пользовательских логгеров."""

    def __init__(self, p_name:str):
        """
        В конструкторе:
        1. Во избежание переопределения имен вместо наследования от класса logging.Logger выполняется обновление пространства имен экземпляра суперкласса
        CustomLogger именами logging.Logger.
        2. Для получения нового словаря пространства имен используется логика:
        2.1: Новый словарь пространства имен будет содержать только те имена, которых нет в экземпляре суперкласа CustomLogger.
        2.2: Используются getattr и dir, чтобы выполнять поиск имен по иерархическому пространству имен связанных объектов.
        2.3: Далее обновляется пространство имен конкретного экземпляра. Поэтому используется словарь пространства имен __dict__.
        """
        self._logger = log.getLogger(p_name)
        new_dict = {attr_name: getattr(self._logger, attr_name) for attr_name in dir(self._logger) if attr_name not in dir(self)}
        self.__dict__.update(new_dict)

class MyCustomLogger(CustomLogger):
    """Класс для создания пользовательского логгера."""
    def __init__(self, p_logger_name:str, p_file_name:str):
        """Переопределяем конструктор суперкласса путем расширения."""
        CustomLogger.__init__(self, p_logger_name)

        try:
            self._logger.setLevel(log.INFO)
            file_handler = log.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{p_file_name}.log'), 'w', 'UTF-8')

            formatter = log.Formatter('%(name)s %(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s')
            file_handler.setFormatter(formatter)

            if self._logger.hasHandlers(): self._logger.handlers.clear()
            self._logger.addHandler(file_handler)
        except Exception:
            self._logger.error('Ошибка в настройке конфигуратора логов', exc_info=True)
