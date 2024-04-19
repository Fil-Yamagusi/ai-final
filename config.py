from auth import _TB, _YANDEX

# **********************************************************
# Ну вы поняли, какие переменные надо задать в файле auth.py
# Telegram bot
TB = {}
TB['TOKEN'] = _TB['TOKEN']
TB['BOT_NAME'] = _TB['BOT_NAME']  # 'Fil FC Personal assistant'

# Yandex API
YANDEX = {}
YANDEX['GPT_MODEL'] = _YANDEX['GPT_MODEL']  # 'yandexgpt-lite'
YANDEX['FOLDER_ID'] = _YANDEX['FOLDER_ID']
YANDEX['IAM_TOKEN'] = _YANDEX['IAM_TOKEN']
# **********************************************************

#
# А вот тут уже несекретные настройки - ограничения по токенам-шмокенам
LIM = {}  # limits
# Ограничения на проект
LIM['P_USERS'] = {
    'name': 'max пользователей на весь проект',
    'value': 13, }
LIM['P_GPT_TOKENS'] = {
    'name': 'max токенов (GPT) на весь проект',
    'value': 22222, }
LIM['P_TTS_SYMBOLS'] = {
    'name': 'max символов (TTS) на весь проект',
    'value': 55555, }
LIM['P_STT_BLOCKS'] = {
    'name': 'max блоков (STT) на весь проект',
    'value': 100, }

# Ограничения GPT на пользователя
LIM['U_GPT_SESSIONS'] = {
    'name': 'max сессий (GPT) на пользователя',
    'value': 22, }
LIM['U_GPT_TOKENS_IN_SESSION'] = {
    'name': 'max токенов (GPT) в одной сессии пользователя',
    'value': 999, }
LIM['U_ASK_TOKENS'] = {
    'name': 'max токенов в запросе пользователя',
    'value': 33, }
LIM['U_ASK_TOKENS'] = {
    'name': 'max токенов в ответе пользователю',
    'value': 44, }

# Ограничения TTS и STT на пользователя
LIM['U_TTS_SYMBOLS'] = {
    'name': 'max символов (TTS) на пользователя',
    'value': 7777, }
LIM['U_STT_BLOCKS'] = {
    'name': 'max блоков (STT) на пользователя',
    'value': 15, }
