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
        'datetime TEXT NOT NULL '
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

    try:
        r = db_conn.commit()
    except Exception as e:
        logging.error(f"DB: get_db_connection: {e}")
        return False

    return r


def is_limit(db_conn, **kwargs):
    """
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
        r, rr = False, None
    elif res[0] is None:
        r, rr = False, None
    else:
        r, rr = res[0] >= param['value'], res[0]
    logging.debug(f"DB: {param_name} is_limit = {r}: "
                  f"{rr} / {param['value']} ({param['descr']})")

    return r


def create_user(db_conn, user):
    """
    Пробуем все проверки в одной функции сделать
    user - про кого спрашиваем, но иногда это не надо
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


def get_total_symbols(db_connection) -> int:
    """
    Сколько уже потрачено символов синтеза речи всеми пользователями
    """
    cursor = db_connection.cursor()
    query = ('SELECT sum(symbols) FROM TTS;')

    try:
        cursor.execute(query)
        res = cursor.fetchone()

        # Считаем, пустой результат - это отсутствие пользователя, а не ошибка
        if res[0] is None:
            # print(f"get_total_symbols None = 0")
            logging.warning(f"get_total_symbols None = 0")
            return 0
        else:
            # print(f"get_total_symbols {res[0]}")
            logging.warning(f"All users have {res[0]} symbols")
            return res[0]
    except Exception as e:
        return 0


def get_total_blocks(db_connection) -> int:
    """
    Сколько уже потрачено блоков распознавания текста всеми пользователями
    """
    cursor = db_connection.cursor()
    query = ("SELECT sum(blocks) FROM STT WHERE model='SpeechKit';")

    try:
        cursor.execute(query)
        res = cursor.fetchone()

        # Считаем, пустой результат - это отсутствие пользователя, а не ошибка
        if res[0] is None:
            # print(f"get_total_blocks None = 0")
            logging.warning(f"get_total_blocks None = 0")
            return 0
        else:
            # print(f"get_total_blocks {res[0]}")
            logging.warning(f"All users have {res[0]} blocks")
            return res[0]
    except Exception as e:
        return 0


def get_user_symbols(db_connection, user) -> int:
    """
    Сколько уже потрачено символов синтеза речи у пользователя
    """
    cursor = db_connection.cursor()
    query = ('SELECT sum(symbols) FROM TTS '
             'WHERE user_id = ?;')

    try:
        cursor.execute(query, (user['user_id'],))
        res = cursor.fetchone()

        # Считаем, пустой результат - это отсутствие пользователя, а не ошибка
        if res[0] is None:
            # print(f"get_user_symbols None = 0")
            logging.warning(f"get_user_symbols None = 0")
            return 0
        else:
            # print(f"get_user_symbols {res[0]}")
            logging.warning(f"User {user['user_id']} "
                            f"has {res[0]} symbols")
            return res[0]
    except Exception as e:
        return 0


def get_user_blocks(db_connection, user) -> int:
    """
    Сколько уже потрачено блоков распознавания речи у пользователя
    """
    cursor = db_connection.cursor()
    query = ("SELECT sum(blocks) FROM STT "
             "WHERE user_id = ? AND model='SpeechKit';")

    try:
        cursor.execute(query, (user['user_id'],))
        res = cursor.fetchone()

        # Считаем, пустой результат - это отсутствие пользователя, а не ошибка
        if res[0] is None:
            # print(f"get_user_blocks None = 0")
            logging.warning(f"get_user_blocks None = 0")
            return 0
        else:
            # print(f"get_user_blocks {res[0]}")
            logging.warning(f"User {user['user_id']} "
                            f"has {res[0]} blocks")
            return res[0]
    except Exception as e:
        return 0


def get_user_tts_requests(db_connection, user) -> int:
    """
    Сколько запросов на синтез речи у пользователя
    """
    cursor = db_connection.cursor()
    query = ('SELECT COUNT(id) FROM TTS '
             'WHERE user_id = ?;')

    try:
        cursor.execute(query, (user['user_id'],))
        res = cursor.fetchone()

        # Считаем, пустой результат - это отсутствие пользователя, а не ошибка
        if res[0] is None:
            # print(f"get_user_tts_requests None = 0")
            logging.warning(f"get_user_tts_requests None = 0")
            return 0
        else:
            # print(f"get_user_tts_requests {res[0]}")
            logging.warning(f"User {user['user_id']} "
                            f"has {res[0]} tts requests")
            return res[0]
    except Exception as e:
        return 0


def get_user_stt_requests(db_connection, user) -> int:
    """
    Сколько запросов на распознавание речи у пользователя
    """
    cursor = db_connection.cursor()
    query = ("SELECT COUNT(id) FROM STT "
             "WHERE user_id = ? AND model='SpeechKit';")

    try:
        cursor.execute(query, (user['user_id'],))
        res = cursor.fetchone()

        # Считаем, пустой результат - это отсутствие пользователя, а не ошибка
        if res[0] is None:
            # print(f"get_user_stt_requests None = 0")
            logging.warning(f"get_user_stt_requests None = 0")
            return 0
        else:
            # print(f"get_user_stt_requests {res[0]}")
            logging.warning(f"User {user['user_id']} "
                            f"has {res[0]} stt requests")
            return res[0]
    except Exception as e:
        return 0


def is_limit_symbols(db_connection, user_id):
    """
    Не превысили количество символов для пользователя?
    """
    global MAX_USER_SYMBOLS

    return get_user_symbols(db_connection, user_id) >= MAX_USER_SYMBOLS


def is_limit_blocks(db_connection, user_id):
    """
    Не превысили количество символов для пользователя?
    """
    global MAX_USER_STT_BLOCKS

    return get_user_blocks(db_connection, user_id) >= MAX_USER_STT_BLOCKS


def is_limit_total_symbols(db_connection):
    """
    Не превысили количество символов для всех пользователей?
    """
    global MAX_PROJECT_SYMBOLS

    return get_total_symbols(db_connection) >= MAX_PROJECT_SYMBOLS


def is_limit_total_blocks(db_connection):
    """
    Не превысили количество блоков для всех пользователей?
    """
    global MAX_PROJECT_STT_BLOCKS

    return get_total_blocks(db_connection) >= MAX_PROJECT_STT_BLOCKS


def is_limit_tokens_in_session(db_connection, user, t):
    """
    Можно ли ещё t токенов потратить?
    """
    global MAX_TOKENS_IN_SESSION

    return (MAX_TOKENS_IN_SESSION <=
            (get_tokens_in_session(db_connection, user) + t))


def insert_tokenizer_info(db_connection, user, content, tokens):
    """
    Функция для добавления нового пользователя в базу данных.
    """
    cursor = db_connection.cursor()
    logging.warning(f"Asking tokenizer for user_id={user['user_id']}... ")
    data = (
        user['user_id'],
        user['session_id'],
        time_ns(),
        content,
        tokens
    )

    try:
        cursor.execute('INSERT INTO Tokenizer '
                       '(user_id, session_id, t_start, content, tokens) '
                       'VALUES (?, ?, ?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def insert_full_story(db_connection, user, content):
    """
    Функция для добавления итогового сочинения
    """
    cursor = db_connection.cursor()
    logging.warning(f"Saving full story of user_id={user['user_id']}... ")
    data = (
        user['user_id'],
        user['session_id'],
        content,
    )

    try:
        cursor.execute('INSERT INTO Full_Stories '
                       '(user_id, session_id, content) '
                       'VALUES (?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def get_full_story(db_connection):
    """
    Вернуть случайную историю, если есть
    """
    cursor = db_connection.cursor()
    query = ('SELECT content FROM Full_Stories '
             'ORDER BY RANDOM() LIMIT 1;')

    cursor.execute(query)
    res = cursor.fetchone()

    # Считаем, что пустой результат - это отсутствие сессии, а не ошибка
    if res is None:
        logging.warning(f"get_full_story None = 0")
        return "Нет готовых сочинений"
    else:
        logging.warning(f"Get Full Story")
        return res[0]


def insert_prompt(db_connection, user, role, content, tokens):
    """
    Функция для добавления нового промта в БД - для всех ролей
    Значение tokens - накопительная сумма для этой сессии этого пользователя!
    """
    cursor = db_connection.cursor()
    # В tokens накапливающуюся сумму, поэтому ищем последнюю известную
    logging.warning(f"Finding the last prompt session_id={user['session_id']}")
    tokens_prev = get_tokens_in_session(db_connection, user)

    logging.warning(f"Adding prompt user_id={user['user_id']}, role={role}... ")
    data = (
        user['user_id'],
        user['session_id'],
        role,
        content,
        tokens + tokens_prev
    )

    try:
        cursor.execute('INSERT INTO Prompts '
                       '(user_id, session_id, role, content, tokens) '
                       'VALUES (?, ?, ?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def insert_tts(db_connection, user, content, symbols):
    """
    Функция для добавления в БД нового запроса TTS
    """
    cursor = db_connection.cursor()
    logging.warning(f"Adding tts request user_id={user['user_id']},... ")
    data = (
        user['user_id'],
        content,
        symbols
    )

    try:
        cursor.execute('INSERT INTO TTS '
                       '(user_id, content, symbols) '
                       'VALUES (?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def insert_stt(
        db_connection,
        user: int, filename: str, content: str,
        blocks: int, model: str, asr_time_ms: int):
    """
    Функция для добавления в БД нового запроса STT
    """
    cursor = db_connection.cursor()

    data = (
        user['user_id'],
        filename,
        content,
        blocks,
        model,
        asr_time_ms,
    )
    try:
        cursor.execute('INSERT INTO STT '
                       '(user_id, filename, content, '
                       'blocks, model, asr_time_ms) '
                       'VALUES (?, ?, ?, ?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"Adding stt request user_id={user['user_id']},... "
                        f"OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning(f"Adding stt request user_id={user['user_id']},... "
                        f"Error")
        return False


def get_tokens_info(db_connection, user):
    """
    Информация о токенах для пользователя
    """
    result = []

    result.append("\n<b>** КОНСТАНТЫ **</b>")
    result.append(f"MAX_USERS = {MAX_USERS} - "
                  f"макс. количество пользователей на весь проект")
    result.append(f"MAX_SESSIONS = {MAX_SESSIONS} - "
                  f"макс. количество сессий бота-сценариста у пользователя")
    result.append(f"MAX_PROJECT_TOKENS = {MAX_PROJECT_TOKENS} - "
                  f"макс. количество токенов суммарно на бота-сценариста")
    result.append(f"MAX_TOKENS_IN_SESSION = {MAX_TOKENS_IN_SESSION} - "
                  f"макс. количество токенов за сессию пользователя")

    result.append(f"MAX_PROJECT_SYMBOLS = {MAX_PROJECT_SYMBOLS} - "
                  f"макс. символов суммарно на синтез речи SpeechKit")
    result.append(f"MAX_USER_SYMBOLS = {MAX_USER_SYMBOLS} - "
                  f"макс. количество символов на пользователя")

    result.append(f"MAX_PROJECT_STT_BLOCKS = {MAX_PROJECT_STT_BLOCKS} - "
                  f"макс. блоков распознавания речи на весь проект")
    result.append(f"MAX_USER_STT_BLOCKS = {MAX_USER_STT_BLOCKS} - "
                  f"макс. блоков распознавания речи на пользователя")

    result.append("\n<b>** СТАТИСТИКА ТВОЯ **</b>")

    result.append("\n- <b><i>Бот-сценарист</i></b>:")

    r = get_tokens_in_session(db_connection, user)
    result.append(f"{r} - токенов в твоей текущей сессии")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(id) FROM Sessions WHERE user_id = ?;'
    cursor.execute(query, (user['user_id'],))
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"{r} - сессий у тебя")

    cursor = db_connection.cursor()
    query = 'SELECT DISTINCT (session_id) FROM Prompts WHERE user_id = ?;'
    cursor.execute(query, (user['user_id'],))
    res = cursor.fetchall()
    r = 0
    if res is not None:
        session_ids = [row[0] for row in res]
        for sid in session_ids:
            query2 = 'SELECT max(tokens) FROM Prompts WHERE session_id= ? ;'
            cursor.execute(query2, (sid,))
            res2 = cursor.fetchone()
            if res2 is not None:
                r += res2[0]
    result.append(f"{r} - всего токенов во всех твоих сессиях потрачено")

    result.append("\n- <b><i>Синтез речи</i></b>:")

    r = get_user_symbols(db_connection, user)
    r2 = get_user_tts_requests(db_connection, user)
    result.append(f"{r} - всего символов потрачено у тебя")
    result.append(f"{r2} - запросов синтеза речи")

    result.append("\n- <b><i>Распознавание речи</i></b>:")

    r = get_user_blocks(db_connection, user)
    r2 = get_user_stt_requests(db_connection, user)
    result.append(f"{r} - всего блоков потрачено у тебя")
    result.append(f"{r2} - запросов распознавания речи")

    result.append("\n<b>** СТАТИСТИКА ОБЩАЯ **</b>")

    result.append("\n- <b><i>Бот-сценарист</i></b>:")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(DISTINCT user_id) FROM Sessions WHERE 1;'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"{r} - всего пользователей")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(id) FROM Sessions WHERE 1;'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"{r} - всего сессий у всех пользователей")

    cursor = db_connection.cursor()
    query = 'SELECT DISTINCT (session_id) FROM Prompts WHERE 1;'
    cursor.execute(query)
    res = cursor.fetchall()
    r = 0
    if res is not None:
        session_ids = [row[0] for row in res]
        for sid in session_ids:
            query2 = 'SELECT max(tokens) FROM Prompts WHERE session_id= ? ;'
            cursor.execute(query2, (sid,))
            res2 = cursor.fetchone()
            if res2 is not None:
                r += res2[0]
    result.append(
        f"{r} ({(100 * r / MAX_PROJECT_TOKENS):2.2f}%) - "
        f"всего токенов во всех сессиях потрачено")

    result.append("\n- <b><i>Синтез речи</i></b>:")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(DISTINCT user_id) FROM TTS WHERE 1;'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"{r} - всего пользователей")

    r = get_total_symbols(db_connection)
    result.append(f"{r} - всего символов у всех пользователей")

    result.append("\n- <b><i>Распознавание речи</i></b>:")

    cursor = db_connection.cursor()
    query = "SELECT COUNT(DISTINCT user_id) FROM STT WHERE model='SpeechKit'"
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"{r} - всего пользователей")

    r = get_total_blocks(db_connection)
    result.append(f"{r} - всего блоков у всех пользователей")

    return result
