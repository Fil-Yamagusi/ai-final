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

# third-party
import speech_recognition as sr

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM


def ask_speech_kit_stt(user: dict, downloaded_file):
    pass

def ask_speech_recognition(wav_file: str):
    """
    Функция для перевода аудио, в формате ".wav" в текст
    """
    r = sr.Recognizer()
    message = sr.AudioFile(wav_file)
    with message as source:
        audio = r.record(source)
    result = r.recognize_google(audio, language="ru_RU")
    return result