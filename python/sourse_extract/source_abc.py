"""
В этом модуле определен обязательный интерфейс, которому должны соответствовать источники.
"""
import abc

class DataSource(abc.ABC):
    """Абстрактный базовый суперкласс определяет единый интерфейс для источников получения данных."""
    @abc.abstractmethod
    def connect(self):
        """Для создания подключения."""
        pass

    def __enter__(self):
        """Для поддержки протокола менеджера контекста. Отслеживает вход в with."""
        self.connect()
        return self

    @abc.abstractmethod
    def read(self) -> list[dict]:
        """
        Метод для обращения к источнику и возвращения данных.
        :return: - данные, полученные из источника.
        """
        pass

    @abc.abstractmethod
    def close(self):
        """Метод для закрытия соединения и подключения."""
        pass

    def __exit__(self, ex_type, ex_val, tb):
        """Для поддержки протокола менеджера контекста. Отслеживает выход из with."""
        try:
            pass
        finally:
            self.close()

    @abc.abstractmethod
    def metadata(self) -> dict:
        """Возвращает описание источника."""
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Свойство, которое обладает только геттером.
        :return: - динамически возвращает имя источника.
        """
        pass