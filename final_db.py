#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-
"""2024-04-20 Fil - Future code Yandex.Practicum
Final AI-bot: GPT, STT, TTS
README.md for more

SQLite DB functions
"""
__version__ = '0.1'
__author__ = 'Firip Yamagusi'

# standard
from time import time_ns, time, strftime
import logging
import sqlite3
from os import remove

# third-party

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM


def get_db_connection(db_file: str) -> sqlite3.Connection:
    """
    Получаем соединение с БД
    """
    try:
        db_conn = sqlite3.connect(db_file, check_same_thread=False)
    except Exception as e:
        logging.error(f"DB: get_db_connection: {e}")
        return False

    return db_conn


def create_db(db_conn):
    """
    Создаём все таблицы. ИИ-ресурсы учитываем раздельно
    """
    cursor = db_conn.cursor()

    # Пользователи
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Users ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER NOT NULL, '
        'user_name TEXT NOT NULL, '
        'datetime TEXT NOT NULL, '
        'user_age INTEGER NOT NULL'
        ')'
    )

    # Сессии пользователей
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Sessions ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER NOT NULL, '
        'datetime TEXT NOT NULL, '
        'task TEXT NOT NULL, '
        'answer TEXT'
        ')'
    )

    # Обращения к GPT в пределах сессии
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Prompts ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER NOT NULL, '
        'session_id INTEGER NOT NULL, '
        'datetime TEXT NOT NULL, '
        'role TEXT, '
        'content TEXT, '
        'tokens INT'
        ')'
    )

    # Обращения к TTS - SpeechKit синтез речи
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS TTS ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER NOT NULL, '
        'datetime TEXT NOT NULL, '
        'content TEXT, '
        'symbols INT'
        ')'
    )

    # Создаем таблицу к STT - SpeechKit распознавание речи
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS STT ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER NOT NULL, '
        'datetime TEXT NOT NULL, '
        'content TEXT, '
        'blocks INT'
        ')'
    )

    # Список дел на лето - ради чего мы здесь осбрались
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Plan ('
        'id INTEGER PRIMARY KEY, '
        'user_id INTEGER NOT NULL, '
        'datetime TEXT NOT NULL, '
        'content TEXT, '
        'is_finished INT DEFAULT 0'
        ')'
    )

    # Звуковые файлы для удаления
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Files2Remove ('
        'id INTEGER PRIMARY KEY, '
        'user_id INTEGER NOT NULL, '
        'file_path TEXT NOT NULL, '
        'timens_added INTEGER NOT NULL'
        ')'
    )

    try:
        r = db_conn.commit()
    except Exception as e:
        logging.error(f"DB: get_db_connection: {e}")
        return False

    return r


def is_limit(db_conn, **kwargs):
    """
    Возвращает кортеж: (Превышен ли лимит, текущее значение)
    Пробуем все проверки в одной функции сделать
    user - про кого спрашиваем, но иногда это не надо
    """
    global LIM
    # Для некоторых проверок нужны параметры, достаём их из kwargs
    param_name = kwargs.get('param_name', None)

    user = kwargs.get('user', None)
    if isinstance(user, dict):
        user_id = user['user_id']

    session_id = kwargs.get('session_id', None)

    param = LIM[param_name]

    cursor = db_conn.cursor()
    # Чаще всего передаём в запрос user_id
    data = tuple()

    # LIM['P_USERS'] = {
    #     'name': 'max пользователей на весь проект',
    #     'value': 13, }
    if param_name == 'P_USERS':
        query = 'SELECT COUNT(DISTINCT user_id) FROM Users;'

    # LIM['P_GPT_TOKENS'] = {
    #     'name': 'max токенов (GPT) на весь проект',
    #     'value': 22222, }
    if param_name == 'P_GPT_TOKENS':
        query = ('SELECT SUM(max_tokens) FROM '
                 '(SELECT MAX(tokens) AS max_tokens '
                 'FROM Prompts '
                 'GROUP BY session_id) AS max_tokens_by_session;')

    # LIM['P_TTS_SYMBOLS'] = {
    #     'name': 'max символов (TTS) на весь проект',
    #     'value': 55555, }
    if param_name == 'P_TTS_SYMBOLS':
        query = 'SELECT sum(symbols) FROM TTS;'

    # LIM['P_STT_BLOCKS'] = {
    #     'name': 'max блоков (STT) на весь проект',
    #     'value': 100, }
    if param_name == 'P_STT_BLOCKS':
        query = 'SELECT sum(blocks) FROM STT;'
    #
    # # Ограничения GPT на пользователя
    # LIM['U_GPT_TOKENS'] = {
    #     'name': 'max токенов (GPT) во всех сессиях пользователя',
    #     'value': 5432, }
    if param_name == 'U_GPT_TOKENS':
        query = ('SELECT SUM(max_tokens) FROM '
                 '(SELECT MAX(tokens) AS max_tokens '
                 'FROM Prompts '
                 'WHERE user_id = ?'
                 'GROUP BY session_id) AS max_tokens_by_session;')
        data = (user_id,)

    # LIM['U_ASK_TOKENS'] = {
    #     'name': 'max токенов в запросе пользователя',
    #     'value': 33, }
    # Это константа, запрос к БД фиктивный
    if param_name == 'U_ASK_TOKENS':
        query = ('SELECT Null')

    # LIM['U_ANSWER_TOKENS'] = {
    #     'name': 'max токенов в ответе пользователю',
    #     'value': 44, }
    if param_name == 'U_ANSWER_TOKENS':
        query = ('SELECT Null')
    #
    # # Ограничения TTS и STT на пользователя
    # LIM['U_TTS_SYMBOLS'] = {
    #     'name': 'max символов (TTS) на пользователя',
    #     'value': 7777, }
    if param_name == 'U_TTS_SYMBOLS':
        query = ('SELECT sum(symbols) FROM TTS WHERE user_id = ?;')
        data = (user_id,)

    # LIM['U_STT_BLOCKS'] = {
    #     'name': 'max блоков (STT) на пользователя',
    #     'value': 30, }
    if param_name == 'U_STT_BLOCKS':
        query = ('SELECT sum(blocks) FROM STT WHERE user_id = ?;')
        data = (user_id,)

    try:
        cursor.execute(query, data)
        res = cursor.fetchone()
    except Exception as e:
        logging.error(f"DB: is_limit {param_name} {e}")

    if res is None:
        r, rr = False, 0
    elif res[0] is None:
        r, rr = False, 0
    else:
        r, rr = res[0] >= param['value'], res[0]
    logging.debug(f"DB: {param_name} is_limit = {r}: "
                  f"{rr} / {param['value']} ({param['descr']})")

    return r, rr


def create_user(db_conn, user):
    """
    Добавляем пользователя в БД с учётом ограничений
    """

    user_id = user['user_id']
    query = 'SELECT id FROM Users WHERE user_id = ?;'
    cursor = db_conn.cursor()
    cursor.execute(query, (user_id,))
    res = cursor.fetchone()

    # Если такой уже есть, то всё отлично, пускай пользуется
    if res is not None:
        logging.debug(f"DB: create_user: user {user_id} already exists")
        return True

    # Если такого нет, но превышено число пользователей на проект
    if is_limit(db_conn, param_name='P_USERS', user=user):
        logging.debug(f"DB: create_user: Can't create! Limit! {user_id}")
        return False
    else:
        query = ('INSERT INTO Users '
                 '(user_id, user_name, datetime) '
                 'VALUES (?, ?, ?);')
        cursor.execute(query,
                       (user['user_id'], user['user_name'], strftime('%F %T')))
        db_conn.commit()
        logging.warning(f"DB: create_user: New user is created {user_id}")
        return True


def update_user(db_conn, user):
    """
    Обновляем данные о пользователе
    """
    query = ('UPDATE Users '
             'SET user_name = ?, user_age = ? '
             'WHERE user_id = ?;')
    cursor = db_conn.cursor()
    cursor.execute(query,
                   (user['user_name'], user['user_age'], user['user_id']))
    db_conn.commit()


def add_file2remove(db_conn, user, file_path):
    """
    Добавить файл в очередь на удаление, удалить старые
    """

    cursor = db_conn.cursor()
    query = ('INSERT INTO Files2Remove '
             '(user_id, file_path, timens_added) '
             'VALUES (?, ?, ?);')
    cursor.execute(query, (user['user_id'], file_path, time_ns()))

    old = time_ns() - 10 ** 9  # старше 1000 секунд
    query = (f"SELECT id, file_path FROM Files2Remove WHERE "
             f"timens_added <= {old} AND timens_deleted IS NULL;")
    cursor.execute(query)
    res = cursor.fetchall()
    if res is not None:
        for r in res:
            try:
                remove(r[1])
                cursor.execute(f"DELETE FROM Files2Remove WHERE id={r[0]};")
            except Exception as e:
                logging.error(f"Error while deleting {r[0]} {r[1]}")

    db_conn.commit()
