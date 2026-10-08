class ArgsError(Exception):
    """Пользовательское исключение для перехвата передачи лишних аргументов или отсутствия передачи аргументов."""
    def __init__(self, p_msg:str):
        """
        :param p_msg: - это сообщение об ошибке.
        """
        self.msg = p_msg

    def __str__(self):
        return self.msg

class Structure:
    """
    Этот класс будет использоваться для упрощения инициализации экземпляров подклассов. Больше не придется определять конструкторы с перечислением большего
    количества атрибутов.
    """
    _fields = [] # В этом списке будут храниться все имена атрибутов, которые будут формировать состояние экземпляра.

    def __init__(self, *args, **kwargs):
        """
        Будет реализована поддержка для передачи как позиционных, так и ключевых аргументов.
        """
        if len(args) > len(self._fields):
            raise ArgsError(f'Ожидалось получение {len(self._fields)} аргументов')

        # Присваиваем аргументы, переданные позиционно
        for name_attr, value_attr in zip(args, self._fields):
            setattr(self, name_attr, value_attr)

        # Присваиваем аргументы, переданные по ключевым словам.
        for name_attr in self._fields[len(args):]:
            setattr(self, name_attr, kwargs.pop(name_attr))

        # Экземпляры не должны получать лишних атрибутов, которые не предусмотрены логикой.
        if kwargs:
            raise ArgsError(f"Переданы лишние аргументы: {','.join(kwargs)}")
