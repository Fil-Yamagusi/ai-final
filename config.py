# top-secret passwords
from auth import _TB, _YANDEX

#
# Настройки самой программы
MAIN = {}
MAIN['test_mode'] = True
MAIN['log_filename'] = 'final_log.txt'
MAIN['db_filename'] = 'final_sqlite.db'

# **********************************************************
# Ну вы поняли, какие переменные надо задать в файле auth.py
# Telegram bot
TB = {}
TB['TOKEN'] = _TB['TOKEN']
TB['BOT_NAME'] = _TB['BOT_NAME']  # 'ИИ-помощник для планов на лето'
TB['BOT_USERNAME'] = _TB['BOT_USERNAME']  # 'fil_fc_ai_pa_bot'

# Yandex API
YANDEX = {}
YANDEX['GPT_MODEL'] = _YANDEX['GPT_MODEL']  # 'yandexgpt-lite'
YANDEX['FOLDER_ID'] = _YANDEX['FOLDER_ID']
YANDEX['IAM_TOKEN'] = _YANDEX['IAM_TOKEN']
# **********************************************************

#
# А вот тут уже несекретные настройки - ограничения по ИИ-ресурсам
LIM = {}
# Ограничения на проект
# Каждый пользователь использует все типы ресурсов, не дробим на GPT/STT/TTS
LIM['P_USERS'] = {
    'descr': 'max пользователей на весь проект',
    'value': 4, }
LIM['P_GPT_TOKENS'] = {
    'descr': 'max токенов (GPT) на весь проект',
    'value': 22222, }
LIM['P_TTS_SYMBOLS'] = {
    'descr': 'max символов (TTS) на весь проект',
    'value': 55555, }
LIM['P_STT_BLOCKS'] = {
    'descr': 'max блоков (STT) на весь проект',
    'value': 100, }

# Ограничения GPT на пользователя. Сессии оставляем на случай, если
# пользователь захочет переделать Список дел. Но прошлое-то хранить надо!
# По количеству сессий и токенов в них не ограничиваем. Только общий лимит.
LIM['U_GPT_TOKENS'] = {
    'descr': 'max токенов (GPT) во всех сессиях пользователя',
    'value': 5432, }
LIM['U_ASK_TOKENS'] = {
    'descr': 'max токенов в запросе пользователя к GPT',
    'value': 33, }
LIM['U_ANSWER_TOKENS'] = {
    'descr': 'max токенов в ответе пользователю от GPT',
    'value': 44, }

# Ограничения TTS и STT на пользователя
LIM['U_TTS_SYMBOLS'] = {
    'descr': 'max символов (TTS) на пользователя',
    'value': 7777, }
LIM['U_STT_BLOCKS'] = {
    'descr': 'max блоков (STT) на пользователя',
    'value': 30, }
