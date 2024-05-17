# top-secret passwords
from auth import _TB, _YANDEX

#
# HOME_DIR = '/home/student/ai-final/'  # путь к папке с проектом
HOME_DIR = ''  # путь к папке с проектом
IAM_TOKEN_PATH = f'{HOME_DIR}creds/iam_token.txt'  # файл для хранения iam_token
FOLDER_ID_PATH = f'{HOME_DIR}creds/folder_id.txt'  # файл для хранения folder_id
BOT_TOKEN_PATH = f'{HOME_DIR}creds/bot_token.txt'  # файл для хранения bot_token

#
# Настройки самой программы
MAIN = {}
MAIN['test_mode'] = True
MAIN['on_server'] = False
MAIN['log_filename'] = f'{HOME_DIR}final_log.txt'
MAIN['db_filename'] = f'{HOME_DIR}final_sqlite.db'

# **********************************************************
# Telegram bot
TB = {}
# до публикации на сервере простая инициализация
# TB['TOKEN'] = _TB['TOKEN']
TB['BOT_NAME'] = _TB['BOT_NAME']  # 'ИИ-помощник для планов на лето'
TB['BOT_USERNAME'] = _TB['BOT_USERNAME']  # 'fil_fc_ai_pa_bot'

# Yandex API
YANDEX = {}
YANDEX['GPT_MODEL'] = _YANDEX['GPT_MODEL']  # 'yandexgpt-lite'
# до публикации на сервере простая инициализация
# YANDEX['FOLDER_ID'] = _YANDEX['FOLDER_ID']
# YANDEX['IAM_TOKEN'] = _YANDEX['IAM_TOKEN']
YANDEX['MAX_ANSWER_TOKENS'] = 50  # длина от GPT в токенах
YANDEX['MAX_ASK_LENGTH'] = 45  # длина запроса к GPT в символах
# Системный промт, который объяснит нейросети, как правильно писать сценарий вместе с пользователем
YANDEX['SYSTEM_PROMPT'] = ("Ты помогаешь составлять список интересных заданий на лето. "
                           "Тебе сообщают увлечение, а ты придумай ровно одно подходящее и очень конкретное задание. "
                           "В ответе должно быть только само задание, без лишних слов! "
                           "Отвечай кратко, в одно-два предложения или 10-20 слов.")
# **********************************************************

#
# А вот тут уже несекретные настройки - ограничения по ИИ-ресурсам
LIM = {}
# Ограничения на проект
# Каждый пользователь использует все типы ресурсов, не дробим на GPT/STT/TTS
LIM['P_USERS'] = {
    'descr': 'max пользователей на весь проект',
    'value': 10, }
LIM['P_GPT_TOKENS'] = {
    'descr': 'max токенов (GPT) на весь проект',
    'value': 22222, }  # 22222
LIM['P_TTS_SYMBOLS'] = {
    'descr': 'max символов (TTS) на весь проект',
    'value': 55555, }  # 55555
LIM['P_STT_BLOCKS'] = {
    'descr': 'max блоков (STT) на весь проект',
    'value': 100, }

# Ограничения GPT на пользователя. Сессии оставляем на случай, если
# пользователь захочет переделать Список дел. Но прошлое-то хранить надо!
# По количеству сессий и токенов в них не ограничиваем. Только общий лимит.
LIM['U_GPT_TOKENS'] = {
    'descr': 'max токенов (GPT) во всех сессиях пользователя',
    'value': 5432, }  # 5432
LIM['U_ASK_TOKENS'] = {
    'descr': 'max токенов в запросе пользователя к GPT',
    'value': 33, }
LIM['U_ANSWER_TOKENS'] = {
    'descr': 'max токенов в ответе пользователю от GPT',
    'value': 44, }

# Ограничения TTS и STT на пользователя
LIM['U_TTS_SYMBOLS'] = {
    'descr': 'max символов (TTS) на пользователя',
    'value': 7777, }  # 7777
LIM['U_STT_BLOCKS'] = {
    'descr': 'max блоков (STT) на пользователя',
    'value': 30, }

# ****************************************************
# Большие списки
random_ideas = [
    'наблюдать за живой природой',
    'наблюдать за птицами',
    'наблюдать за насекомыми',
    'наблюдать за растениями',
    'путешествовать за городом',
    'бродить по лесу, собирать грибы-ягоды',
    'кататься на велосипеде',
    'гулять по историческому центру города',
    'заниматься спортом',
    'отдыхать на берегу водоёма',
    'отдыхать с друзьями на природе',
    'отдыхать с друзьями в парке',
    'ходить по музеям и выставкам',
    'помогать как волонтёр',
    'ходить на концерты',
    'ходить в театры',
    'фотографировать людей',
    'фотографировать природу и город',
    'наблюдать за звёздами',
    'проверять рецепты десертов',
    'проверять рецепты коктейлей',
    'проверять рецепты крутых блюд',
    'бродить под дождём',
    'изучать достопримечательности города',
    'изучать достопримечательности пригорода',
    'экспериментировать с причёской и стилем',
    'смотреть хорошие фильмы',
    'есть вкусные летние фрукты и ягоды',
    'есть арбузы и дыни',
    'кататься на лодке или SUP',
    'играть в волейбол',
    'играть в футбол',
    'играть в настольный теннис',
    'мастерить своими руками',
    'собирать Лего',
    'веселиться в аквапарке',
    'веселиться в парке аттракционов',
    'собирать паззлы',
    'настольные игры с друзями',
    'рисовать красками',
    'кататься на теплоходе',
    'играть в компьютерные игры',
    'кататься на лошади',
    'менять обстановку в комнате',
    'рукоделие, хэнд-мейд',
    'снимать видео о своих приключениях',
    'вести блог о своих приключениях',
    'рисовать комиксы',
    'взламывать аккаунты своих друзей',
    'постить в википедию фальшивые факты',
    'рисовать граффити в лифтах',
    'шляться без дела по торговому центру',
    'ломать детские куличики в песочнице',
    'ставить одну звезду всем топовым фильмам',
    'троллить людей в соцсетях',
]
