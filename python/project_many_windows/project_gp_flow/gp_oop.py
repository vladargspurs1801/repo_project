"""
Модуль gp_oop.py.
Модуль, в котором создано приложение GUI для сборки дистрибутива по техническому стеку GreenPlum.
В приложении разработчик или аналитик, заполняя поля для ввода и нажимая на кнопки, могут собрать дистрибутив GreenPlum с созданными разработками.
Перед использованием приложения GUI вы должны создать хранимую (ые) процедуру (ы) в СУБД, которая (ые) войдет (ут) в состав дистрибутива.
"""
import psycopg2 as ps
import userconfig.config as uc
import tkinter as tk
from tkinter.messagebox import showinfo, showerror
import re, git
import general_classes.general_widgets as gw
import general_classes.general_logger as gl

class DistrGp:
    """
    Класс реализует GUI, который позволит разработчику или аналитику собирать дистрибутив GreenPlum. GUI интегрирован с СУБД GreenPlum. Пользователю
    будет нужно только ввести название схемы и функции, которую он разработал и хочет внедрить на другие стенды разработки в рамках релизного процесса.
    """
    def __init__(self, p_master:tk.Toplevel):
        """
        GUI по созданию расчетных потоков будет окном верхнего уровня многооконного приложения GUI, ввиду этого в конструкторе определяется параметр
        p_master
        """
        self.main_window = p_master
        self.main_window.title('СБОРКА ДИСТРИБУТИВОВ GREENPLUM')
        self.main_window.geometry('1920x1080')

        # Внедряем другие объекты, которые будут реализовывать интерфейс экземпляра класса DistrGp.
        self._logger = gl.MyCustomLogger("gp_logger", "gp_log")
        self.font = gw.TextFont()
        self.promt_label = gw.PromtLabel(p_frame=self.main_window, p_tittle='СБОРКА ДИСТРИБУТИВОВ GREENPLUM')
        self.crt_branch_type_frame()
        self.crt_branch_frame()
        self.crt_greenplum_frame()
        #self.git_frame = gw.GitFrame(p_frame=self.main_window, p_logger=self._logger, p_tech_stack='GP')

        tk.mainloop()

    def crt_branch_type_frame(self):
        """Метод, определяющий виджеты для выбора типа ветки."""
        self.branch_type_frame = tk.Frame(self.main_window)
        self.branch_type_frame.pack(padx=20)

        self.branch_type_label = tk.Label(self.branch_type_frame, text='Выберите тип ветки: ', font=self.font.custom_font_2)
        self.branch_type_label.pack(side=tk.TOP, padx=5, pady=20)

        self.branch_type_choise = tk.StringVar(self.branch_type_frame, value='Feature')
        values = {"feature":"feature", "release":"release", "bugfix":"bugfix"}

        for text, value in values.items():
            self.rad_but_type = tk.Radiobutton(self.branch_type_frame, text=text, variable=self.branch_type_choise, value=value, command=self.choise_type,
                                               font=self.font.custom_font_3)
            self.rad_but_type.pack(side=tk.TOP, ipady=5)

    def choise_branch_type(self):
        """Обратный вызов для кнопки rad_but_type. Возвращает тип ветки, выбранный пользователем."""
        self.branch_type = self.branch_type_choise.get()

    def crt_branch_frame(self):
        """Метод для определения виджетов к созданию ветки в локальном репозитории."""

        self.branch_frame = tk.Frame(self.main_window)
        self.branch_frame.pack(padx=20)

        self.branch_label = tk.Label(self.branch_frame, text='Введите наименование ветки: ', font=self.font.custom_font_2)
        self.branch_label.pack(side='left', padx=5, pady=20)

        self.branch_entry = tk.Entry(self.branch_frame, width=60)
        self.branch_entry.pack(side='left', padx=5, pady=20)

        self.branch_button = tk.Button(self.branch_frame, text='Создать / перейти в ветку', command=self.crt_branch)
        self.branch_button.pack(side='right', padx=5, pady=5)

    def crt_branch(self):
        """Обратный вызов для кнопки branch_button. Создает ветку в локальном репозитории либо переходит в ветку, если она существует."""
        try:
            self._logger.info('Начинаем создавать ветку')

            self.repo_obj = git.Repo(uc.REPO_FOLDER_GP)
            self.branch_name = self.branch_type + re.sub(string=self.branch_entry.get(), pattern=r"\w*/", repl="")

            # Активировать внедренные объекты.
            self.git_frame = gw.GitFrame(p_frame=self.main_window, p_logger=self._logger, p_tech_stack='GP')
            self.version_jenkins = gw.VersionPipeline(p_logger=self._logger, p_frame=self.main_window, p_tech_stack='GP', p_branch_name=self.branch_name)
            self.pull_request_frame = gw.BitbucketFrame(p_frame=self.main_window, p_tech_stack='GP', p_logger=self._logger, p_branch_name=self.branch_name)
            self.quit = gw.Quit(p_frame=self.main_window)
            self.del_branch_frame = gw.DeleteBranchFrame(p_frame=self.quit.quit_frame, p_repo_obj=self.repo_obj, p_logger=self._logger,
                                                         p_branch_name=self.branch_name)

            o = self.repo_obj.remotes.origin
            if self.branch_frame in self.repo_obj.branches:
                feature_branch = self.repo_obj.branches[self.branch_name]
                feature_branch.checkout()
                o.pull()
                self._logger.info('Перешел в ветку')
                showinfo('SUCCESS!', 'Перешли в ветку')

            else:
                dev_branch = self.repo_obj.branches["dev"]
                dev_branch.checkout()
                o.pull()
                feature_branch = self.repo_obj.create_head(self.branch_name)
                feature_branch.checkout()
                self._logger.info('Ветка создана.')
                showinfo('SUCCESS!', 'Создали ветку')

        except git.NoSuchPathError:
            self._logger.error('Не найдена директория локального репозитория', exc_info=True)
            showerror('ERROR!','Ошибка! Смотри логги.')
        except git.CommandError:
            self._logger('Ошибка в переключении в ветку в git', exc_info=True)
        except Exception:
            self._logger('Прочая ошибка', exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')

    def crt_greenplum_frame(self):
        """Метод, определяющий виджеты для записи файлов с ddl функций, запросом проверок создания функций и заполнение меты"""
        "Создание контейнеров для виджетов по записи файлов с ddl-запросом функции, запроса проверок создания и меты"
        try:
            self.owner_frame = tk.Frame(self.main_window)
            self.owner_frame.pack(padx=20)

            self.owner_label = tk.Label(self.owner_frame, text="Введите название схемы", font=self.font.custom_font_2)
            self.owner_label.pack(side='left', padx=5, pady=20)

            self.owner_entry = tk.Entry(self.owner_frame, width=50)
            self.owner_entry.pack(side='left', padx=5, pady=20)

            self.func_frame = tk.Frame(self.main_window)
            self.func_frame.pack(padx=20)

            self.func_label = tk.Label(self.func_frame, text="Введите название функций", font=self.font.custom_font_2)
            self.func_label.pack(side='left', padx=5, pady=20)

            self.func_entry = tk.Entry(self.func_frame, width=60)
            self.func_entry.pack(side='left', padx=5, pady=20)

            self.file_button = tk.Button(self.func_frame, text="Записать файлы", command=self.write_file)
            self.file_button.pack(side="right", padx=5, pady=5)

        except Exception:
            self._logger.error("Ошибка в создании виджетов при работе с GreenPlum", exc_info=True)

    def write_file(self):
        """Обратный вызов для кнопки file_button. Записывает файлы с ddl функций, запросом проверки создания и файлом.yml"""
        try:
            owner_name = self.owner_entry.get()
            comment_pattern = re.compile(pattern=r"\w*\W*\d{2}.\d{2}.\d{4}")

            # Записываем файлы для каждого объекта в GreenPlum.
            for function_name in re.split(pattern=r"(?:\s|,|;)\s*", string=self.func_entry.get()):
                # Получаем ddl функции.
                ddl_sql = f"""SELECT pg_get_functiondef(p.oid)
                               FROM pg_proc p
                               JOIN pg_namespace ns on p.pronamespace = ns.oid
                               WHERE ns.nspname = %s
                               AND p.proname = %s"""
                uc.cur.execute(ddl_sql, [owner_name, function_name])

                # Пишем анонимный блок для удаления функции во избежание создания перегруженной функции.
                block_anon = f"""do $$
                                 declare
                                   del_command text;
                                 begin
                                   for del_command in (
                                                        select format('drop function if exists %s.%s(%s);',
                                                                       ns.nspname,
                                                                       pr.proname,
                                                                       oidvectortypes(pr.proargtypes)
                                                                     )
                                                         from pg_proc as pr
                                                         join pg_namespace as ns on pr.pronamespace = ns.oid
                                                        where ns.nspname = '{owner_name}'
                                                        and pr.proname = '{function_name}'
                                                       )
                                    loop
                                      execute del_command;
                                    end loop;
                                end $$;            
                                """
                folder_path = uc.get_path(uc.function_folder, f"{function_name}.sql")

                # Записываем ddl-запрос функции.
                with open(file=folder_path, mode="w", encoding="UTF-8") as sql_file:
                    sql_file.writelines(block_anon)
                    for line in uc.cur.fetchall(): sql_file.writelines(line[0])
                    # Извлекаем комментарий для добавления в запрос проверок наката.
                    comment = comment_pattern.search(string=line[0]).group(0)

                # Записываем в файл.yaml файлы с программным кодом по созданию функций.
                with open(file=uc.meta_folder, mode="a", encoding="utf-8") as meta_file:
                    meta_file.write(folder_path + "\n")

                # Если изменено несколько функций, то запрос проверок должен проверять создание этих функций.
                # Пишем sql-запрос для проверки.
                check_sql = f"""select 'Проверка наката функции {owner_name}.{function_name}: ' || count(*) || ' - ожидаем 1' as chk
                                 from pg_proc p
                                 join pg_namespace ns on p.pronamespace = ns.oid
                                where ns.nspname = '{owner_name}'
                                and p.proname = '{function_name}'
                                and p.prosrc like '%{comment}%';"""

                with open(file=uc.check_folder, mode="a", encoding="UTF-8") as check_file:
                    check_file.writelines(check_sql)

            # Заполняем файл.yml файлом с проверками.
            with open(file=uc.meta_folder, mode="a", encoding="UTF-8") as meta_file:
                meta_file.write(uc.check_folder + "\n")

        except ps.DatabaseError:
            self._logger.error("Ошибка в работе с GreenPlum", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логи!")

        except Exception:
            self.logger.error("Другая ошибка", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логи!")

        else:
            self._logger.info("Файлы с кодом sql созданы.")
            showinfo("SUCCESS!", "Файлы с кодом sql созданы.")
