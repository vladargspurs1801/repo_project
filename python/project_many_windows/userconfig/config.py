"""
Модуль хранит данные пользователя для настроек. Все значения для переменных выдуманы.
"""
# Для создания пулл реквеста в битбакете.
PROJECT_NAME = 'KARP-1899'
DELTA_USERNAME = '123456789'
DELTA_PASSWORD = 'AbcdefgH123'
BITBUCKET_AUTH = (DELTA_USERNAME, DELTA_PASSWORD)

# Для работы с локальным репозиторием.
REPO_FOLDER_GP = r'C:\Users\123456789\repo_gp\reposit_gp'
REPO_FOLDER_FLOW = r'C:\Users\123456789\repo_flow\reposit_flow'

# Для сборки джобы в дженкинсе.
EMAIL = 'vlad_arg@mail.ru'
JENKINS_TOKEN = '1a2b3c4e5t6y8q963'
JENKINS_AUTH = (DELTA_USERNAME, JENKINS_TOKEN)
JEN_URL = r''

# Для подключения к БД GreenPlum
import psycopg2 as ps
with ps.connect(user=DELTA_USERNAME, password=DELTA_PASSWORD, host='....', port='...', database='project_exam') as con:
    cur = con.cursor()

# Настройки витрин.
from collections import namedtuple
Config_Flow = namedtuple(typename='Config_Flow', field_names=['SVD_KB_PROJECT_CLASS', 'SVD_KB_PROJECT_EXAM', 'SVD_KB_PROJECT_TOP'])
config_flow = Config_Flow(SVD_KB_PROJECT_CLASS=dict(space_id='PROJECT_CLASS_159GY-YE159', export_name='GP_CLASS', space_profile='__CLASS_USER__'),
                          SVD_KB_PROJECT_EXAM=dict(space_id='PROJECT_EXAM_382GY-YE028', export_name='GP_PROJECT', space_profile='__PROJECT_USER__'),
                          SVD_KB_PROJECT_TOP=dict(space_id='PROJECT_TOP_759GY-YE173', export_name='GP_TOP', space_profile='__TOP_USER__')
                         )
# Для сборки дистрибутива GreenPlum.
function_folder = ''
meta_folder = ''