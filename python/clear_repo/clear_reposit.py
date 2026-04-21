"""
clear_reposit.py: в файле модуля выполняется очищение репозитория BitBucket от веток feature, в которых разработка была завершена более чем две недели
назад => срок релизного процесса. Такие ветки утрачивают необходимость, т.к они уже слиты в релизную ветку, которая слита в dev-ветку. Ввиду этого такие
ветки feature без их оперативного удаления будут засорять репозиторий BitBucket.
"""

import git, re, os, datetime as dt, logging as log
import userconfig.config as uc

def main():
    try:
        logger = crt_log(p_mode="w")
        logger.info(f"Начинаем удалять неактуальные feature ветки автора => {uc.FIO}")

        folders = (uc.GP_REPOSIT, uc.PG_REPOSIT, uc.DPFW_REPOSIT)
        for folder in folders:
            # Вызываем функцию для удаления feature-веток в каждом репозитории.
            if folder: delete_branch(p_repo=folder)

    except Exception:
        logger.error("Ошибка в функции main", exc_info=True)

    else:
        logger.info("Удаление неактуальных веток feature завершено")

def delete_branch(p_repo:str, p_fio=uc.FIO):
    """
    Функция для удаления веток feature, утративших актуальность. Ветки, подлежащие удалению, отбираются по критериям:
    1. Тип ветки должен быть feature.
    2. Последним коммитом ветки должно быть либо обычное сообщение, либо сообщение, в котором написано, что был выполнен merge из одной feature ветки в
    другую feature-ветку.
    3. Дата последнего коммита должна превышать 14 дней. 14 дней - это срок релизного процесса.
    4. Автором последнего коммита должен быть разработчик, запускающий программу.
    """
    try:
        logger = crt_log(p_mode="a")

        # Настраиваем часовой пояс для получения смещения во времени
        timezone = +3.0
        timezone_info = dt.timezone(dt.timedelta(hours=timezone))
        pat_repo = re.compile(pattern=r"\w*$")
        folder_name = pat_repo.search(string=p_repo).group()

        logger.info(f"Получаем ветки feature, утратившие актуальность и подлежащие удалению, в репозитории => {folder_name}")

        repo_obj = git.Repo(p_repo)
        remote = repo_obj.remote(name="origin")
        pat = r"(Merge in)(?:.*)(from feature/)(?:.*)(to feature/)"
        feature_branches = (branch for branch in repo_obj.remote().refs if "feature" in branch.name and (re.search(pat, branch.commit.message) or branch.commit.message)
                            and (dt.datetime.now(timezone_info) - branch.commit.committed_datetime).days == 0 and branch.commit.author.name == p_fio)

        logger.info(f"Выполняем удаление неактуальных веток feature в репозитории => {folder_name}")

        for branch_reff in feature_branches:
            remote.push(refspec=(":" + branch_reff.remote_head))
            logger.info(f"Удалили ветку => {branch_reff.name}")

    except Exception:
        logger.error(f"Ошибка при удалении неактуальных веток feature в репозитории => {folder_name}", exc_info=True)

    else:
        logger.info(f"Выполнили удаление неактуальных веток feature в репозитории => {folder_name}")

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

if __name__ == "__main__":
    main()