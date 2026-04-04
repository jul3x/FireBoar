import os
import asyncio
import flet as ft
import json
from pathlib import Path
from fireboar.training import Training, Session
from fireboar.utils import show_dialog, StorageError

STORAGE_TRAININGS = "trainings"
STORAGE_ARCHIVED_TRAININGS = "archived-trainings"
STORAGE_TRAINING = "training"
STORAGE_SESSIONS = "sessions"
STORAGE_SESSION = "session"

_prefs = None
_prefs_keepalive = None  # extra ref to prevent flet 0.83+ unregister_services() from GC'ing the singleton

def _get_prefs():
    global _prefs, _prefs_keepalive
    if _prefs is None:
        _prefs = ft.SharedPreferences()
        _prefs_keepalive = _prefs
    return _prefs

async def _prefs_get(key: str) -> str | None:
    for attempt in range(5):
        try:
            return await asyncio.wait_for(_get_prefs().get(key), timeout=2)
        except asyncio.TimeoutError:
            print(f"SharedPreferences.get timeout (attempt {attempt + 1}/5): {key}")
    raise StorageError(f"Nie można odczytać danych po 5 próbach.\nWyłącz tryb oszczędzania energii i uruchom ponownie.")

async def _prefs_set(key: str, value: str):
    for attempt in range(5):
        try:
            await asyncio.wait_for(_get_prefs().set(key, value), timeout=2)
            return
        except asyncio.TimeoutError:
            print(f"SharedPreferences.set timeout (attempt {attempt + 1}/5): {key}")
    raise StorageError(f"Nie można zapisać danych po 5 próbach.\nWyłącz tryb oszczędzania energii i uruchom ponownie.")

async def load_trainings() -> list[Training]:
    names = json.loads(await _prefs_get(STORAGE_TRAININGS) or '[]')
    data = []
    for name in names:
        data.append(Training.from_json(await _prefs_get(STORAGE_TRAINING + ":" + name)))

    return data

async def load_sessions() -> list[Session]:
    names = json.loads(await _prefs_get(STORAGE_SESSIONS) or '[]')
    data = []
    for name in names:
        data.append(Session.from_json(await _prefs_get(STORAGE_SESSION + ":" + name)))
    return data

async def save_trainings(trainings: list[Training]):
    # TODO - remove old
    ts = {t.id: t for t in trainings}
    await _prefs_set(STORAGE_TRAININGS, json.dumps(list(ts.keys())))
    for name, t in ts.items():
        await _prefs_set(STORAGE_TRAINING + ":" + name, t.to_json())

async def save_training(training: Training):
    await _prefs_set(STORAGE_TRAINING + ":" + training.id, training.to_json())

async def save_sessions(sessions: list[Session]):
    # TODO - remove old
    ss = {s.id: s for s in sessions}
    await _prefs_set(STORAGE_SESSIONS, json.dumps(list(ss.keys())))
    for name, s in ss.items():
        await _prefs_set(STORAGE_SESSION + ":" + name, s.to_json())

async def get_training(id: str) -> Training:
    return Training.from_json(await _prefs_get(STORAGE_TRAINING + ":" + id) or '{}')

async def delete_training_from_list(id: str):
    # TODO - more efficiently
    trainings = await load_trainings()
    await save_trainings([t for t in trainings if t.id != id])

async def delete_session_from_list(id: str):
    # TODO - more efficiently
    sessions = await load_sessions()
    await save_sessions([s for s in sessions if s.id != id])

async def archive_training_instance(id: str):
    names = set(json.loads(await _prefs_get(STORAGE_ARCHIVED_TRAININGS) or '[]'))
    names.add(id)
    await _prefs_set(STORAGE_ARCHIVED_TRAININGS, json.dumps(list(names)))

async def dearchive_training_instance(id: str):
    names = set(json.loads(await _prefs_get(STORAGE_ARCHIVED_TRAININGS) or '[]'))
    names.remove(id)
    await _prefs_set(STORAGE_ARCHIVED_TRAININGS, json.dumps(list(names)))

async def get_archived_trainings() -> set[str]:
    return set(json.loads(await _prefs_get(STORAGE_ARCHIVED_TRAININGS) or '[]'))
