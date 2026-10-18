"""
В этом модуле определены:
1. Пользовательские исключения для реализации ошибок, возникновение которых обусловлено нарушением бизнес-логики.
2. Структура ошибки для формирования отчетов.
"""
import dataclasses
import enum

class SourceException(Exception):
    """Категория исключений для источников."""
    pass

class ConnectError(SourceException):
    """Специфическое исключение для перехвата ошибок, которые могут возникнуть при открытии соединения с источником."""
    def __init__(self, p_source_name:str, p_msg:str):
        self.source_name = p_source_name
        self.msg = p_msg

    def __str__(self):
        return f'Подключение к источнику {self.source_name} завершилось с ошибкой. Причина: {self.msg}'

class ReadError(SourceException):
    """Специфическое исключение для перехвата ошибок, которые могут возникнуть при получении данных из источника."""
    def __init__(self, p_source_name: str, p_msg: str):
        self.source_name = p_source_name
        self.msg = p_msg

    def __str__(self):
        return f'Получение данных из источника {self.source_name} завершилось с ошибкой. Причина: {self.msg}'

class CloseError(SourceException):
    """Специфическое исключение для перехвата ошибок, которые могут возникнуть при закрытии соединения с источником."""
    def __init__(self, p_source_name: str, p_msg: str):
        self.source_name = p_source_name
        self.msg = p_msg

    def __str__(self):
        return f'Закрытие соединения с источником {self.source_name} завершилось с ошибкой. Причина: {self.msg}'

class CheckFieldError(ReadError):
    """
    Специфическое исключение для перехвата ошибок, которые могут возникнуть во время получения данных, в частности во время проверки наличия обязательных
    столбцов.
    """
    def __init__(self, p_source_name: str, p_msg: str):
        self.source_name = p_source_name
        self.msg = p_msg

    def __str__(self):
        # Проверка на наличие обязательных столбцов в данных источника завершилась с ошибкой.
        return f'Проверка на наличие обязательных столбцов в данных источника {self.source_name} завершилась с ошибкой.. Причина: {self.msg}'

class SourceErrorStage(str, enum.Enum):
    """
    Класс, который перечисляет, на каких этапах работы источника возникает ошибка.
    """
    CONNECT = 'connect' # Этап подключения к источнику.
    READ = 'read' # Этап получения данных из источника.
    CLOSE = 'close' # Этап закрытия подключения источника.

class SourceErrorSeverity(str, enum.Enum):
    """
    Класс, который определяет уровень критичности ошибки. В зависимости от уровня критичности ошибки pipeline будет определять допустимое действие, как
    реагировать на возникшую ошибку.
    """
    WARNING = 'warning' # Продолжаем работу pipeline. Ошибку описываем и сохраняем. Это будет предупреждением.
    ERROR = 'error' # Продолжаем работу pipeline. Ошибку описываем и сохраняем. Эту ошибку следует проанализировать в логах после завершение pipeline.
    CRITICAL = 'critical' # Критическая ошибка. Pipeline должен завершить работу.

@dataclasses.dataclass
class SourceError:
    """
    Класс описывает структуру ошибки. Такая описательная структура:
    1. Сделает ошибку более информативной для восприятия и анализа.
    2. Позволит создавать отчет ошибок.
    3. Позволит pipeline использовать состояние экземпляра для получения нужной ему информации об ошибке.
    """
    source_name: str # Имя источника, в работе с которым возникла ошибка.
    stage: SourceErrorStage # на каком этапе работы с источником возникла ошибка.
    exception_type: str # Имя класса исключения.
    message: str # Сообщение ошибки.
    severity: SourceErrorSeverity = SourceErrorSeverity.ERROR # Уровень критичности ошибки.