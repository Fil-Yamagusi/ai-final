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
import torch

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM


def ask_silero_v4_tts(text: str, file_path: str) -> tuple:
    """
    Запросы к Silero v4: Бесплатный модуль TTS СИНТЕЗ
    Локально исполняется, требует 400+ Мб
    сразу создаёт файл, отдаём уже путь к нему
    """

    device = torch.device('cpu')
    torch.set_num_threads(4)
    local_file = 'silero/model.pt'

    # Для лучшего звучания желательно ставить точку в конце предложения
    if text[-1] not in ['.', '!', '?']:
        text += '.'

    try:
        model = (torch.package.PackageImporter(local_file).
                 load_pickle("tts_models", "model"))
        model.to(device)

        sample_rate = 48000
        speaker = 'kseniya'
        speakers = ['aidar', 'baya', 'kseniya', 'xenia', 'eugene', 'random']

        audio_paths = model.save_wav(text=text,
                                     speaker=speaker,
                                     sample_rate=sample_rate,
                                     audio_path=file_path)
        if audio_paths:
            return True, file_path
        else:
            logging.warning(f"Silero v4 TTS error: {e}")
            return False, f"Silero v4 model.save_wav error"
    except Exception as e:
        logging.warning(f"Silero v4 TTS error: {e}")
        return False, f"Silero v4 TTS error: {e}"


def ask_silero_tts(text: str, file_path: str) -> tuple:
    """
    Запросы к Silero: Бесплатный модуль TTS СИНТЕЗ
    Локально исполняется, требует 400+ Мб
    сразу создаёт файл, отдаём уже путь к нему
    """

    language = 'ru'
    model_ids = ['v3_1_ru', 'ru_v3']
    model_id = model_ids[0]
    sample_rate = 48000
    speakers = ['aidar', 'baya', 'kseniya', 'xenia', 'eugene', ]
    speaker = speakers[1]
    device = torch.device('cpu')

    # Для лучшего звучания желательно ставить точку в конце предложения
    if text[-1] not in ['.', '!', '?']:
        text += '.'

    try:
        model, example_text = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language=language,
            speaker=model_id)
        model.to(device)  # gpu or cpu
        audio_paths = (
            model.save_wav(text=text,
                           speaker=speaker,
                           sample_rate=sample_rate,
                           audio_path=file_path))
        if audio_paths:
            return True, file_path
        else:
            logging.warning(f"Silero TTS error: {e}")
            return False, f"Silero model.save_wav error"
    except Exception as e:
        logging.warning(f"Silero TTS error: {e}")
        return False, f"Silero TTS error: {e}"


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
        'format': 'mp3',
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
