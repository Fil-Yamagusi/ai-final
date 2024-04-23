#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-
"""2024-04-21 Fil - Future code Yandex.Practicum
Final AI-bot: GPT, STT, TTS
README.md for more

GPT functions. Yandex GPT by default
"""
__version__ = '0.1'
__author__ = 'Firip Yamagusi'

# standard
from requests import post

# third-party
import logging
from freeGPT import Client, AsyncClient

# custom
# для авторизации и для ограничений
from config import MAIN, TB, YANDEX, LIM


async def ask_freegpt_async(model: str, prompt: str) -> str:
    """
    Асинхронно. Примерно 50 запросов в час. Для увеличения ещё синхронно есть
    https://pypi.org/project/freeGPT/
    python -m pip install -U freeGPT
    Умеет и картинки, но тут мне нужен простой GPT без подсчета ИИ-ресурсов
    """
    try:
        resp = await AsyncClient.create_completion(
            model,
            f"Instruction: Отвечай на русском. Prompt: {prompt}")
        return True, resp
    except Exception as e:
        return False, e


def ask_freegpt(model: str, prompt: str) -> str:
    """
    Не-асинхронно. Примерно 50 запросов в час.
    https://pypi.org/project/freeGPT/
    python -m pip install -U freeGPT
    Умеет и картинки, но тут мне нужен простой GPT без подсчета ИИ-ресурсов
    """
    try:
        resp = Client.create_completion(
            "gpt3",
            f"Instruction: Отвечай на русском. Prompt: {prompt}")
        return True, resp
    except Exception as e:
        return False, e


def count_tokens(text):
    """
    Подсчитывает количество токенов в тексте, который потом в GPT отправлять
    """

    headers = {
        'Authorization': f'Bearer {YANDEX['IAM_TOKEN']}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{YANDEX['FOLDER_ID']}/{YANDEX['GPT_MODEL']}/latest",
        "maxTokens": LIM['U_ASK_TOKENS'],
        "text": text  # text - тот текст, в котором мы хотим посчитать токены
    }
    return len(
        post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
            json=data,
            headers=headers
        ).json()['tokens']
    )
