import os
import re
import flet as ft
import uuid
import asyncio
import json
import datetime
import shutil
from pathlib import Path

# TODO: Organize code
# TODO: Sounds of beeping for sessions
# TODO: Rewrite this for better DB structure
# TODO: Add fingerboarding intervals type training
# TODO: Handle Core training exercises
# TODO: Mark sessions with PB and historical PB
# TODO: Import from XLSX
# TODO: Export to XLSX
# TODO: Add FireBoar logo

STORAGE_TRAININGS = "trainings"
STORAGE_TRAINING = "training"
STORAGE_SESSIONS = "sessions"
STORAGE_SESSION = "session"

async def load_trainings() -> list[dict]:
    names = json.loads(await ft.SharedPreferences().get(STORAGE_TRAININGS) or '[]')
    data = []
    for name in names:
        data.append(json.loads(await ft.SharedPreferences().get(STORAGE_TRAINING + ":" + name)))

    return data

async def load_sessions() -> list[dict]:
    names = json.loads(await ft.SharedPreferences().get(STORAGE_SESSIONS) or '[]')
    data = []
    for name in names:
        data.append(json.loads(await ft.SharedPreferences().get(STORAGE_SESSION + ":" + name)))
    return data

async def save_trainings(trainings: list[dict]):
    # TODO - remove old
    ts = {t["id"]: t for t in trainings}
    await ft.SharedPreferences().set(STORAGE_TRAININGS, json.dumps(list(ts.keys())))
    for name, t in ts.items():
        await ft.SharedPreferences().set(STORAGE_TRAINING + ":" + name, json.dumps(t))

async def save_sessions(sessions: list[dict]):
    # TODO - remove old
    ss = {s["id"]: s for s in sessions}
    await ft.SharedPreferences().set(STORAGE_SESSIONS, json.dumps(list(ss.keys())))
    for name, s in ss.items():
        await ft.SharedPreferences().set(STORAGE_SESSION + ":" + name, json.dumps(s))

async def get_training(id: str):
    return json.loads(await ft.SharedPreferences().get(STORAGE_TRAINING + ":" + id) or '{}')

async def delete_training_from_list(id: str):
    # TODO - more efficiently
    trainings = await load_trainings()
    await save_trainings([t for t in trainings if t["id"] != id])

async def delete_session_from_list(id: str):
    # TODO - more efficiently
    sessions = await load_sessions()
    await save_sessions([s for s in sessions if s["id"] != id])

def get_sets_list(training: dict):
    sets = []
    supersets = {}
    for ex in training["exercises"]:
        if ex["superset_id"].strip():
            supersets.setdefault(ex["superset_id"].strip(), []).append(
                ex
            )
    
    superset_visited = set()
    for ex in training["exercises"]:
        s_id = ex["superset_id"].strip()
        if not s_id:
            for i in range(ex["sets"]):
                sets.append({**ex, "current_set": i + 1})
        else:
            if s_id in superset_visited:
                continue

            max_sets = max(ex["sets"] for ex in supersets[s_id])
            for i in range(max_sets):
                for super_ex in supersets[s_id]:
                    if i >= super_ex["sets"]:
                        continue
                    sets.append({**super_ex, "current_set": i + 1})

            superset_visited.add(s_id)
    return sets


def normalize_string(value: str | int | float) -> float:
    if isinstance(value, int) or isinstance(value, float):
        return float(value)

    cleaned = re.sub(r"[^0-9.,]", "", value)
    cleaned = cleaned.replace(",", ".")
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def get_pb_for_training(sessions: list, exercise_id: str) -> tuple[float, int, float]:
    max_weight = 0.0
    max_reps = 0
    session_date = 0.0
    for s in sessions:
        for set in s["sets"]:
            if set["id"] != exercise_id:
                continue
            w = normalize_string(set["weight"])
            r = int(normalize_string(set["reps"]))
            if w > max_weight:
                max_weight = w
                max_reps = r
                session_date = s["date"] 
            if w == max_weight and r > max_reps:
                max_reps = r
                session_date = s["date"]

    return max_weight, max_reps, session_date


def get_session_pb_emoji(sessions: list, session_idx: int) -> str:
    # TODO - get this
    current_pb = "🥇"    
    historical_pb = "🥈"

    #for s in sessions:
    #    if s["sets"]

    return ""


async def main(page: ft.Page):
    page.title = "FireBoar"
    page.scroll = "auto"

    logo = ft.Image(
        src="logo.png",
        width=300,
        height=300,
    )


    async def show_home():
        trainings = await load_trainings()
        sessions = await load_sessions()
        page.controls.clear()
        page.bgcolor = "#222222"

        os.makedirs("uploads", exist_ok=True)

        async def upload_json_file(e):
            if e.progress != 1.0:
                return

            file_path = os.path.join("uploads", "trainings.json")

            with open(file_path, "r") as f:
                data = json.load(f)
            
            # TODO - data verification
            await save_trainings(data["trainings"])
            await save_sessions(data["sessions"])
            hf = ft.HapticFeedback()
            await hf.vibrate()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Dane zaimportowane"),
                content=ft.Text("Poprzednie dane zostały wyczyszczone!"),
                actions=[
                    ft.TextButton("Ok", on_click=lambda e: page.pop_dialog()),
                ],
                open=True,
            ))
            await show_home()

        async def import_json_file(e):
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

        async def export_json(e):
            trainings = await load_trainings()
            sessions = await load_sessions()
            await json_file_picker.save_file(
                dialog_title="Zapisz treningi",
                file_name="fireboar_trainings.json",
                src_bytes=json.dumps({"trainings": trainings, "sessions": sessions}).encode("utf-8"),
            )   

        json_file_picker = ft.FilePicker(on_upload=upload_json_file)

        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.TOP_CENTER, 
                content=ft.Column([
                        logo,
                        ft.Text("Poczuj w sobie siłę dzika!", size=20, weight="bold", text_align="center"),
                        ft.Text(""),
                        ft.Button("➕ Dodaj trening", on_click=show_add_training, expand=True, width=2000, height=50),
                        ft.Button("↗ Importuj JSON", on_click=import_json_file, expand=True, width=2000, height=50),
                        ft.Button("↘ Eksportuj JSON", on_click=export_json, expand=True, width=2000, height=50)

                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

        for t in trainings:
            sessions_for_t = [s for s in sessions if s["training"] == t["id"]]
            page.add(
                ft.Card(
                    ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Row([ft.Text(t["name"], size=18, weight="bold"),
                                    ft.Text(f"ćwiczeń: {len(t['exercises'])}, było łojone: {len(sessions_for_t)} razy", size=14),
                            ]),
                            ft.Column([
                                ft.Row([
                                    ft.TextButton("▶ Start", on_click=start_training, data=t["id"]),
                                    ft.TextButton("🚀 Pokaż sesyjki", on_click=show_sessions, data=t),
                                ]),
                                ft.Row([
                                    ft.TextButton("✏ Edytuj", on_click=edit_training, data=t["id"]),
                                    ft.TextButton("🗑️ Usuń", on_click=delete_training, data=t["id"]),
                                ]),
                            ])
                        ]),
                    )
                )
            )

        page.update()

    async def show_sessions(e):
        sessions = await load_sessions()
        training_data = e.control.data
        sessions_for_t = [s for s in sessions if s["training"] == training_data["id"]]
        page.controls.clear()
        page.add(
            ft.Text(f"Sesyjki dla treningu: {training_data['name']}", size=24),
        )

        async def delete_session(e):
            await delete_session_from_list(e.control.data)
            e.control.data = training_data
            hf = ft.HapticFeedback()
            await hf.vibrate()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Sesyjka usunięta"),
                content=ft.Text("Wstydzisz się ciężaru?"),
                actions=[
                    ft.TextButton("Dzień chrabonszcza", on_click=lambda e: page.pop_dialog()),
                ],
                open=True,
            ))
            await show_sessions(e)

        for session_idx, s in enumerate(sessions_for_t):
            sets_text = [
                ft.Text(f"{set_idx+1}. Ćw. {set['name']}, Seria {set.get('set_index')}, {set['weight']} x {set['reps']}, uwagi: {set['notes']}") for set_idx, set in enumerate(s["sets"])
            ]
            page.add(
                ft.Card(
                    ft.Container(
                        padding=10,
                        content=ft.ExpansionTile(
                            title=ft.Row(controls=[
                                ft.Text(f"{session_idx+1}. Data: {str(datetime.datetime.fromtimestamp(s['date'])).split(' ')[0]}", size=18, weight="bold"),
                                ft.Button("Usuń", on_click=delete_session, data=s["id"])
                            ]),
                            controls=ft.Column(
                                controls=[
                                ft.Text(""),
                                *sets_text,
                                ft.Text(""),
                            ]),
                            expanded=False, # Controls initial state
                            expanded_alignment=ft.Alignment.CENTER_LEFT,
                        )
                    )
                )
            )

        page.add(
            ft.TextButton("⬅ Wróć", on_click=show_home)
        )
        page.update()

    async def show_add_training(e=None):
        name = ft.TextField(label="Nazwa treningu")

        async def save(e):
            trainings = await load_trainings()
            trainings.append({
                "id": str(uuid.uuid4()),
                "name": name.value,
                "exercises": []
            })
            await save_trainings(trainings)
            hf = ft.HapticFeedback()
            await hf.vibrate()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Trening dodany"),
                content=ft.Text("Dodaj ćwiczenia drapichruście."),
                actions=[
                    ft.TextButton("Będę łoił", on_click=lambda e: page.pop_dialog()),
                ],
                open=True,
            ))
            await show_home()

        page.controls.clear()
        page.add(
            ft.Text("Nowy trening", size=24),
            name,
            ft.Row([
                ft.Button("Zapisz", on_click=save),
                ft.TextButton("⬅ Wróć", on_click=show_home)
            ]),
        )
        page.update()

    async def edit_training(event):
        page.controls.clear()
        trainings = await load_trainings()
        idx = 0
        for i, t in enumerate(trainings):
            if t["id"] == event.control.data:
                idx = i

        async def add_exercise(e):
            trainings[idx]["exercises"].append({
                "id": str(uuid.uuid4()),
                "name": "",
                "sets": 3,
                "suggested_weight": "",
                "suggested_reps": "",
                "rest_seconds": 60,
                "superset_id": "",
            })
            await save_trainings(trainings)
            await edit_training(e)

        async def remove_exercise(e):
            trainings[idx]["exercises"] = [ex for ex in trainings[idx]["exercises"] if ex["id"] != e.control.data]
            await save_trainings(trainings)
            await edit_training(e)

        async def save_training(e):
            await save_trainings(trainings)
            hf = ft.HapticFeedback()
            await hf.vibrate()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Ćwiczenia ogarnięte"),
                content=ft.Text("Teraz tylko ładować."),
                actions=[
                    ft.TextButton("Ok", on_click=lambda e: page.pop_dialog()),
                ],
                open=True,
            ))
            await show_home()

        page.add(
            ft.Text(f"Edycja treningu: {trainings[idx]['name']}", size=22),
            ft.Button("➕ Dodaj ćwiczenie", on_click=add_exercise, data=event.control.data),
        )

        for ex in trainings[idx]["exercises"]:
            page.add(
                ft.Card(
                    ft.Container(
                        padding=10,
                        expand=True,
                        content=ft.ExpansionTile(
                            title=ft.Row(controls=[
                                ft.Text(f"{ex['name'] or 'Kliknij by rozwinąć'}"),
                                ft.Button("Usuń", on_click=remove_exercise, data=ex["id"]),
                            ]),
                            controls=ft.Column(
                                controls=[
                                ft.Text(""),
                                ft.TextField(
                                    label="Nazwa",
                                    expand=True,
                                    value=ex["name"],
                                    on_change=lambda e, ex=ex: ex.update(name=e.control.value)
                                ),
                                ft.TextField(
                                    label="Serie",
                                    expand=True,
                                    value=str(ex["sets"]),
                                    on_change=lambda e, ex=ex: ex.update(sets=int(e.control.value or 1))
                                ),
                                ft.TextField(
                                    label="Propozycja obciążenia",
                                    expand=True,
                                    value=ex["suggested_weight"],
                                    on_change=lambda e, ex=ex: ex.update(suggested_weight=e.control.value)
                                ),
                                ft.TextField(
                                    label="Propozycja powtórzeń",
                                    expand=True,
                                    value=ex["suggested_reps"],
                                    on_change=lambda e, ex=ex: ex.update(suggested_reps=e.control.value)
                                ),
                                ft.TextField(
                                    label="Rest (sek)",
                                    expand=True,
                                    value=str(ex["rest_seconds"]),
                                    on_change=lambda e, ex=ex: ex.update(rest_seconds=int(e.control.value or 10))
                                ),
                                ft.TextField(
                                    label="Identyfikator superserii (dodaj taki sam dla ćwiczeń naprzemiennych)",
                                    expand=True,
                                    value=str(ex["superset_id"]),
                                    on_change=lambda e, ex=ex: ex.update(superset_id=e.control.value)
                                ),
                                ft.Text(""),
                            ]),
                            expanded=False, # Controls initial state
                            expanded_alignment=ft.Alignment.CENTER_LEFT,
                        )
                    )
                )
            )

        page.add(ft.Row([
            ft.Button("Zapisz", on_click=save_training),
            ft.TextButton("⬅ Wróć", on_click=show_home)
        ]))
        page.update()

    async def delete_training(event):
        await delete_training_from_list(event.control.data)
        hf = ft.HapticFeedback()
        await hf.vibrate()
        page.show_dialog(ft.AlertDialog(
                title=ft.Text("Trening usunięty"),
                content=ft.Text("W sumie smutno."),
                actions=[
                    ft.TextButton("Ok", on_click=lambda e: page.pop_dialog()),
                ],
                open=True,
        ))
        await show_home()

    async def start_training(event):
        page.controls.clear()

        training = await get_training(event.control.data) 
        sessions = await load_sessions()
        last_sessions = [s for s in sessions if s["training"] == event.control.data]
        if last_sessions:
            last_session = last_sessions[-1]
        else:
            last_session = None

        set_index = 0

        timer_text = ft.Text(size=40, weight="bold", width=2000, text_align="center")
        weight = ft.TextField(label="Obciążenie", expand=True)
        reps = ft.TextField(label="Powtórzenia", expand=True)
        notes = ft.TextField(label="Uwagi", expand=True)

        session = {
            "id": str(uuid.uuid4()),
            "date": datetime.datetime.now().timestamp(),
            "training": event.control.data,
            "sets": [],
        }

        sets = get_sets_list(training)
        if not sets:
            hf = ft.HapticFeedback()
            await hf.vibrate()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Trening pusty"),
                content=ft.Text("Wypełnij go ćwiczeniami dziku."),
                actions=[
                    ft.TextButton("Ogarnij się", on_click=lambda e: page.pop_dialog()),
                ],
                open=True,
            ))
            await show_home()
            return

        def add_set_header(page, ex, last_session, set_index):
            superset_string = f"Superseria {ex['superset_id']}: " if ex["superset_id"].strip() else ""
            max_weight, max_reps, session_date = get_pb_for_training(sessions, ex["id"])
            session_date = datetime.datetime.fromtimestamp(session_date)
            page.add(
                ft.Text(f"{superset_string}{ex['name']} – seria {ex['current_set']}/{ex['sets']}", size=22, width=2000, text_align="center"),
                ft.Text(f"Proponowane {ex['suggested_weight']} x {ex['suggested_reps']}", size=22, width=2000, text_align="center"),
            )
            if max_weight or max_reps:
                page.add(
                    ft.Text(f"Twój max: {max_weight} kg x {max_reps} ({session_date})", width=2000, text_align="center")
                )
            if last_session and set_index < len(last_session['sets']):
                last_set = last_session['sets'][set_index]
                page.add(
                    ft.Text(f"Ostatnio: {last_set['weight']} x {last_set['reps']} ({last_set['notes']})", width=2000, text_align="center")
                )

        async def start_rest():
            nonlocal set_index
            page.controls.clear()
            page.bgcolor = "#550022"

            ex = sets[set_index]
            add_set_header(page, ex, last_session, set_index)
            page.add(timer_text)

            for i in range(ex["rest_seconds"], -1, -1):
                timer_text.value = f"Rest: ⏱ {i}s"
                page.update()
                await asyncio.sleep(1)

            hf = ft.HapticFeedback()
            await hf.heavy_impact()
            await show_set_input()

        async def show_set_input():
            ex = sets[set_index]
            timer_text.value = f"Ładuj!"

            async def next_step(e):
                nonlocal set_index, session
                session["sets"].append({
                    "name": ex["name"],
                    "id": ex.get("id", ex["name"]),
                    "weight": weight.value or "brak",
                    "reps": reps.value or 0,
                    "notes": notes.value or "normalnie",
                    "set_index": ex["current_set"],
                })

                set_index += 1

                if set_index >= len(sets):
                    await end_session(e)
                    return
                
                await start_rest()

            async def end_session(e):
                nonlocal set_index, session
                sessions.append(session)
                await save_sessions(sessions)
                hf = ft.HapticFeedback()
                await hf.vibrate()
                page.show_dialog(ft.AlertDialog(
                    title=ft.Text("Trening zakończony"),
                    content=ft.Text("Co by o Tobie nie mówili na mieście, jesteś w porządku."),
                    actions=[
                        ft.TextButton("Napój dzika", on_click=lambda e: page.pop_dialog()),
                    ],
                    open=True,
                ))
                await show_home()
                return

            page.controls.clear()
            page.bgcolor = "#002255"

            add_set_header(page, ex, last_session, set_index)
            page.add(
                timer_text,
                weight,
                reps,
                notes,
                ft.Column([
                    ft.Button("Zapisz serię", on_click=next_step, width=2000, height=50),
                    ft.Button("Zakończ trening (bez ostatniej serii)", on_click=end_session, width=2000, height=50),
                ]),
            )
            page.update()

        await show_set_input()

    await show_home()


ft.run(main, upload_dir="uploads")

