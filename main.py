#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-
"""2024-04-20 Fil - Future code Yandex.Practicum
Final AI-bot: GPT, STT, TTS
README.md for more

Fil FC Personal assistant
@fil_fc_ai_pa
https://t.me/fil_fc_ai_pa_bot
"""
__version__ = '0.1'
__author__ = 'Firip Yamagusi'


# standard
from time import time_ns, strftime
from random import randint

# third-party
import logging
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, Message

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM
from final_db import (
    get_db_connection,
    create_db,
    is_limit,
    create_user,
    update_user,
)

if MAIN['test_mode']:  # Настройки для этапа тестирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%F %T',
        level=logging.INFO,
    )
else:  # Настройки для опубликованного бота
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%F %T',
        level=logging.WARNING,
        filename=MAIN['log_filename'],
        filemode="w",
    )

# *******************************************************************
# ПОНЕСЛАСЬ! В АКАКУ!
logging.warning(f"MAIN: start")

# Подключаемся к БД и создаём таблицы (если не было). Без БД не сможем работать
db_conn = get_db_connection(MAIN['db_filename'])
if db_conn == False:
    exit(1)

logging.warning(f"MAIN: DB open connection")

r = create_db(db_conn)
if r == False:
    exit(2)

bot = TeleBot(TB['TOKEN'])
logging.warning(f"TB: start: {TB['BOT_NAME']} | {TB['TOKEN']}")

# Пустое меню, может пригодиться
hideKeyboard = ReplyKeyboardRemove()

# Словарь с пользователями в памяти, чтобы не мучить БД
user_data = {}


def check_user(m):
    """
    Проверка наличия записи для данного пользователя
    Проверка ограничений разных пользователей (MAX_USERS)
    """
    global user_data, db_conn

    user_id = m.from_user.id

    if user_id not in user_data:
        # Если пользователя нет в user_data, то нужно создать
        user_data[user_id] = {}
        user_data[user_id]['user_id'] = user_id
        # У некоторых пользователей ерунда в имени.
        user_data[user_id]['user_name'] = m.from_user.first_name
        user_data[user_id]['age'] = 20

        # но в БД добавим только с учётом ограчений из конфига
        if not create_user(db_conn, user_data[user_id]):
            bot.send_message(
                user_id,
                f"<b>ОШИБКА!</b>\n"
                f"По ТЗ ограничено количество пользователей!\n"
                f"Сейчас {LIM['P_USERS']['value']}/{LIM['P_USERS']['value']}. "
                f"Не могу для тебя создать запись",
                parse_mode="HTML",
                reply_markup=hideKeyboard)
            logging.warning("MAIN: check_user Can't create user! {user_id}")
            return False


@bot.message_handler(commands=['start'])
def handle_start(m: Message):
    """
    Обработчик команды /start
    Подсказка самого быстрого начала
    """
    user_id = m.from_user.id
    check_user(m)

    # Исходное приветствие
    bot.send_message(
        user_id,
        '✌🏻 <b>Привет! Я — бот с искусственным интеллектом.</b>\n\n'
        'Помогу тебе составить план дел на лето. Начни с команды /profile,'
        'а потом переходи к обсуждению новых дел: /idea\n\n'
        'Готовый список дел смотри в /show_plan\n\n'
        'Подробнее про все команды: /help',
        parse_mode='HTML',
        reply_markup=hideKeyboard)


@bot.message_handler(commands=['profile'])
def handle_profile(m: Message):
    """
    Обработчик команды /profile
    Пользователь укажет подробности о себе, чтобы ИИ-советы были полезнее
    """
    user_id = m.from_user.id
    check_user(m)

    # Исходное приветствие
    bot.send_message(
        user_id,
        'Сообщи текстом или голосом, сколько тебе лет. '
        'Можешь ответить просто '
        '<i>учусь в 10 классе</i> или <i>я на 2 курсе</i>.',
        parse_mode='HTML',
        reply_markup=hideKeyboard)
    bot.register_next_step_handler(m, process_profile)

def process_profile(m: Message):
    """
    пользователь сообщил текстом или голосом, сколько тебе лет.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    if m.voice:
        bot.send_message(
            user_id,
            f"process_profile ГОЛОСОМ {user_id}",
            reply_markup=hideKeyboard)
        file_id = m.voice.file_id
        print(f"{file_id}")
        file_info = bot.get_file(file_id)
        print(f"{file_info}")
        downloaded_file = bot.download_file(file_info.file_path)
        print(f"{downloaded_file}")

    if m.text:
        bot.send_message(
            user_id,
            f"process_profile ТЕКСТОМ {user_id}",
            reply_markup=hideKeyboard)

    user_data[user_id]['user_age'] = randint(12, 42)
    print(user_data[user_id])
    update_user(db_conn, user_data[user_id])


@bot.message_handler(commands=['idea'])
def handle_idea(m: Message):
    """
    Обработчик команды /idea
    Здесь в пошаговом режиме обсуждаем с ИИ новую идею.
    При необходимости добавляем её в список дел
    """
    user_id = m.from_user.id
    check_user(m)

    # Исходное приветствие
    bot.send_message(
        user_id,
        'Сейчас придумаем тебе новое задание на лето!\n\n'
        'Пришли текстом или голосом, чем ты увлекаешься. '
        'Например: <i>Я люблю кататься на велосипеде!</i>, '
        'а я предложу задание. '
        'Если оно тебе понравится, пришли '
        'Подробнее про все команды: /help',
        parse_mode='HTML',
        reply_markup=hideKeyboard)


@bot.message_handler(commands=['test_tts'])
def handle_test_tts(m: Message):
    """
    по ТЗ: пользователь вводит текст, а бот выдаёт аудио с озвучиванием текста.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    bot.send_message(
        user_id,
        f"test_tts",
        parse_mode='HTML',
        reply_markup=hideKeyboard)
    bot.register_next_step_handler(m, process_test_tts)


def process_test_tts(m: Message):
    """
    по ТЗ: пользователь вводит текст, а бот выдаёт аудио с озвучиванием текста.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    bot.send_message(
        user_id,
        f"process_test_tts",
        reply_markup=hideKeyboard)


@bot.message_handler(commands=['test_stt'])
def handle_test_stt(m: Message):
    """
    по ТЗ: пользователь отправляет аудио, а бот распознаёт текст.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    bot.send_message(
        user_id,
        f"test_stt",
        parse_mode='HTML',
        reply_markup=hideKeyboard)
    bot.register_next_step_handler(m, process_test_stt)


def process_test_stt(m: Message):
    """
    по ТЗ: пользователь отправляет аудио, а бот распознаёт текст.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    bot.send_message(
        user_id,
        f"process_test_stt",
        reply_markup=hideKeyboard)


# Запуск бота
try:
    bot.infinity_polling()
except urllib3.exceptions.ReadTimeoutError as e:
    logging.info(f"TB: Read timed out. (read timeout=25)")

logging.warning(f"TB: finish")

db_conn.close()
logging.warning(f"MAIN: DB close connection")

logging.warning(f"MAIN: finish")

#
#
# for limit in LIM.keys():
#     is_limit(db_conn,
#              param_name=limit,
#              user=user_data[666],
#              session_id=1)

# [print("MAIN", val) for val in MAIN]
# [print("TB", val) for val in TB]
# [print("YANDEX", val) for val in YANDEX]
# [print(val['descr'], val['value']) for val in LIM.values()]
