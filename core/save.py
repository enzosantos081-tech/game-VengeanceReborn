"""
core/save.py
Persistência em JSON do Vengeance Reborn.

O arquivo de salvamento (savegame.json) tem duas partes:

  "stats" - progressão PERMANENTE de Kael (moedas, melhorias, espadas).
            É o mesmo conteúdo que este módulo já gravava antes
            (PlayerStats.to_dict).
  "run"   - estado TEMPORÁRIO da partida em andamento (fase, posição,
            inimigos, moedas coletadas, checkpoints...). É montado e
            aplicado por core/run_state.py; aqui ele é só um dict.

Garantias:
  * Escrita atômica: grava em um arquivo .tmp, força o disco (fsync) e só
    então troca o arquivo definitivo (os.replace). Um fechamento no meio
    da gravação nunca deixa um savegame pela metade.
  * Backup: antes de cada troca, o último arquivo válido é copiado para
    savegame.json.bak. Se o principal estiver corrompido, o backup é usado.
  * Leitura tolerante: arquivo ausente, vazio, truncado ou com formato
    inesperado nunca derruba o jogo - simplesmente não há partida salva.
  * Saves antigos (somente a progressão, sem "version") continuam sendo
    lidos: viram {"stats": ..., "run": None}.

Local do arquivo (pasta de dados do usuário, fora da pasta do projeto):
  Windows: %APPDATA%\\VengeanceReborn
  macOS:   ~/Library/Application Support/VengeanceReborn
  Linux:   $XDG_DATA_HOME/VengeanceReborn (padrão ~/.local/share/...)
A variável de ambiente VENGEANCE_SAVE_DIR substitui o local (usada nos
testes). Se a pasta não puder ser criada, usa a pasta do projeto.
"""

import json
import os
import shutil
import sys

from config import settings

SAVE_VERSION = 2

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- caminhos
def _data_dir():
    override = os.environ.get("VENGEANCE_SAVE_DIR")
    if override:
        base = override
    elif sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        base = os.path.join(root, settings.SAVE_DIR_NAME)
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library",
                            "Application Support", settings.SAVE_DIR_NAME)
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
        base = os.path.join(root, settings.SAVE_DIR_NAME)
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except OSError:
        return _PROJECT_ROOT


def save_path():
    """Caminho completo do arquivo de salvamento."""
    return os.path.join(_data_dir(), settings.SAVE_FILE)


def _backup_path():
    return save_path() + ".bak"


def _tmp_path():
    return save_path() + ".tmp"


def _legacy_path():
    """savegame.json antigo, que ficava na pasta do projeto. Com
    VENGEANCE_SAVE_DIR definido (testes) ele é ignorado."""
    if os.environ.get("VENGEANCE_SAVE_DIR"):
        return os.path.join(save_path() + ".nolegacy")   # caminho que nunca existe
    return os.path.join(_PROJECT_ROOT, settings.SAVE_FILE)


# ----------------------------------------------------------------- leitura
def _parse(raw):
    """Valida a estrutura de um savegame já decodificado. Devolve
    {"stats": dict, "run": dict | None} ou None se for inutilizável."""
    if not isinstance(raw, dict):
        return None
    if "version" not in raw:
        # Formato antigo: o arquivo inteiro era o dicionário de stats.
        return {"stats": raw, "run": None}
    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version > SAVE_VERSION:
        return None
    stats = raw.get("stats")
    run = raw.get("run")
    if not isinstance(stats, dict) or not (run is None or isinstance(run, dict)):
        return None
    return {"stats": stats, "run": run}


def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _parse(json.load(f))
    except (OSError, ValueError, RecursionError):
        # ValueError cobre JSONDecodeError e UnicodeDecodeError.
        return None


def read_save():
    """Lê o salvamento: arquivo principal, depois o backup e por fim o
    savegame.json antigo da pasta do projeto. Devolve
    {"stats": dict, "run": dict | None} ou None se não houver nada válido."""
    for path in (save_path(), _backup_path(), _legacy_path()):
        if os.path.exists(path):
            data = _read_file(path)
            if data is not None:
                return data
    return None


def load_game(player_stats):
    """Carrega SÓ a progressão (moedas, melhorias, espadas) em player_stats.
    Usado ao iniciar um novo jogo quando existe apenas um save antigo, sem
    partida em andamento. Devolve True se carregou algo."""
    data = read_save()
    if data is None or data["run"] is not None:
        return False
    try:
        player_stats.from_dict(data["stats"])
    except (TypeError, ValueError, AttributeError):
        return False
    return True


# ---------------------------------------------------------------- gravação
def save_game(player_stats, run=None):
    """Grava progressão (+ estado da partida, se fornecido) de forma
    atômica. Devolve True em caso de sucesso."""
    payload = {
        "version": SAVE_VERSION,
        "stats": player_stats.to_dict(),
        "run": run,
    }
    path = save_path()
    tmp = _tmp_path()
    try:
        text = json.dumps(payload, separators=(",", ":"))
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        # Só vira backup o que estiver íntegro: um principal corrompido
        # nunca sobrescreve um backup bom.
        if os.path.exists(path) and _read_file(path) is not None:
            shutil.copyfile(path, _backup_path())
        os.replace(tmp, path)
        return True
    except (OSError, TypeError, ValueError):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def delete_save():
    """Apaga o salvamento (principal, backup, temporário e o save antigo).
    Só deve ser chamado em ações explícitas: novo jogo confirmado ou fim
    da campanha."""
    for path in (save_path(), _backup_path(), _tmp_path(), _legacy_path()):
        try:
            os.remove(path)
        except OSError:
            pass
