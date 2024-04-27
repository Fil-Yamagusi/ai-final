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
from random import randint, choice
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
from config import (
    MAIN, TB, YANDEX, LIM,
    random_ideas)
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
    ask_silero_v4_tts,
    ask_silero_tts,
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
        encoding='utf-8',
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
# Наглядный (готовый) пример сравнения моделей озвучки. Сравнить интонацию
t_compare_tts = 'Сравнить модели'
# Для начала обсуждения идей
t_random_idea = 'Чё-то туплю... давай рандомную идею!'
t_idea_yes = 'Отлично, обсудим!'
t_idea_no = 'Предложи другую'

mu_test_stt = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
mu_test_stt.add(*[t_stop_test])

mu_test_tts = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
mu_test_tts.add(*[t_compare_tts, t_stop_test])

mu_idea = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
mu_idea.add(*[t_idea_yes, t_idea_no])

mu_random_idea = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
mu_random_idea.add(*[t_random_idea])

# Словарь с пользователями в памяти, чтобы не мучить БД
user_data = {}

# Ведём идею к записи, статус логически по возрастающей, кроме 30/40
idea_statuses = {
    0: 'Не выбрана идея.',
    10: 'Выбрана идея.',
    20: 'Идёт обсуждение.',
    30: 'Закончить обсуждение, записать.',
    40: 'Закончить обсуждение, НЕ записать.',
}


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
        user_data[user_id]['user_age'] = 17

        # Для общения с GPT промежуточные статусы
        user_data[user_id]['status'] = 0
        user_data[user_id]['idea'] = ''

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

    # Бесплатный модуль SpeechRecognition.Google
    asr_start = time_ns()
    success, res = ask_speech_recognition(wav_file_path)
    asr_time_ms = (time_ns() - asr_start) // 1000000

    # Проверяем успешность распознавания и выводим результат, сохраняем в БД
    if success:
        result['SR.Google'] = {'content': res,
                               'asr_time_ms': asr_time_ms}
        insert_stt(db_conn, user_data[user_id],
                   wav_file_path, content=res,
                   blocks=stt_blocks, model='SR.Google',
                   asr_time_ms=asr_time_ms)
        if not all_modules:
            return True, result
    else:
        logging.info(f"Модуль SR.Google: не получилось распознать")

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


def text_to_voice(m: Message, all_modules: int) -> tuple:
    """
    Повторяющийся код для /test_tts, /idea,...
    Надо преобразовать текст в голос.
    Начинаем с бесплатного, если неудача, то платный.
    Блоки TTS проверяем только для платного.
    all_modules = 0 означает выйти при первом же успешном рапознавании
    """
    user_id = m.from_user.id

    symbols = len(m.text)

    result = {}

    # Бесплатный модуль Silero v4; Лимиты не проверяем
    tts_start = time_ns()
    # silero возвращает путь к уже созданному wav-файлу
    wav_file_path = f"voice/ftts-{user_id}-{time_ns() // 1000000}.wav"
    bot.send_chat_action(user_id, 'record_audio')
    success, res = ask_silero_v4_tts(m.text, wav_file_path)
    tts_time_ms = (time_ns() - tts_start) // 1000000

    if success:
        add_file2remove(db_conn, user_data[user_id], wav_file_path)
        result['Silero v4'] = {'filename': wav_file_path,
                               'tts_time_ms': tts_time_ms}
        insert_tts(db_conn, user_data[user_id],
                   content=m.text, filename=wav_file_path,
                   symbols=symbols, model='Silero_v4',
                   tts_time_ms=tts_time_ms)
        if not all_modules:
            return True, result
    else:
        # Если возникла ошибка, выводим сообщение
        logging.warning(f"MAIN: process_test_tts: Silero v4 fail: {res}")

    # Бесплатный модуль Silero v3.1; Лимиты не проверяем
    tts_start = time_ns()
    # silero возвращает путь к уже созданному wav-файлу
    wav_file_path = f"voice/ftts-{user_id}-{time_ns() // 1000000}.wav"
    bot.send_chat_action(user_id, 'record_audio')
    success, res = ask_silero_tts(m.text, wav_file_path)
    tts_time_ms = (time_ns() - tts_start) // 1000000

    if success:
        add_file2remove(db_conn, user_data[user_id], wav_file_path)
        result['Silero v3.1'] = {'filename': wav_file_path,
                                 'tts_time_ms': tts_time_ms}
        insert_tts(db_conn, user_data[user_id],
                   content=m.text, filename=wav_file_path,
                   symbols=symbols, model='Silero_v3.1',
                   tts_time_ms=tts_time_ms)
        if not all_modules:
            return True, result
    else:
        # Если возникла ошибка, выводим сообщение
        logging.warning(f"MAIN: process_test_tts: Silero v3.1 fail: {res}")

    # Платный модуль SpeechKit. Перед ним нужно проверить лимиты
    r1, r2 = is_limit(db_conn,
                      param_name='P_TTS_SYMBOLS', user=user_data[user_id])
    # Уже превышен или будет превышен?
    if r1 or (r2 + symbols) > LIM['P_TTS_SYMBOLS']['value']:
        error_msg = (f"СТОП! Будет превышен лимит P_TTS_SYMBOLS\n"
                     f"{LIM['P_TTS_SYMBOLS']['descr']}\n"
                     f"({r2} + {symbols}) >= {LIM['P_TTS_SYMBOLS']['value']}")
        return False, {'error': error_msg}

    r1, r2 = is_limit(db_conn,
                      param_name='U_TTS_SYMBOLS', user=user_data[user_id])
    # Уже превышен или будет превышен?
    if r1 or (r2 + symbols) > LIM['U_TTS_SYMBOLS']['value']:
        error_msg = (f"СТОП! Будет превышен лимит U_TTS_SYMBOLS\n"
                     f"{LIM['U_TTS_SYMBOLS']['descr']}\n"
                     f"({r2} + {symbols}) >= {LIM['U_TTS_SYMBOLS']['value']}")
        return False, {'error': error_msg}

    tts_start = time_ns()
    bot.send_chat_action(user_id, 'record_audio')
    success, res = ask_speech_kit_tts(m.text)
    tts_time_ms = (time_ns() - tts_start) // 1000000

    if success:
        mp3_file_path = f"voice/tts-{user_id}-{time_ns() // 1000000}.mp3"
        with open(mp3_file_path, "wb") as f:
            f.write(res)
        add_file2remove(db_conn, user_data[user_id], mp3_file_path)
        result['Yandex SpeechKit'] = {'filename': mp3_file_path,
                                      'tts_time_ms': tts_time_ms}
        insert_tts(db_conn, user_data[user_id],
                   content=m.text, filename=mp3_file_path,
                   symbols=symbols, model='SpeechKit',
                   tts_time_ms=tts_time_ms)
        return True, result
    else:
        # Если возникла ошибка, выводим сообщение
        logging.warning(f"MAIN: process_test_tts: SpeechKit fail: {res}")
        return False, {'error': f"Yandex SpeechKit error {res}"}


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
        'Чуть подробнее про все команды: /help',
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
        'Можешь написать/сказать просто: '
        '<i>учусь в 10 классе</i> или <i>закончил школу 10 лет назад</i> '
        'или <i>я на 2 курсе</i> ну и т.п. .',
        parse_mode='HTML',
        reply_markup=hideKeyboard)
    bot.register_next_step_handler(m, process_profile)


def process_profile(m: Message):
    """
    пользователь сообщил текстом или голосом: сколько ему лет.
    Голос расшифровываем через speech_recognition
    Дальше фразу даём GPT, чтобы она предположила примерный возраст
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    if m.voice:
        result = ""
        if m.voice.duration > 5:
            bot.send_message(
                user_id,
                "Не получается сохранить твоё голосовое сообщение. "
                "Попробуй чётче и короче 5 сек. Или текстом. /profile",
                reply_markup=hideKeyboard)

        voice_obj = bot.get_file(m.voice.file_id)
        success, res = voice_obj_to_text(m, voice_obj, all_modules=False)

        if success:
            for r in res.keys():
                result = res[r]['content']

    if m.text:
        result = m.text

    # Если возраст получили числом, то просто базовая проверка
    user_age = 17  # по умолчанию
    user_data[user_id]['user_age'] = user_age
    gpt_msg = ''
    if result.isdigit() and (10 <= int(result) <= 75):
        user_age = int(result)
    # иначе пробуем определить через GPT
    else:
        gpt_model = "gpt3"
        gpt_prompt = (f"Кто-то сказал про свой возраст: {result}. "
                      f"Сколько ему лет? Ответь одним целым числом, без слов")
        # случайно sync or async
        if randint(0, 2):
            success, res = run(ask_freegpt_async(
                model=gpt_model, prompt=gpt_prompt))
        else:
            success, res = ask_freegpt(
                model=gpt_model, prompt=gpt_prompt)

        logging.debug(f"MAIN: process_profile ask_freegpt: {res} / {result}")
        if success and res.isdigit():
            user_age = int(res)
            gpt_msg = ''
        else:
            gpt_msg = "☹️ Не получилось определить возраст с помощью GPT.\n"
        if not (10 <= user_age <= 75):
            user_age = 17

    user_data[user_id]['user_age'] = user_age
    update_user(db_conn, user_data[user_id])

    bot.send_message(
        user_id,
        f"{gpt_msg}Я запишу, что твой возраст: <b>{user_age}</b>. "
        f"Если неправильно, напиши свой возраст просто числом: /profile",
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
        f"<b>{user_data[user_id]['user_name']}, "
        "сейчас придумаем тебе интересное дело на лето!</b>\n\n"
        f"Судя по /profile, твой возраст: {user_data[user_id]['user_age']}.\n\n"
        "Сообщи текстом или голосом, чем ты увлекаешься "
        "(не забывай, что речь про лето).\n"
        "Например: <i>Я люблю кататься на велосипеде</i>, или "
        "<i>нравятся книги про приключения</i> или <i>пеку тортики</i>. "
        "Я предложу подходящее дело. Вместе обсудим его, уточним, и "
        "если оно тебе понравится, добавим в твой план.\n\n"
        "Подробнее про все команды: /help",
        parse_mode='HTML',
        reply_markup=mu_random_idea)
    bot.register_next_step_handler(m, process_idea)


def process_idea(m: Message):
    """
    Основная функция проекта, общение с GPT голосом/текстом
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    # Если просит случайную идею (самое начало обсуждения)
    if m.text == t_random_idea or m.text == t_idea_no:
        user_data[user_id]['status'] = 0
        user_data[user_id]['idea'] = choice(random_ideas)
        bot.send_message(
            user_id,
            f"<b>Случайную идею для начала обсуждения?</b>\n\n"
            f"Прелагаю: <i>{user_data[user_id]['idea'].lower()}</i>.\n",
            parse_mode='HTML',
            reply_markup=mu_idea)
        bot.register_next_step_handler(m, process_idea)
        # тут нужен return или next_step никогда уже не вернётся сюда?
        return

    # Если выбрал сам текстом/голосом или согласился на предложенную
    if user_data[user_id]['status'] == 0:

        # это если на предложенную соглашался
        if m.text == t_idea_yes:
            user_data[user_id]['status'] = 10
            # Если хитрец юда зашёл без выбора идеи, то на тебе рандомную
            if not user_data[user_id]['idea']:
                user_data[user_id]['idea'] = choice(random_ideas)

        # это если сам текстом
        elif m.text:
            user_data[user_id]['status'] = 10
            user_data[user_id]['idea'] = m.text

        # это если сам голосом
        if m.voice:
            bot.send_chat_action(user_id, 'typing')
            voice_obj = bot.get_file(m.voice.file_id)
            success, res = voice_obj_to_text(m, voice_obj, all_modules=False)
            if success:
                user_data[user_id]['status'] = 10
                user_data[user_id]['idea'] = res.items()[0]['content']

        bot.send_message(
            user_id,
            f"<b>status & idea:</b>\n\n"
            f"{user_data[user_id]['status']} {user_data[user_id]['idea']}",
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
        reply_markup=mu_test_tts)
    bot.register_next_step_handler(m, process_test_tts)


def process_test_tts(m: Message):
    """
    по ТЗ: пользователь вводит текст, а бот выдаёт аудио с озвучиванием текста.
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    if m.text == t_compare_tts:
        bot.send_message(
            user_id,
            f"<b>Вот примеры трёх моделей Text-to-speech</b>\n\n"
            f"Бесплатные <b>Silero v4</b> и <b>v3.1</b> "
            f"(на слабой локальной машине) "
            f"и платная <b>Yandex SpeechKit</b> (на быстром сервере).\n\n"
            f"У <b>Silero v4</b> авто-ударения и очень хорошая интонация!\n"
            f"Попробуй свой текст: /test_tts",
            parse_mode='HTML',
            reply_markup=hideKeyboard)

        example = choice(['gvozdik', 'sokol'])
        bot.send_chat_action(user_id, 'upload_audio')
        with open(f'voice/{example}-silero-v4.wav', "rb") as f:
            bot.send_audio(
                user_id, audio=f, title='Free TTS', performer='Silero v4')
        bot.send_chat_action(user_id, 'upload_audio')
        with open(f'voice/{example}-silero-v3.wav', "rb") as f:
            bot.send_audio(
                user_id, audio=f, title='Free TTS', performer='Silero v3.1')
        bot.send_chat_action(user_id, 'upload_audio')
        with open(f'voice/{example}-speechkit.mp3', "rb") as f:
            bot.send_audio(
                user_id, audio=f, title='Yandex TTS', performer='SpeechKit')
        return

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

    bot.send_message(
        user_id,
        f"Передаю в обработку...\n\n"
        f"символов: <b>{symbols}</b>\n"
        f"текст: <i>{m.text}</i>\n",
        parse_mode='HTML',
        reply_markup=hideKeyboard)

    success, res = text_to_voice(m, all_modules=True)

    if success:
        for r in res.keys():
            with open(res[r]['filename'], "rb") as f:
                bot.send_chat_action(user_id, 'upload_audio')
                bot.send_audio(
                    user_id, audio=f,
                    title=f"TTS за {res[r]['tts_time_ms']} мс",
                    performer={r},
                    caption="Запусти аудиофайл. Проверь звук, если не слышно. "
                            "Проверяй расход командой /stat")
    else:
        bot.send_message(
            user_id,
            f"<b>Ошибка!</b>\n\n{res['error']}\n\n"
            f"Проверяй расход командой /stat",
            parse_mode='HTML',
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
        f"<b>Проверка работы Speech-to-text</b>\n\n"
        f"Пришли голосовое сообщение 5-15 сек, получи в ответ текст.\n"
        f"(или нажми <i>Отказаться от проверки</i>)\n\n"
        f"Проверка использует лимиты на блоки (1 блок = 15 сек): /stat ",
        parse_mode='HTML',
        reply_markup=mu_test_stt)
    bot.register_next_step_handler(m, process_test_stt)


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
    bot.send_chat_action(user_id, 'typing')
    voice_obj = bot.get_file(m.voice.file_id)
    success, res = voice_obj_to_text(m, voice_obj, all_modules=False)

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


@bot.message_handler(commands=['help'])
def handle_help(m: Message):
    """
    Чуть более подробная справка о проекте и ссылка на Гитхаб
    """
    global db_conn, user_data
    user_id = m.from_user.id
    check_user(m)

    bot.send_message(
        user_id,
        f"<b>Справка чуть подробнее</b>\n\n"
        f"Это — финальный проект на Яндекс.Практикуме. Бот-помощник, "
        f"который помогает составить <b>план дел</b> на лето:\n"
        f"- укажи в Профиле свой возраст;\n"
        f"- потом в разделе Идея сообщи какое-то своё увлечение;\n"
        f"- обсуди с GPT варианты <b>дела</b> (цель, задание) по увлечению;\n"
        f"- выбранное дело добавь в <b>план</b>, повтори с другим увлечением;\n"
        f"- в итоге получишь отличный план и проведёшь лето с пользой!\n\n"
        f""
        f"<b>/profile</b> - по умолчанию бот считает, что тебе 17 лет. "
        f"Запусти эту команду, чтобы сообщить свой настоящий возраст. "
        f"Указать можешь простым тестом, например: <i>19</i>, "
        f"или эмодзи 1️⃣8️⃣, "
        f"или сообщением типа <i>через 5 лет мне стукнет 20!</i>, "
        f"или любым голосовым сообщением, из которого можно понять возраст, "
        f"например <i>у меня возраст Христа</i>.\n\n"
        f""
        f"<b>/idea</b> - вход в пошаговое общение с GPT. "
        f"Можно голосом, а можно и текстом. В итоге общения должно "
        f"получиться очередное <b>дело</b> на лето. Это дело можно записать "
        f"в <b>план</b> или отклонить.\n\n"
        f""
        f"<b>/show_plan</b> - посмотреть список уже придуманных дел (план). "
        f"Некоторые дела из списка можно удалить, а можно вообще начать "
        f"новый список!\n\n"
        f""
        f"<b>/stat</b> - Обязательно отслеживай расход "
        f"ИИ-ресурсов (токены для GPT, символы для TTS, блоки для STT). "
        f"Когда ты исчерпаешь свой лимит, соответствующее действие станет "
        f"недоступным.\n\n"
        f""
        f"<b>/test_tts</b> - по ТЗ нужен режим тестирования TTS. Показывает "
        f"результат платных и бесплатных моделей СИНТЕЗА речи. "
        f"Помни, что ИИ-ресурсы тратятся из твоего лимита.\n\n"
        f""
        f"<b>/test_stt</b> - по ТЗ нужен режим тестирования STT. Показывает "
        f"результат платных и бесплатных моделей РАСПОЗНАВАНИЯ речи. "
        f"Помни, что ИИ-ресурсы тратятся из твоего лимита.\n\n"
        f""
        f"Ещё подробнее - <a href='https://github.com/Fil-Yamagusi/ai-final'>"
        f"README на Github</a>\n\n",
        parse_mode='HTML',
        disable_web_page_preview=True,
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
