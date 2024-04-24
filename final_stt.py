#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-
"""2024-04-21 Fil - Future code Yandex.Practicum
Final AI-bot: GPT, STT, TTS
README.md for more

STT functions. Yandex SpeechKit by default
"""
__version__ = '0.1'
__author__ = 'Firip Yamagusi'

# standard
from requests import post

# third-party
import logging
import speech_recognition as sr

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM


def ask_speech_recognition(wav_file: str):
    """
    Функция для перевода аудио, в формате ".wav" в текст
    """

    with sr.AudioFile(wav_file) as source:
        r = sr.Recognizer()
        audio = r.record(source)
        try:
            return True, r.recognize_google(audio, language="ru_RU")
        except Exception as e:
            return False, e

    # r = sr.Recognizer()
    # message = sr.AudioFile(wav_file)
    # with message as source:
    #     audio = r.record(source)
    # result = r.recognize_google(audio, language="ru_RU")
    return result


def ask_speech_kit_stt(data):
    """
    Запросы к SpeechKit РАСПОЗНАВАНИЕ
    Проверку на лимиты делаем в том месте, где вызывается функция
    """

    params = "&".join([
        "topic=general",
        f"folderId={YANDEX['FOLDER_ID']}",
        "lang=ru-RU",
    ])

    url = f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}"
    headers = {'Authorization': f"Bearer {YANDEX['IAM_TOKEN']}"}

    try:
        response = post(url, headers=headers, data=data)
        decoded_data = response.json()
        if decoded_data.get('error_code') is None:
            logging.debug(decoded_data.get('result'))
            return True, decoded_data.get('result')
        else:
            logging.warning(f"Error SpeechKit {decoded_data.get('error_code')}")
            return False, f"Error SpeechKit {decoded_data.get('error_code')}"

    except Exception as e:
        logging.warning(f"Error SpeechKit: post {e}")
        return False, f"Error SpeechKit: post {e}"
