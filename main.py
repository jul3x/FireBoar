import os
import flet as ft
import uuid
import asyncio
import json
import datetime
import shutil
from pathlib import Path

# TODO: Organize code
# TODO: Rewrite this for better DB structure
# TODO: Add fingerboarding intervals type training
# TODO: Handle Core training exercises
# TODO: Show PB on current set, not only last time
# TODO: Mark sessions with PB and historical PB
# TODO: Import from XLSX
# TODO: Export to XLSX
# TODO: Deployment to phones
# TODO: Better layout
# TODO: Add FireBoar logo

trainings_path = os.path.join("assets", "trainings.json")
sessions_path = os.path.join("assets", "sessions.json")

async def load_trainings(page: ft.Page):
    with open(trainings_path) as f:
        db = json.loads(f.read())
    raw = db or []
    return raw

async def load_sessions(page: ft.Page):
    with open(sessions_path) as f:
        db = json.loads(f.read())
    raw = db or []
    return raw

async def save_trainings(page: ft.Page, trainings):
    with open(trainings_path, "w") as f:
        f.write(json.dumps(trainings))

async def save_sessions(page: ft.Page, sessions):
    with open(sessions_path, "w") as f:
        f.write(json.dumps(sessions))

async def get_training(page: ft.Page, id: str):
    trainings = await load_trainings(page)
    return [t for t in trainings if t["id"] == id][0]

async def delete_training_from_list(page: ft.Page, id: str):
    trainings = await load_trainings(page)
    await save_trainings(page, [t for t in trainings if t["id"] != id])

async def delete_session_from_list(page: ft.Page, id: str):
    sessions = await load_sessions(page)
    await save_sessions(page, [s for s in sessions if s["id"] != id])

def create_if_not_exists(path: str):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("[]")

def get_sets_list(training: dict):
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
    create_if_not_exists(trainings_path)
    create_if_not_exists(sessions_path)

    async def show_home():
        trainings = await load_trainings(page)
        sessions = await load_sessions(page)
        page.controls.clear()
        page.bgcolor = "#222222"


        async def upload_json_file(e):
            if e.progress != 1.0:
                return
            # TODO - data verification
            shutil.copyfile(Path("uploads") / Path("trainings.json"), trainings_path) 
            await save_sessions(page, [])
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

        json_file_picker = ft.FilePicker(on_upload=upload_json_file)

        page.add(
            ft.Text("🏋️ FireBoar - poczuj w sobie siłę dzika", size=26, weight="bold"),
            ft.Row([
                ft.Button("➕ Dodaj trening", on_click=show_add_training),
                ft.Button("> Importuj JSON", on_click=import_json_file),
                ft.Button("< Eksportuj JSON", disabled=False)
            ]),
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
                            ft.Row([
                                ft.TextButton("▶ Start", on_click=start_training, data=t["id"]),
                                ft.TextButton("✏ Edytuj", on_click=edit_training, data=t["id"]),
                                ft.TextButton("✏ Usuń", on_click=delete_training, data=t["id"]),
                                ft.TextButton("✏ Pokaż sesyjki", on_click=show_sessions, data=t),
                            ])
                        ])
                    )
                )
            )

        page.update()

    async def show_sessions(e):
        sessions = await load_sessions(page)
        training_data = e.control.data
        sessions_for_t = [s for s in sessions if s["training"] == training_data["id"]]
        page.controls.clear()
        page.add(
            ft.Text(f"Sesyjki dla treningu: {training_data['name']}", size=24),
        )

        async def delete_session(e):
            await delete_session_from_list(page, e.control.data)
            e.control.data = training_data
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
                                ft.Text(f"{session_idx+1}. Data: {datetime.datetime.fromtimestamp(s['date'])}", size=18, weight="bold"),
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
            trainings = await load_trainings(page)
            trainings.append({
                "id": str(uuid.uuid4()),
                "name": name.value,
                "exercises": []
            })
            await save_trainings(page, trainings)
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
        trainings = await load_trainings(page)
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
            await save_trainings(page, trainings)
            await edit_training(e)

        async def remove_exercise(e):
            trainings[idx]["exercises"] = [ex for ex in trainings[idx]["exercises"] if ex["id"] != e.control.data]
            await save_trainings(page, trainings)
            await edit_training(e)

        async def save_training(e):
            await save_trainings(page, trainings)
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
                        width=600,
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
                                    width=600,
                                    value=ex["name"],
                                    on_change=lambda e, ex=ex: ex.update(name=e.control.value)
                                ),
                                ft.TextField(
                                    label="Serie",
                                    width=600,
                                    value=str(ex["sets"]),
                                    on_change=lambda e, ex=ex: ex.update(sets=int(e.control.value or 1))
                                ),
                                ft.TextField(
                                    label="Propozycja obciążenia",
                                    width=600,
                                    value=ex["suggested_weight"],
                                    on_change=lambda e, ex=ex: ex.update(suggested_weight=e.control.value)
                                ),
                                ft.TextField(
                                    label="Propozycja powtórzeń",
                                    width=600,
                                    value=ex["suggested_reps"],
                                    on_change=lambda e, ex=ex: ex.update(suggested_reps=e.control.value)
                                ),
                                ft.TextField(
                                    label="Rest (sek)",
                                    width=600,
                                    value=str(ex["rest_seconds"]),
                                    on_change=lambda e, ex=ex: ex.update(rest_seconds=int(e.control.value or 10))
                                ),
                                ft.TextField(
                                    label="Identyfikator superserii (dodaj taki sam dla ćwiczeń naprzemiennych)",
                                    width=600,
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
        await delete_training_from_list(page, event.control.data)
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

        training = await get_training(page, event.control.data) 
        sessions = await load_sessions(page)
        last_sessions = [s for s in sessions if s["training"] == event.control.data]
        if last_sessions:
            last_session = last_sessions[-1]
        else:
            last_session = None

        set_index = 0

        timer_text = ft.Text(size=40, weight="bold")
        weight = ft.TextField(label="Obciążenie")
        reps = ft.TextField(label="Powtórzenia")
        notes = ft.TextField(label="Uwagi")

        session = {
            "id": str(uuid.uuid4()),
            "date": datetime.datetime.now().timestamp(),
            "training": event.control.data,
            "sets": [],
        }

        sets = get_sets_list(training)
        if not sets:
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
            page.add(
                ft.Text(f"{superset_string}{ex['name']} – seria {ex['current_set']}/{ex['sets']}", size=22),
                ft.Text(f"Proponowane {ex['suggested_weight']} x {ex['suggested_reps']}", size=22),
            )
            if last_session and set_index < len(last_session['sets']):
                last_set = last_session['sets'][set_index]
                page.add(
                    ft.Text(f"Ostatnio: {last_set['weight']} x {last_set['reps']} ({last_set['notes']})")
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
                await save_sessions(page, sessions)
                page.controls.clear()
                page.add(
                    ft.Row([
                        ft.Text("✅ Trening zakończony"),
                        ft.TextButton("⬅ Wróć", on_click=show_home)
                    ])
                )
                page.update()

            page.controls.clear()
            page.bgcolor = "#002255"

            add_set_header(page, ex, last_session, set_index)
            page.add(
                timer_text,
                weight,
                reps,
                notes,
                ft.Row([
                    ft.Button("Zapisz serię", on_click=next_step),
                    ft.Button("Zakończ trening (bez ostatniej serii)", on_click=end_session),
                ]),
            )
            page.update()

        await show_set_input()

    await show_home()


ft.run(main, upload_dir="uploads")

