"""
Модуль flow_oop.py.
Модуль, в котором создано приложение GUI для сборки дистрибутива по техническому стеку Flow.
В приложении разработчик или аналитик, заполняя поля для ввода и нажимая на кнопки, могут создать расчетный поток.
Перед использованием приложения GUI вы должны создать хранимую процедуру в СУБД, которую будет вызывать созданный расчетный поток.
"""

import tkinter as tk
import userconfig.config as uc
import git, os, re, yaml
import general_classes.general_logger as gl
import general_classes.general_widgets as gw
import xml.etree.ElementTree as et
from collections import Counter
from tkinter.messagebox import showinfo, showerror
from logging import Logger

def get_path(p_path:str, p_folder:str) -> str:
    """Функция возвращает файловый путь до нужной директории"""
    return os.path.join(p_path, p_folder)

class Iterable:
    """Класс создает пользовательский итерируемый объект, обладающий множественным итерационным просмотром. Далее он будет использоваться для
    множественного итеративного просмотра результата select запроса.
    """
    def __init__(self, p_owner:str, p_func:str, p_logger:Logger):
        self.owner = p_owner
        self.func = p_func
        self._logger = p_logger

    def __iter__(self):
        """Используется yield, поскольку генератор уже является итератором и итерируемым объектом одновременно. Определять метод перегрузки __next__ в
        таком случае не потребуется."""
        try:
            self._logger.info("Получаем сигнатуру функции.")

            query = f"""SELECT unnest(p.proargnames) as arguments,
                               unnest(string_to_array((oidvectortypes(p.proargtypes)), ',')) as argument_type
                         FROM pg_catalog.pg_namespace n
                         JOIN pg_catalog.pg_proc p ON pronamespace = n.oid
                         JOIN pg_type t ON p.prorettype = t.oid
                         WHERE nspname = %s
                         AND proname = '%s
                         GROUP BY p.proname, p.proargtypes, p.proargnames
                     """

            uc.cur.execute(query, [self.owner, self.func])

            for ind, arg_type in enumerate(filter(lambda data: 'p_crl_loadingid' not in data, uc.cur.fetchall()),1):
                yield ind, arg_type

        except uc.con.DatabaseError:
            self._logger.error("Ошибка в выполнении select запроса для получения сигнатуры функции", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логги.")
        except Exception:
            self._logger.error("Ошибка в создании итерационного контекста через __iter__", exc_info=True)
        else:
            self._logger.info("Получили сигнатуру функций.")

class Flow:
    """Класс реализует GUI, который позволит разработчику или аналитику создавать расчетные потоки. За создание отдельных компонентов расчетного потока
    отвечают кнопки."""

    def __init__(self, p_master:tk.Toplevel):
        """GUI по созданию расчетных потоков будет окном верхнего уровня многооконного приложения GUI, ввиду этого в конструкторе определяется параметр
        p_master"""

        self.main_window = p_master
        self.main_window.title('СОЗДАНИЕ ПОТОКОВ')
        self.main_window.geometry('1920x1080')

        # Внедряем другие объекты, которые будут реализовывать интерфейс экземпляра класса Flow.
        self._logger = gl.MyCustomLogger("flow_logger", "flow")
        self.font = gw.TextFont()
        self.promt_label = gw.PromtLabel(p_frame=self.main_window, p_tittle='СОЗДАНИЕ ПОТОКОВ')
        self.crt_branch_frame()
        self.get_showcase()
        self.crt_flow_directory()
        self.crt_sql_frame()
        self.crt_instance_frame()

        tk.mainloop()

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

            self.repo_obj = git.Repo(uc.REPO_FOLDER_FLOW)
            self.branch_name = "feature/" + re.sub(string=self.branch_entry.get(), pattern=r"\w*/", repl="")

            # Активировать внедренные объекты.
            self.git_frame = gw.GitFrame(p_frame=self.main_window, p_logger=self._logger, p_tech_stack='FLOW')
            self.version_jenkins = gw.VersionPipeline(p_logger=self._logger, p_frame=self.main_window, p_tech_stack='FLOW', p_branch_name=self.branch_name)
            self.pull_request = gw.BitbucketFrame(p_frame=self.main_window, p_tech_stack='FLOW', p_logger=self._logger, p_branch_name=self.branch_name)
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

    def get_showcase(self):
        """Метод для определения виджетов к выбору витрины."""
        try:
            self.showcase_frame = tk.Frame(self.main_window)
            self.showcase_frame.pack(padx=20)

            self.variable = tk.StringVar(self.showcase_frame)
            self.variable.set('Выберите витрину')

            self.menu = tk.OptionMenu(self.showcase_frame, self.variable, *uc.config_flow._fields, command=self.choise_showcase)
            self.menu.pack(side='top', padx=5, pady=20)
        except Exception:
            self._logger.error('Ошибка в виджетах для выбора витрины', exc_info=True)

    def choise_showcase(self, option):
        """Обратный вызов для выпадающего списка menu. Возвращает наименование витрины, выбранной пользователем."""
        try:
            self.showcase = self.variable.get()
            self._logger.info(f'Выбрана витрина => {self.showcase}')
        except Exception:
            self._logger.error("Ошибка в получении витрины", exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги')

    def crt_flow_directory(self):
        """Метод для определения виджетов к получению наименования потока."""
        self.flow_frame = tk.Frame(self.main_window)
        self.flow_frame.pack(padx=20)

        self.flow_label = tk.Label(self.flow_frame, text='Введите наименование потока: ', font=self.font.custom_font_2)
        self.flow_label.pack(side='left', padx=5, pady=20)

        self.flow_entry = tk.Entry(self.flow_frame, width=60)
        self.flow_entry.pack(side='left', padx=5, pady=20)

        self.flow_button = tk.Button(self.flow_frame, text='Создать каталог потока', command=self.crt_flow)
        self.flow_button.pack(side='right', padx=5, pady=5)

    def crt_flow(self):
        """Обратный вызов для кнопки flow_button. Создает каталог, в котором будет храниться структура потока"""
        try:
            # Перейти в каталог витрины.
            self.vitrina_folder = get_path(uc.REPO_FOLDER_FLOW, self.showcase)
            # Получаем название схемы для потока.
            schema = self.showcase.replace('SVD_KB_', '')
            # Создать каталог потока. Получить имя потока.
            self.long_flow_name = f"CORP120_{schema}_{self.flow_entry.get()}_GP_FLOW_TGR" # Создаем длинное название потока.
            self.flow_dir_name = get_path(self.vitrina_folder, self.long_flow_name)
            # Создаем подкаталог нового потока.
            if not os.path.isdir(self.flow_dir_name): os.makedirs(get_path(self.vitrina_folder, self.long_flow_name))

        except os.error:
            self._logger.error('Ошибка в работе с файловыми каталогами', exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')
        except Exception:
            self._logger.error('Прочая ошибка', exc_info=True)

        else:
            self._logger.info('Создали каталог потока')
            showinfo('SUCCESS!', 'Создали каталог потока.')

    def crt_sql_frame(self):
        """Метод для определения виджетов по созданию подкаталога с файлами кода sql и файлом pom.xml"""
        self.sql_frame = tk.Frame(self.main_window)
        self.sql_frame.pack(padx=20)

        self.sql_label = tk.Label(self.sql_frame, text='Введите имя главной функции: ', font=self.font.custom_font_2)
        self.sql_label.pack(side='left', padx=5, pady=20)

        self.sql_entry = tk.Entry(self.sql_frame, width=60)
        self.sql_entry.pack(side='left', padx=5, pady=20)

        self.sql_button = tk.Button(self.sql_frame, text='Создать подкаталог sql', command=self.crt_sql)
        self.sql_button.pack(side='right', padx=5, pady=5)

    def crt_sql(self):
        """Обратный вызов для кнопки sql_button. Создает подкаталог с файлами кода sql и файл pom.xml."""
        try:
            # Создать подкаталог sql.
            self._logger.info('Начинаем создавать подкаталог для файлов с кодом sql.')

            self.func_name = self.sql_entry.get()
            sql_folder = get_path(self.flow_dir_name, 'sql')
            if not os.path.isdir(sql_folder): os.makedirs(get_path(self.flow_dir_name, "sql"))

            self._logger.info('Начинаем создавать файлы с кодом sql.')

            get_log = get_path(sql_folder, 'get_log_stat.sql')
            get_stat = get_path(sql_folder, 'project_statistics_db_query.sql')
            call_func = get_path(sql_folder, f'run_{self.func_name}.sql')

            with open(file=get_log, mode='w', encoding='UTF-8') as log_file, open(file=get_stat, mode='w', encoding='UTF-8') as stat_file:
                log_file.write(f'select schema_{self.showcase.lower()}_core.get_log_stat($$p_loading_id')

                stat_file.writelines(f"""SELECT '$$p_loading_id' as loading_id, coalesce((calc_stats->>'p_ins'), '0')::VARCHAR as statval --insert
                                          FROM schema_{self.showcase.lower()}_core.t_logs
                                         WHERE load_id = $$p_loading_id AND calc_stats is not null""")


                args_new = ["$$p_loading_id"]
                self.args_iter = Iterable(p_owner=f'schema_{self.showcase.lower()}_core', p_func=self.func_name, p_logger=self._logger)
                types_dct = {'character varying': 'varchar', 'smallint': 'int2', 'integer': 'int4', 'bigint': 'int8'}
                for ind, params in self.args_iter:
                    _, arg_type = params
                    if arg_type in types_dct: arg_type = types_dct[arg_type]
                    args_new.append(f"${{p{ind}}}::{arg_type}".format_map(vars()))

                with open(file=call_func, mode='w', encoding='UTF-8') as func_file:
                    func_file.write(f"SELECT schema_{self.showcase.lower()}_core.{self.func_name}({','.join(args_new).replace(' ', '')})")

                # Создаем файл pom.xml
                self.crt_pom()

        except os.error:
            self._logger.error('Ошибка в работе с файловыми каталогами', exc_info=True)
        except Exception:
            self._logger.error('Прочая ошибка', exc_info=True)

        else:
            self._logger.info('Создали подкаталог для файлов sql и файлы с кодом sql')
            showinfo('SUCCESS!', 'Создан подкаталог sql и файлы с кодом sql')

    def crt_pom(self):
        """Метод, выполняющий парсинг файла pom.xml."""
        try:
            self._logger.info('Начинаем создавать файл pom.xml')
            pom_file = get_path(uc.REPO_FOLDER_FLOW, 'pom.xml')
            parent_pom_tree = et.parse(pom_file)
            # Регистрируем пространство имен xml.
            et.register_namespace(prefix="", uri=r"http://flow.example.com")

            # Получаем корневой тег-заголовок, дочерние теги modules, version, plugin.
            parent_pom_root = parent_pom_tree.getroot()
            modules = parent_pom_root.find("{http://flow.example.com}modules")
            module = modules.find("{http://flow.example.com}module")
            module.text = f"{self.showcase}/{self.long_flow_name}"
            version_parent = parent_pom_root.find("{http://flow.example.com}version")
            version_parent.text = '0.1.0'
            plugin = parent_pom_root.find("{http://flow.example.com}plugin")
            plugin.text = ":" + "/".join(["user", "__user__", "project_flow", self.long_flow_name])

            # Форматируем, чтобы каждый тег находился на отдельной строке.
            et.indent(parent_pom_tree, space="\t", level=0)
            # Записываем отредактированное дерево xml в новый файл.
            parent_pom_tree.write(file_or_filename=pom_file, encoding="UTF-8", xml_declaration=True, short_empty_elements=False)

        except et.ParseError:
            self._logger.error("Ошибка в анализе и работе с xml", exc_info=True)
            showerror('ERROR!', "Ошибка! Смотри логги")
        except Exception:
            self._logger.error("Прочая ошибка", exc_info=True)
            showerror('ERROR!', "Ошибка! Смотри логги")

        else:
            self._logger.info("Парсинг pom.xml завершен успешно")
            showinfo("SUCCESS!", "Создали файл pom.xml")

    def crt_instance_frame(self):
        """Метод определяет виджеты для получения номера сущности"""
        self.instance_frame = tk.Frame(self.main_window)
        self.instance_frame.pack(padx=20)

        self.instance_label = tk.Label(self.instance_frame, text='Введите номер сущности: ', font=self.font.custom_font_2)
        self.instance_label.pack(side='left', padx=5, pady=20)

        self.instance_entry = tk.Entry(self.instance_frame, width=60)
        self.instance_entry.pack(side='left', padx=5, pady=20)

        self.instance_button = tk.Button(self.instance_frame, text='Создать data-product', command=self.crt_data_product)
        self.instance_button.pack(side='right', padx=5, pady=20)

    def crt_data_product(self):
        """Обратный вызов для кнопки instance_button. Создает файл data-product.yml. Выполняется копирование файла data-product.yml с универсальным
        шаблоном заполнения. Затем выполняется редактирование содержимого файла через библиотеку yaml."""
        try:
            self._logger.info('Получаем целевую таблицу')

            #Получаем целевую таблицу. Для этого получаем код управляющей функции. Затем получаем код всех функций, вложенных в управляющую. Получаем
            # все целевые таблицы и их кол-во.
            query_tables = """SELECT p.prosrc
                               FROM pg_catalog.pg_namespace n
                               JOIN pg_catalog.pg_proc p ON pronamespace = n.oid
                               JOIN pg_type t ON p.prorettype = t.oid
                              WHERE nspname = %s
                              AND proname = %s
                             GROUP BY proname, proargtypes, proargnames, p.prosrc
                           """
            uc.cur.execute(query_tables, [f'schema_{self.showcase.lower()}_core', self.func_name.strip()])
            func_code = uc.cur.fetchall()[0][0]

            tables = Counter()
            for func_owner_name in set(re.findall(pattern=r'(?:perform\s)(\w*.\w*)(?:\()', string=func_code)):
                uc.cur.execute(query_tables, [func_owner_name.split('.')[0], func_owner_name.split('.')[1]])
                tables.update(re.findall(pattern=r'(?:insert into\s)(\w*.\w*)', string=uc.cur.fetchall()[0][0]))
            target_table = tables.most_common(1)[0][0].split('.')[1]

            # Создаем файла data-product.
            data_product_file = get_path(uc.REPO_FOLDER_FLOW, "data-product.yml")
            new_data_product_file = get_path(self.flow_dir_name, "data-product.yml")

            self._logger.info('Начинаем создавать файл data-product')
            # В модели Python структура yml документа представляет собой словарь. Для работы с содержимым yml документа преобразуем его в словарь и
            # сохраним в памяти.
            with open(data_product_file, encoding='UTF-8') as old_data_product, open(new_data_product_file, 'w', encoding='UTF-8') as new_data_product:
                data_product_dict = yaml.safe_load(stream=old_data_product)

                # Изменяем содержимое словаря yml.
                key = ('data-product-name', 'flume_id', 'object_code')
                value = (self.long_flow_name, uc.config_flow.__getattribute__(self.showcase)['export_name'], self.showcase)
                key_val = zip(key, value)

                for item in data_product_dict['jdb_profile-list']:
                    item['jdbc-profile'] = uc.config_flow.__getattribute__(self.showcase)['space_profile']
                    item['jdbc-profile_name'] = uc.config_flow.__getattribute__(self.showcase)['space_id']
                    item['db_name'] = f'schema_{self.showcase.lower()}_core'

                for k, v in key_val:
                    data_product_dict[k] = v

                data_product_dict["flow-var-map"] = {f"p{k[0]}":'null' for k in self.args_iter}

                for item in data_product_dict["job-list"]:
                    item["job"] = f"job_{self.long_flow_name}"
                    for i in item["target-to-run-list"]:
                        i["target-ro-run"] = target_table
                        i["query-list"] = [f"run_{self.func_name}.sql"]

                yaml.dump(data=data_product_dict, stream=new_data_product, encoding='UTF-8', sort_keys=False, indent=5, allow_unicode=False)

        except yaml.YAMLError:
            self._logger.error('Ошибка при обработке документа yml', exc_info=True)
            showerror("ERROR!", 'Ошибка! Смотри логги.')
        except Exception:
            self._logger.error('Прочая ошибка', exc_info=True)
            showerror("ERROR!", 'Ошибка! Смотри логги.')

        else:
            self._logger.info('Создан файл data-product.yml')
            showinfo('SUCCESS!', 'Создан файл data-product.yml')
