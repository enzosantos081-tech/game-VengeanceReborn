"""
core/save.py
Persistência simples em JSON. Não é obrigatório para o MVP jogado em
uma única sessão, mas permite continuar a progressão (moedas e
melhorias) entre execuções do jogo, o que combina bem com a proposta
de "tentativas" descrita no documento.
"""

import json
import os

from config import settings


def save_game(player_stats):
    try:
        with open(settings.SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(player_stats.to_dict(), f)
        return True
    except OSError:
        return False


def load_game(player_stats):
    if not os.path.exists(settings.SAVE_FILE):
        return False
    try:
        with open(settings.SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        player_stats.from_dict(data)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def delete_save():
    if os.path.exists(settings.SAVE_FILE):
        os.remove(settings.SAVE_FILE)
