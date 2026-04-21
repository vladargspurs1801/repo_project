"""
Файл multiple_windows.py
В модуле определяется приложение с многооконным GUI. Пользователь может перейти в отдельное приложение GUI по сборке дистрибутива конкретного технического
стека, нажав на нужную кнопку.
"""
import tkinter as tk
from tkinter.messagebox import showerror
import project_gp_flow.gp_oop as gp
from project_gp_flow.flow_oop import Flow
from general_classes.general_widgets import PromtLabel, TextFont, Quit
import general_classes.general_logger as gl

class MultiDistr:
    """
    Класс создает многооконное приложение GUI. Каждое окно - это переход в другое GUI приложение, отвечающее за сборку дистрибутива по отдельному
    техническому стеку.
    """
    def __init__(self, p_master:tk.Tk):
        """
        Конструктор создает корневое окно-интерфейс. В нем будут кнопки, нажатие на которые откроет другие окна верхнего уровня.
        """
        self._logger = gl.MyCustomLogger(p_logger_name="distr_logger", p_file_name="distribution")
        self.master = p_master
        self.master.title("СБОРКА ДИСТРИБУТИВОВ")
        self.master.geometry('1920x1080')

        # Реализуем интерфейс.
        self.font = TextFont()
        self.promt_label = PromtLabel(p_frame=self.master, p_tittle='СБОРКА ДИСТРИБУТИВОВ')

        self.frame = tk.Frame(self.master)
        self.frame.pack(padx=20)
        self.desc_label = tk.Label(self.master, text='Нажмите на кнопку для перехода в интерфейс, чтобы собрать дистрибутив', font=self.font.custom_font_2)
        self.desc_label.pack(side=tk.TOP, padx=5, pady=20)

        self.but_frame = tk.Frame(self.master)
        self.but_frame.pack(padx=20)
        self.button_gp = tk.Button(self.but_frame, text='Собрать дистрибутив ГП', width=25, command=self.gp_window)
        self.button_gp.pack(side='right', padx=30, pady=30)
        self.button_flow = tk.Button(self.but_frame, text='Собрать дистрибутив FLOW', width=25, command=self.flow_window)
        self.button_flow.pack(side='right', padx=30, pady=30)

        self.quit = Quit(p_frame=self.master)

    def gp_window(self):
        """
        Обратный вызов для кнопки button_gp. Создает окно верхнего уровня, в котором пользователь может собрать дистрибутив GreenPlum.
        Создаем окно верхнего уровня (вложенное окно), которое будет:
        1. Синхронизировано с главным окном tk.Tk.
        2. Будет связано с главным окном tk.Tk.
        Для создания окна верхнего используем класс tkinter.Toplevel.
        Класс tkinter.Toplevel позволяет создавать самостоятельные окна верхнего уровня. Но эти окна верхнего уровня будут связаны с главным окном tk.Tk.
        """
        try:
            self.greenplum_window = tk.Toplevel(self.master)
            self.app = gp.DistrGp(self.greenplum_window)
        except Exception:
            self._logger.error('Ошибка в создании верхнего окна для сборки дистрибутива GreenPlum', exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логи.")

    def flow_window(self):
        """
        Обратный вызов для кнопки button_gp. Создает окно верхнего уровня, в котором пользователь может собрать дистрибутив Flow.
        """
        try:
            self.stream_window = tk.Toplevel(self.master)
            self.app = Flow(self.stream_window)
        except Exception:
            self._logger.error("Ошибка в создании верхнего окна для сборки дистрибутива Flow", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логи.")

def main():
    root = tk.Tk()
    app = MultiDistr(root)
    root.mainloop()

if __name__ == "__main__":
    main()