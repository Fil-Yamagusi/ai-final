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

# third-party
import logging
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, Message

# custom
# для авторизации и для ограничений
from config import TB, YANDEX, LIM

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt="%F %T",
)
if False: # Настройки для опубликованного бота
    logging.basicConfig(
        level=logging.WARNING,
        filename="log.txt",
        filemode="w",
    )

logging.info(f"Main start")
logging.info(f"TB start: {TB['BOT_NAME']} | {TB['TOKEN']}")

# [print("TB", val) for val in TB]
# [print("YANDEX", val) for val in YANDEX]
# [print(val['name'], val['value']) for val in LIM.values()]

logging.info(f"TB finish")
logging.info(f"Main finish")



