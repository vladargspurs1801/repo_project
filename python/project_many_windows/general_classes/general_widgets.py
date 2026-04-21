"""
Модуль general_widgets.py.
В этом модуле определены классы для создания общих виджетов, используемых обоими приложениями GUI.
"""
from logging import Logger
import tkinter as tk
from tkinter.font import Font
import git, os, re
from json import dumps
from tkinter.messagebox import showinfo, showerror, showwarning
import userconfig.config as uc
import requests as req
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup

def get_path(p_path:str, p_folder:str) -> str:
    """Функция возвращает файловый путь до нужной директории"""
    return os.path.join(p_path, p_folder)

class TextFont:
    """Класс для создания шрифтов"""
    def __init__(self):
        self.custom_font = Font(family='Centro Sans pro', size=15, weight='bold')
        self.custom_font_2 = Font(family='Times New Roman', size=12, underline=True)
        self.custom_font_3 = Font(family='Arial', size=10)

class PromtLabel:
    """Класс для фрейма и виджета заголовка."""
    def __init__(self, p_frame:tk.Tk, p_tittle:str):
        self.tittle = p_tittle
        self.font = TextFont()
        self.promt_label = tk.Label(p_frame, text=self.tittle, font=self.font.custom_font)
        self.promt_label.pack(padx=30, pady=30)

class GitFrame:
    """Класс, создающий виджеты для работы с git"""
    def __init__(self, p_frame:tk.Tk, p_logger:Logger, p_tech_stack:str):
        self.font = TextFont()
        self._logger = p_logger

        self.commit_frame = tk.Frame(p_frame)
        self.commit_frame.pack(padx=20)

        self.commit_label = tk.Label(self.commit_frame, text='Введите сообщение коммита: ', font=self.font.custom_font_2)
        self.commit_label.pack(side='left', padx=5, pady=20)

        self.commit_entry = tk.Entry(self.commit_frame, width=60)
        self.commit_entry.pack(side='left', padx=5, pady=20)

        self.commit_button = tk.Button(self.commit_frame, text='git push', command=self.git_push)
        self.commit_button.pack(side='right', padx=5, pady=5)

        if p_tech_stack == 'FLOW':
            self.repo_obj = git.Repo(uc.REPO_FOLDER_FLOW)
        elif p_tech_stack == 'GP':
            self.repo_obj = git.Repo(uc.REPO_FOLDER_GP)

    def git_push(self):
        """Обратный вызов для кнопки commit_button. Выполняется индексирование, проверка статуса, сохранение и отправка изменений в удаленный репозиторий."""
        try:
            self.repo_obj.git.add(all=True)
            comment = self.commit_entry.get().strip()
            self.repo_obj.index.commit(comment)

            self._logger.info(f'Изменения сохранились. Статус => {self.repo_obj.git.status()}. Отправляем изменения в BitBucket.')
            remote_name = 'origin'
            self.repo_obj.remote(remote_name).push(self.repo_obj.active_branch.name)

        except git.CommandError:
            self._logger.error('Ошибка при выполнении работы с git', exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')
        except Exception:
            self._logger.error('Ошибка в Python', exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')

        else:
            self._logger.info('Изменения были перенесены в BitBucket.')
            showinfo('SUCCESS!', 'Изменения были перенесены в BitBucket')

class Quit:
    """Класс, создающий виджет кнопки выхода из GUI."""
    def __init__(self, p_frame:tk.Tk):
        self.quit_frame = tk.Frame(p_frame)
        self.quit_frame.pack(padx=20)

        self.quit_but = tk.Button(p_frame, text='Выйти', command=p_frame.destroy)
        self.quit_but.pack(side='top', padx=35, pady=10)

class BitbucketFrame:
    """Класс, генерирующий виджеты для создания пулл реквеста в удаленный репозиторий БитБакет"""
    def __init__(self, p_frame:tk.Tk, p_tech_stack:str, p_logger:Logger, p_branch_name:str):
        self._logger = p_logger
        self.tech_stack = p_tech_stack
        self.branch_name = p_branch_name
        self.font = TextFont()

        self.bit_bucket_frame = tk.Frame(p_frame)
        self.bit_bucket_frame.pack(side='left', padx=20)

        self.bit_bucket_label = tk.Label(self.bit_bucket_frame, text='Введите наименование ветки from: ', font=self.font.custom_font_2)
        self.bit_bucket_label.pack(side='left', padx=5, pady=20)

        self.bit_bucket_entry = tk.Entry(self.bit_bucket_frame, width=60)
        self.bit_bucket_entry.pack(side='left', padx=5, pady=20)

        self.bit_bucket_button = tk.Button(self.bit_bucket_frame, text='Создать пулл реквест', command=self.create_pull_request)
        self.bit_bucket_button.pack(side='left', padx=35, pady=10)

    def create_pull_request(self):
        """Обратный вызов для кнопки bit_bucket_button. Создает пулл реквест из ветки, в которой выполняется работа, в другую ветку."""
        try:
            HEADERS = {"Content-Type":"application/json"} # Передаем данные в формате json для создания post запроса

            if self.tech_stack == 'GP':
                repository_name = 'project_gp'
            elif self.tech_stack == 'FLOW':
                repository_name = 'project_flow'

            url = rf"https:/stash.sirius.project.ru/rest/api/9.5/projects/{uc.PROJECT_NAME}/repository/{repository_name}/pull-requests"

            parent_branch = self.bit_bucket_entry.get()

            # Формируем данные для создания пулл реквеста. Данные должны иметь структуру json.
            pr_parameters = {
                               "tittle": "Проверка перед слиянием",
                               "description": "Слияние доработок",
                               "fromeRef": {
                                "id": f"refs/heads/{self.branch_name}",
                                     "repository": {
                                         "slug": repository_name,
                                         "project": {
                                         "key": uc.PROJECT_NAME
                                         }
                                     }
                                     },
                                     "toRef": {
                                     "id": f"refs/heads/{parent_branch}",
                                     "repository": {
                                         "slug": repository_name,
                                         "project": {
                                         "key": uc.PROJECT_NAME
                                         }
                                     }
                                     },
                                     "close_source_branch": False,
                                     "reviewers": [
                                                     {
                                                        "user": {
                                                                  "name": f"{uc.DELTA_USERNAME}"
                                                                 }
                                                     }
                                                  ]
                            }
            self._logger.info(f"Начинаем создавать пулл реквест из ветки {self.branch_name} в ветку {parent_branch}")
            response = req.post(url, headers=HEADERS, data=dumps(pr_parameters), auth=uc.BITBUCKET_AUTH, verify=False)

        except req.HTTPError:
            self._logger.error("Ошибка при выполнении post запроса", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логги.")
        except Exception:
            self._logger.error(f"Ошибка в Python", exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')

        else:
            if response.status_code in (200, 201):
                self._logger.info("Пулл реквест создан")
                showinfo("SUCCESS!", "Пулл реквест создан")
            else:
                self._logger.warning(f"Пулл реквест не создан. Код запроса => {response.status_code}")
                showwarning("WARNING!", "Пулл Реквест не создан! Смотри логги.")

class DeleteBranchFrame:
    """Класс, создающий виджеты для удаления ветки."""
    def __init__(self, p_repo_obj:git.Repo, p_logger:Logger, p_branch_name:str, p_frame:tk.Frame):
        self._logger = p_logger
        self.branch_name = p_branch_name
        self.repo_obj = p_repo_obj

        self.del_branch_frame = tk.Frame(p_frame)
        self.del_branch_frame.pack(padx=20)

        self.del_branch_button = tk.Button(self.del_branch_frame, text='Удалить ветку', command=self.del_branch)
        self.del_branch_button.pack(side='left', padx=35, pady=15)

    def del_branch(self):
        """Обратный вызов для кнопки del_branch_button. Удаляет ветку, в которой выполнялась разработка, из локального и удаленного репозиториев."""
        try:
            self._logger.info("Получаем ссылку на соединение с удаленным репозиторием origin и ветку, связанную с origin")
            remote = self.repo_obj.remote(name='origin')
            branch = self.repo_obj.remote().refs[self.branch_name]

            self._logger.info(f"Начинаем удалять ветку => {self.branch_name}")
            remote.push(refspec=(':' + branch.remote_head))

        except git.GitError:
            self._logger.error(f"Ошибка в удалении ветки", exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')
        except Exception:
            self._logger.error('Ошибка в Python', exc_info=True)
            showerror('ERROR!', 'Ошибка! Смотри логги.')

        else:
            self._logger.info(f"Удалили ветку => {self.branch_name}")
            showinfo('SUCCESS!', 'Ветка удалена')

class VersionPipeline:
    """
    Класс, создающий виджеты для проверки номера сборки дистрибутива. Также выполняется создание и запуск джобы pipeline jenkins.
    """
    def __init__(self, p_logger:Logger, p_frame:tk.Tk, p_tech_stack:str, p_branch_name:str):
        self._logger = p_logger
        self.tech_stack = p_tech_stack
        self.branch_name = p_branch_name
        self.font = TextFont()

        self.version_frame = tk.Frame(p_frame)
        self.version_frame.pack(padx=20)

        self.version_label = tk.Label(self.version_frame, text='Введите номер сборки: ', font=self.font.custom_font_2)
        self.version_label.pack(side='left', padx=5, pady=20)

        self.version_entry = tk.Entry(self.version_frame, width=60)
        self.version_entry.pack(side='left', padx=5, pady=20)

        self.version_button = tk.Button(self.version_frame, text='Проверить номер сборки и запустить джобу', command=self.check_version_crt_job)
        self.version_button.pack(side='left', padx=35, pady=10)

    def get_install(self, p_version:str):
        """
        Метод, выполняющий сборку и запуск джобы pipeline jenkins.
        """
        try:
            # Выполняем сборку джобы pipeline jenkins с последующим накатом на дев-стенд.
            uc.JEN_URL = r''

            # Параметры джобы.
            jen_parameters = {
                "gitRepo": fr"ssh://git@hoop/{'project_flow' if self.tech_stack == 'FLOW' else 'project_gp'}.git",
                "branch": self.branch_name,
                "Inventory": "project_flow" if self.tech_stack == "FLOW" else "project_gp",
                "InstallGreenPlum": "False" if self.tech_stack == "FLOW" else "True",
                "InstallFlow": "True" if self.tech_stack == "FLOW" else "False",
                "version":p_version,
                "emails": uc.EMAIL
            }

            # Получаем строку параметров для сборки джобы.
            parameters = ''
            for (key, value) in jen_parameters.items():
                item = f'{key}={value}&'
                parameters += item

            self._logger.info(f'Запускается джоба наката')
            self._logger.info(f'Параметры джобы наката => {parameters}')

            # Запускаем джобу.
            response = req.post(f'{uc.JEN_URL}/buildWithParameters?{parameters.rstrip("&")}', auth=uc.JENKINS_AUTH,
                                headers=None, verify=False)

        except req.HTTPError:
            self._logger.error('Ошибка в работе с http методами', exc_info=True)
        except Exception:
            self._logger.error("Прочая ошибка", exc_info=True)

        else:
            if response.status_code != 201:
                self._logger.warning(f'Не удалось запустить джобу наката. Код => {response.status_code}')
                showwarning("WARNING!", 'Джоба не запущена. Смотри логи')
            else:
                self._logger.info("Джоба собрана и запущена")
                showinfo("SUCCESS!", "Джоба запущена")

    def check_version_crt_job(self):
        """
        Обратный вызов для кнопки version_button. Выполняет проверку номера сборки дистрибутива и запускает джобу для сборки дистрибутива и наката на
        стенд дев.
        """
        try:
            # Получаем номер сборки.
            version = self.version_entry.get()
            self._logger.info('Проверяем номер сборки дистрибутива.')

            # Здесь хранятся все номера сборок релизных дистрибутивов по техническим стекам GreenPlum и Flow.
            url_version = fr"https://.../distribut-release/CD159357/{'GP' if self.tech_stack == 'GP' else 'FLOW'}/PROD/CD159357/metadata.xml"

            # Обращаемся к метаданным.
            response_version = req.get(url_version, auth=(uc.DELTA_USERNAME, uc.DELTA_PASSWORD), verify=False)

            # Проверяем, что запрос вернул результат.
            if response_version.status_code in (200, 201):

                # Начинаем обработку xml.
                file = BeautifulSoup(response_version.text, features="xml")

                # Проверяем, является ли полученный номер сборки новым. Или он был ранее создан.
                for item in file.find("versions"):
                    if version in item:
                        showwarning("WARNING", f"Номер сборки {version} ранее был создан")

                        # Находим последнюю версию сборки для номера дистрибутива.
                        vers_under = re.search(pattern=r"\d.\d+\.", string=version)[0]
                        lst_1 = (str(ver) for ver in file.find("versions") if str(ver).startswith(f"<version>{vers_under}"))
                        max_version = max((int(re.search(pattern=r"\d+<", string=text)[0].replace("<", "")) for text in lst_1))
                        showinfo("INFO", f"Последний номер сборки => {max_version}. Выберите сборку {max_version+1} и повторите ввод.")
                        self._logger.info("Номер сборки проверен.")
                        break

                    else:
                        showinfo("INFO", "Такого номера сборки нет. Джоба будет запущена.")
                        self._logger.info("Номер сборки проверен.")
                        self._logger.info("Начинается создание джобы jenkins для сборки дистрибутива и наката на дев стенд.")
                        # Используем вызов связанных методов.
                        self.get_install(p_version=version)
                        break
            else:
                self._logger.warning(f"Не получилось обратиться к метаданным. Статус => {response_version.status_code}")
                showwarning("WARNING", "Не получилось проверить номер сборки и запустить джобу. Смотри логи.")

        except req.HTTPError:
            self._logger.error("Ошибка в работе с get запросом для обращения к метаданным и получения номера сборки.", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логи.")
        except Exception:
            self._logger.error("Прочая ошибка", exc_info=True)
            showerror("ERROR!", "Ошибка! Смотри логи.")