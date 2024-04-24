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
from asyncio import run
from math import ceil

# third-party
import logging
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    Message, File)
import soundfile as sf

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM
from final_db import (
    get_db_connection,
    create_db,
    is_limit,
    create_user,
    update_user,
    add_file2remove,
    insert_tts,
    insert_stt,
)
from final_stt import (
    ask_speech_recognition,
    ask_speech_kit_stt,
)
from final_tts import (
    ask_speech_kit_tts,
)
from final_gpt import (
    count_tokens,
    ask_freegpt_async,
    ask_freegpt,
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

# Кнопка для выхода из проверки TTS, STT (вдруг не хочет тратить ИИ-ресурсы)
t_stop_test = 'Отказаться от проверки'
mu_stop_test = ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True)
mu_stop_test.add(*[t_stop_test])

# Словарь с пользователями в памяти, чтобы не мучить БД
user_data = {}


def convert_ogg_to_wav(input_file: str, output_file: str) -> tuple:
    """
    Для бесплатного STT нужен WAV
    https://pypi.org/project/soundfile/
    """
    try:
        data, samplerate = sf.read(input_file)
        sf.write(output_file, data, samplerate, format='WAV')
        return True, output_file
    except Exception as e:
        return False, e


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
        'Помогу тебе составить план дел на лето. Начни с команды /profile, '
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
    пользователь сообщил текстом или голосом, сколько ему лет.
    Голос расшифровываем через speech_recognition
    Дальше фразу даём GPT, чтобы она предположила примерный возраст
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    if m.voice:
        voice_err_msg = ("Не получается сохранить твоё голосовое сообщение. "
                         "Попробуй чётче и короче 5 сек. Или текстом. /profile")
        if m.voice.duration > 5:
            bot.send_message(user_id, voice_err_msg, reply_markup=hideKeyboard)

        # Сохраняем OGG
        file_info = bot.get_file(m.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        ogg_path = file_info.file_path
        # Сохраняем себе
        try:
            with open(ogg_path, 'wb') as ogg_file:
                ogg_file.write(downloaded_file)
                add_file2remove(db_conn, user_data[user_id], ogg_path)
                logging.debug(f"MAIN: process_profile: {user_id} {ogg_path}")
        except Exception as e:
            bot.send_message(user_id, voice_err_msg, reply_markup=hideKeyboard)
            logging.error(f"MAIN: process_profile: {user_id} ogg_write {e}")
            return

        # переводим в WAV для speech_recognition
        try:
            wav_file = f"{ogg_path[0:-4]}.wav"
            a_data, a_samplerate = sf.read(ogg_path)
            sf.write(wav_file, a_data, a_samplerate)
            add_file2remove(db_conn, user_data[user_id], wav_file)
            logging.debug(f"MAIN: process_profile: {user_id} now is {wav_file}")
        except Exception as e:
            bot.send_message(user_id, voice_err_msg, reply_markup=hideKeyboard)
            logging.error(f"MAIN: process_profile: {user_id} ogg2wav {e}")
            return

        # а вот и бесплатный speech_recognition. Блоки не считаем
        try:
            success, result = ask_speech_recognition(wav_file)
            bot.send_message(
                user_id,
                f"Я услышал: <i>{result}</i>",
                parse_mode='HTML',
                reply_markup=hideKeyboard)
        except Exception as e:
            bot.send_message(user_id, voice_err_msg, reply_markup=hideKeyboard)
            logging.error(f"MAIN: process_profile: {user_id} sr {e}")
            return

    if m.text:
        result = m.text

    # Если возраст получили числом, то просто базовая проверка
    user_age = 17  # по умолчанию
    if result.isdigit() and (10 <= int(result) <= 75):
        user_age = int(result)
    # иначе пробуем определить через GPT
    else:
        gpt_model = "gpt3"
        gpt_prompt = (f"Кто-то сказал про свой возраст: {result}. "
                      f"Сколько ему лет? Ответь одним целым числом, без слов")
        # случайно sync or async
        if randint(0, 2):
            res = run(ask_freegpt_async(model=gpt_model, prompt=gpt_prompt))
        else:
            res = ask_freegpt(model=gpt_model, prompt=gpt_prompt)

        print(res)
        if res[0] and res[1].isdigit():
            user_age = int(res[1])
        if not (10 <= user_age <= 75):
            user_age = 71

    user_data[user_id]['user_age'] = user_age

    update_user(db_conn, user_data[user_id])
    bot.send_message(
        user_id,
        f"Я определил, что твой возраст: <b>{user_age}</b>. "
        f"Если неправильно, попробуй указать свой возраст по-другому /profile",
        parse_mode='HTML',
        reply_markup=hideKeyboard)


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
        f"<b>Проверка режима Text-to-speech</b>\n\n"
        f"Пришли сообщение 50-150 символов, получи в ответ озвучку.\n"
        f"(или нажми <i>Отказаться от проверки</i>)\n\n"
        f"Проверка использует лимиты на символы: /stat ",
        parse_mode='HTML',
        reply_markup=mu_stop_test)
    bot.register_next_step_handler(m, process_test_tts)


def process_test_tts(m: Message):
    """
    по ТЗ: пользователь вводит текст, а бот выдаёт аудио с озвучиванием текста.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    if m.text == t_stop_test:
        bot.send_message(
            user_id,
            f"Ок, вышли из проверки Text-to-speech.\n"
            f"Можешь перейти в начало: /start",
            reply_markup=hideKeyboard)
        return

    if not m.text:
        bot.send_message(
            user_id,
            f"Эта функция работает только с текстом.\n"
            f"Попробуй ещё раз: /test_tts",
            reply_markup=hideKeyboard)
        return

    symbols = len(m.text)

    r1, r2 = is_limit(db_conn,
                      param_name='P_TTS_SYMBOLS', user=user_data[user_id])
    # Уже превышен или будет превышен?
    if r1 or (r2 + symbols) > LIM['P_TTS_SYMBOLS']['value']:
        bot.send_message(
            user_id,
            f"СТОП! Будет превышен лимит P_TTS_SYMBOLS\n"
            f"{LIM['P_TTS_SYMBOLS']['descr']}\n"
            f"({r2} + {symbols}) >= {LIM['P_TTS_SYMBOLS']['value']}",
            reply_markup=hideKeyboard)
        return

    r1, r2 = is_limit(db_conn,
                      param_name='U_TTS_SYMBOLS', user=user_data[user_id])
    # Уже превышен или будет превышен?
    if r1 or (r2 + symbols) > LIM['U_TTS_SYMBOLS']['value']:
        bot.send_message(
            user_id,
            f"СТОП! Будет превышен лимит U_TTS_SYMBOLS\n"
            f"{LIM['U_TTS_SYMBOLS']['descr']}\n"
            f"({r2} + {symbols}) >= {LIM['U_TTS_SYMBOLS']['value']}",
            reply_markup=hideKeyboard)
        return

    bot.send_message(
        user_id,
        f"Передаю в обработку...\n\n"
        f"символов: <b>{symbols}</b>\n"
        f"текст: <i>{m.text}</i>\n",
        parse_mode='HTML',
        reply_markup=hideKeyboard)

    success, response = ask_speech_kit_tts(m.text)
    if success:
        insert_tts(db_conn, user_data[user_id], m.text, symbols)

        # Если все хорошо, сохраняем аудио в файл
        # audio_name = f"voice/tts-{user_id}.ogg"
        # with open(audio_name, "wb") as f:
        #     f.write(response)
        # with open(audio_name, "rb") as f:
        #     bot.send_audio(user_id, f)
        #     f.close()
        # add_file2remove(db_conn, user_data[user_id], audio_name)
        try:
            bot.send_audio(user_id, response, title='Проверка Text-to-Speech',
                           caption='Запусти аудиофайл. Проверь звук, если не '
                                   'слышно. Проверяй расход командой /stat')
            logging.debug(f"MAIN: process_test_tts: OK for {user_id}")
        except Exception as e:
            logging.warning(f"MAIN: process_test_tts: {e} for {user_id}")

    else:
        # Если возникла ошибка, выводим сообщение
        logging.warning(f"MAIN: process_test_tts: not success: {response}")
        bot.send_message(
            user_id,
            f"Ошибка Yandex SpeechKit: <b>{response}</b>",
            parse_mode="HTML",
            reply_markup=hideKeyboard)
        return

    # bot.send_message(
    #     user_id,
    #     f'Запусти аудиофайл. Проверь звук, если ничего не слышно.\n'
    #     f'Проверяй расход командой /stat',
    #     parse_mode="HTML",
    #     reply_markup=hideKeyboard)


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
        f"<b>Проверка работы Speech-to-text</b>\n\n"
        f"Пришли голосовое сообщение 5-15 сек, получи в ответ текст.\n"
        f"(или нажми <i>Отказаться от проверки</i>)\n\n"
        f"Проверка использует лимиты на блоки (1 блок = 15 сек): /stat ",
        parse_mode='HTML',
        reply_markup=mu_stop_test)
    bot.register_next_step_handler(m, process_test_stt)


def voice_obj_to_text(m: Message, voice_obj: File, all_modules: int) -> tuple:
    """
    Повторяющийся код для /test_stt, /idea, /profile...
    Надо преобразовать voice из телеграма в словарь ответов.
    Начинаем с бесплатного, если неудача, то платный.
    Блоки STT проверяем только для платного.
    all_modules = 0 означает выйти при первом же успешном рапознавании
    """
    user_id = m.from_user.id

    # для SpeechRecognition нужен WAV
    ogg_file_path = voice_obj.file_path
    voice_file = bot.download_file(ogg_file_path)

    with open(ogg_file_path, 'wb') as ogg_file:
        ogg_file.write(voice_file)

    wav_file_path = f"{ogg_file_path[0:-3]}wav"
    wav_res = convert_ogg_to_wav(ogg_file_path, wav_file_path)[0]
    add_file2remove(db_conn, user_data[user_id], ogg_file_path)
    add_file2remove(db_conn, user_data[user_id], wav_file_path)

    stt_blocks = ceil(m.voice.duration / 15)
    logging.debug(f"MAIN: process_test_stt: {voice_obj.file_path} {stt_blocks}")

    result = {}
    # Бесплатный модуль SpeechRecognition
    asr_start = time_ns()
    success, res = ask_speech_recognition(wav_file_path)
    asr_time_ms = (time_ns() - asr_start) // 1000000

    # Проверяем успешность распознавания и выводим результат, сохраняем в БД
    if success:
        result['SpeechRecognition'] = {'content': res,
                                       'asr_time_ms': asr_time_ms}
        insert_stt(db_conn, user_data[user_id],
                   wav_file_path, content=res,
                   blocks=stt_blocks, model='SR',
                   asr_time_ms=asr_time_ms)
        if not all_modules:
            return True, result
    else:
        logging.info(f"Модуль SpeechRecognition: не получилось распознать")

    # Платный модуль SpeechKit. Перед ним нужно проверить лимиты
    r1, r2 = is_limit(db_conn,
                      param_name='P_STT_BLOCKS', user=user_data[user_id])
    # Уже превышен или будет превышен?
    if r1 or (r2 + stt_blocks) > LIM['P_STT_BLOCKS']['value']:
        error_msg = (f"СТОП! Будет превышен лимит P_STT_BLOCKS\n"
                     f"{LIM['P_STT_BLOCKS']['descr']}\n"
                     f"({r2} + {stt_blocks}) >= {LIM['P_STT_BLOCKS']['value']}")
        return False, {'error': error_msg}

    r1, r2 = is_limit(db_conn,
                      param_name='U_STT_BLOCKS', user=user_data[user_id])
    # Уже превышен или будет превышен?
    if r1 or (r2 + stt_blocks) > LIM['U_STT_BLOCKS']['value']:
        error_msg = (f"СТОП! Будет превышен лимит U_STT_BLOCKS\n"
                     f"{LIM['U_STT_BLOCKS']['descr']}\n"
                     f"({r2} + {stt_blocks}) >= {LIM['U_STT_BLOCKS']['value']}")
        return False, {'error': error_msg}

    asr_start = time_ns()
    success, res = ask_speech_kit_stt(voice_file)
    # success, res = True, "SpeechKit закомментировал, идёт тест модуля SR"
    asr_time_ms = (time_ns() - asr_start) // 1000000

    # Проверяем успешность распознавания и выводим результат, сохраняем в БД
    if success:
        result['Yandex SpeechKit'] = {'content': res,
                                      'asr_time_ms': asr_time_ms}
        insert_stt(db_conn, user_data[user_id],
                   ogg_file_path, content=res,
                   blocks=stt_blocks, model='SpeechKit',
                   asr_time_ms=asr_time_ms)
        return True, result
    elif result.get('SpeechRecognition'):
        return True, result
    else:
        return False, {'error': res}

    return False, {'error': 'Не получилось распознать голосовое сообщение'}


def process_test_stt(m: Message):
    """
    по ТЗ: пользователь отправляет аудио, а бот распознаёт текст.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    if m.text == t_stop_test:
        bot.send_message(
            user_id,
            f"Ок, вышли из проверки Speech-to-text.\n"
            f"Можешь перейти в начало: /start",
            reply_markup=hideKeyboard)
        return

    if not m.voice:
        bot.send_message(
            user_id,
            f"Эта функция работает только с голосовыми сообщениями.\n"
            f"Попробуй ещё раз: /test_stt",
            reply_markup=hideKeyboard)
        return

    if m.voice.duration > 30:
        bot.send_message(
            user_id,
            f"Голосовое сообщение должно быть не длиннее 30 секунд.\n"
            f"Попробуй ещё раз: /test_stt",
            reply_markup=hideKeyboard)
        return

    bot.send_message(
        user_id,
        f"Передаю в обработку...\n\n"
        f"блоков: <b>{ceil(m.voice.duration / 15)}</b>\n"
        f"длина: <b>{m.voice.duration} сек</b>\n",
        parse_mode='HTML',
        reply_markup=hideKeyboard)

    # Для SpeechKit достаточно звуковых данных
    voice_obj = bot.get_file(m.voice.file_id)

    success, res = voice_obj_to_text(m, voice_obj, all_modules=True)
    if success:
        result_msg = ""
        for r in res.keys():
            result_msg += (
                f"Модуль <b>{r}</b> за {res[r]['asr_time_ms']} мс:\n"
                f"<i>{res[r]['content']}</i>\n\n")
    else:
        result_msg = f"<b>Ошибка!</b>\n\n{res['error']}\n\n"
    bot.send_message(
        user_id,
        f"{result_msg}Проверяй расход командой /stat",
        parse_mode='HTML',
        reply_markup=hideKeyboard)


def append_stat(stat: list, param_name: str, user: dict) -> list:
    """
    формирует список для отображения статистики ИИ-ресурсов /stat
    """
    r1, r2 = is_limit(db_conn, param_name=param_name, user=user)

    stat.append(f"{LIM[param_name]['descr']}:")
    stat.append(f"<b>{int(100 * r2 / LIM[param_name]['value'])}</b>% "
                f"({r2} / {LIM[param_name]['value']})")

    return stat


@bot.message_handler(commands=['stat'])
def handle_stat(m: Message):
    """
    Статистика расходов ИИ-ресурсов и ограничений
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    p_stat = []
    p_stat = append_stat(p_stat, 'P_USERS', user_data[user_id])
    p_stat = append_stat(p_stat, 'P_GPT_TOKENS', user_data[user_id])
    p_stat = append_stat(p_stat, 'P_TTS_SYMBOLS', user_data[user_id])
    p_stat = append_stat(p_stat, 'P_STT_BLOCKS', user_data[user_id])

    u_stat = []
    u_stat = append_stat(u_stat, 'U_GPT_TOKENS', user_data[user_id])
    u_stat = append_stat(u_stat, 'U_TTS_SYMBOLS', user_data[user_id])
    u_stat = append_stat(u_stat, 'U_STT_BLOCKS', user_data[user_id])

    bot.send_message(
        user_id,
        f"<b>ОГРАНИЧЕНИЯ И РАСХОД ИИ-РЕСУРСОВ</b>\n\n"
        f"<b>Весь проект:</b>\n\n"
        f"{'\n'.join(p_stat)}\n\n"
        f"<b>Твой личный расход:</b>\n\n"
        f"{'\n'.join(u_stat)}",
        parse_mode='HTML',
        reply_markup=hideKeyboard)


# *********************************************************************
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
