import os
import flet as ft
import json
from pathlib import Path
from fireboar.training import Training, Session
from fireboar.utils import show_dialog

STORAGE_TRAININGS = "trainings"
STORAGE_TRAINING = "training"
STORAGE_SESSIONS = "sessions"
STORAGE_SESSION = "session"

async def load_trainings() -> list[Training]:
    names = json.loads(await ft.SharedPreferences().get(STORAGE_TRAININGS) or '[]')
    data = []
    for name in names:
        data.append(Training.from_json(await ft.SharedPreferences().get(STORAGE_TRAINING + ":" + name)))

    return data

async def load_sessions() -> list[Session]:
    names = json.loads(await ft.SharedPreferences().get(STORAGE_SESSIONS) or '[]')
    data = []
    for name in names:
        data.append(Session.from_json(await ft.SharedPreferences().get(STORAGE_SESSION + ":" + name)))
    return data

async def save_trainings(trainings: list[Training]):
    # TODO - remove old
    ts = {t.id: t for t in trainings}
    await ft.SharedPreferences().set(STORAGE_TRAININGS, json.dumps(list(ts.keys())))
    for name, t in ts.items():
        await ft.SharedPreferences().set(STORAGE_TRAINING + ":" + name, t.to_json())

async def save_training(training: Training):
    await ft.SharedPreferences().set(STORAGE_TRAINING + ":" + training.id, training.to_json())

async def save_sessions(sessions: list[Session]):
    # TODO - remove old
    ss = {s.id: s for s in sessions}
    await ft.SharedPreferences().set(STORAGE_SESSIONS, json.dumps(list(ss.keys())))
    for name, s in ss.items():
        await ft.SharedPreferences().set(STORAGE_SESSION + ":" + name, s.to_json())

async def get_training(id: str) -> Training:
    return Training.from_json(await ft.SharedPreferences().get(STORAGE_TRAINING + ":" + id) or '{}')

async def delete_training_from_list(id: str):
    # TODO - more efficiently
    trainings = await load_trainings()
    await save_trainings([t for t in trainings if t.id != id])

async def delete_session_from_list(id: str):
    # TODO - more efficiently
    sessions = await load_sessions()
    await save_sessions([s for s in sessions if s.id != id])

async def upload_json(e, page):
    if e.progress != 1.0:
        return

    file_path = os.path.join("uploads", "trainings.json")

    with open(file_path, "r") as f:
        data = json.load(f)

    trainings = [Training.from_json(t) for t in data["trainings"]]
    sessions = [Session.from_json(s) for s in data["sessions"]]

    await save_trainings(trainings)
    await save_sessions(sessions)
    await show_dialog(
        page,
        "Dane zaimportowane",
        "Poprzednie dane zostały wyczyszczone!",
        "Ok",
    )


async def import_json(e, page, json_file_picker):
    files = await json_file_picker.pick_files(
        allow_multiple=False
    )
    if not files:
        return

    file = files[0]
    filename = "trainings.json"
    upload_url = page.get_upload_url(filename, expires=60)
    await json_file_picker.upload(
        files=[
            ft.FilePickerUploadFile(
                name=file.name,
                upload_url=upload_url,
            )
        ]
    )

async def export_json(e, json_file_picker):
    trainings = [t.to_json() for t in await load_trainings()]
    sessions = [s.to_json() for s in await load_sessions()]
    await json_file_picker.save_file(
        dialog_title="Zapisz treningi",
        file_name="fireboar_trainings.json",
        src_bytes=json.dumps({"trainings": trainings, "sessions": sessions}).encode("utf-8"),
    )
