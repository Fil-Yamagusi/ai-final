#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-
"""2024-04-21 Fil - Future code Yandex.Practicum
Final AI-bot: GPT, STT, TTS
README.md for more

TTS functions. Yandex SpeechKit by default
"""
__version__ = '0.1'
__author__ = 'Firip Yamagusi'

# standard
from requests import post

# third-party
import logging

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM


def ask_speech_kit_tts(text: str) -> tuple:
    """
    Запросы к SpeechKit СИНТЕЗ
    Проверку на лимиты делаем в том месте, где вызывается функция
    """

    url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    headers = {
        'Authorization': f"Bearer {YANDEX['IAM_TOKEN']}",
    }
    data = {
        'text': text,  # что озвучиваем
        'lang': 'ru-RU',  # язык текста - русский
        'voice': 'filipp',  # голос Филиппа
        'speed': 1.1,  # Скорость чтения
        'emotion': 'good',  # эмоциональная окраска
        'folderId': YANDEX['FOLDER_ID'],
    }

    try:
        response = post(url, headers=headers, data=data)
        if response.status_code == 200:
            return True, response.content
        else:
            return False, f"Error SpeechKit: {response.status_code}"

    except Exception as e:
        return False, f"Error SpeechKit: post {e}"
