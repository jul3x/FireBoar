import flet as ft
from dataclasses import dataclass
from typing import Callable
from fireboar.storage import load_trainings, load_sessions, get_archived_trainings, swap_trainings_order
from fireboar.imports import export_json, import_json, import_kate_entry, export_kate
from fireboar.utils import show_dialog, guard
from fireboar.training import Training, Session
from fireboar.version import VERSION, BUILD_DATETIME


logo = ft.Image(
    src="logo.png",
    width=300,
    height=300,
)


@dataclass
class UI:
    show_home: Callable
    add_training: Callable
    edit_training: Callable
    delete_training: Callable
    start_training: Callable
    show_sessions: Callable
    show_pb: Callable
    archive_training: Callable



async def home_ui(page: ft.Page, ui: UI, show_archived: bool = False):
    # Loading happens before anything is drawn, so without this the flet startup screen
    # (the logo) stays up for the whole read and a slow load is indistinguishable from a hang.
    status = ft.Text("Wczytuję dane...", size=18, text_align="center")
    page.controls.clear()
    page.bgcolor = "#222222"
    page.add(
        ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                [ft.ProgressRing(width=40, height=40), status],
                spacing=16,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
    )
    page.update()

    def show_progress(done: int, total: int):
        # every item would mean one round-trip to the UI per session - throttle it
        if total and (done == total or done % 10 == 0):
            status.value = f"Wczytuję sesyjki: {done}/{total}"
            page.update()

    trainings = await load_trainings()
    archived_trainings = await get_archived_trainings()
    sessions = await load_sessions(on_progress=show_progress)
    page.controls.clear()
    page.bgcolor = "#222222"

    file_picker = ft.FilePicker()
    async def _import_json_file(e):
        files = await file_picker.pick_files(
            allow_multiple=False,
            with_data=True,
        )
        await import_json(page, files)
        await home_ui(page, ui, show_archived=show_archived)
    import_json_file = guard(page, _import_json_file)

    async def _import_kate_file(e):
        await import_kate_entry(page, home_function=ui.show_home)
        await home_ui(page, ui, show_archived=show_archived)
    import_kate_file = guard(page, _import_kate_file)

    async def export_json_file(e):
        await export_json(file_picker)

    async def export_kate_file(e):
        await export_kate(file_picker)

    async def _move_training(e):
        await swap_trainings_order(e.control.data["id"], e.control.data["other"])
        await home_ui(page, ui, show_archived=show_archived)
    move_training = guard(page, _move_training)

    page.add(
        ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Column([
                    logo,
                    ft.Text("Poczuj w sobie siłę dzika!", size=20, weight="bold", text_align="center"),
                    ft.Text(""),
                    ft.Button("💪 Dodaj trening", on_click=ui.add_training, expand=True, width=4000, height=50),
                    ft.Button("📤 Wgraj arkusz Google", on_click=import_kate_file, expand=True, width=4000, height=50),
                    ft.Button("💾 Zapisz arkusz", on_click=export_kate_file, expand=True, width=4000, height=50),
                    ft.Button("♻️ Wgraj backup", on_click=import_json_file, expand=True, width=4000, height=50),
                    ft.Button("🛟 Zrób backup", on_click=export_json_file, expand=True, width=4000, height=50),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )

    visible_trainings = [t for t in trainings if (t.id in archived_trainings) == show_archived]

    for i, t in enumerate(visible_trainings):
        is_first = i == 0
        is_last = i == len(visible_trainings) - 1
        sessions_for_t = t.get_sessions(sessions)
        page.add(
            ft.Card(
                ft.Container(
                    padding=10,
                    content=ft.Column([
                          ft.Text("Trening: " + t.name, size=18, weight="bold", margin=10),
                          ft.Text(f"ćwiczeń: {len(t.exercises)}, było łojone: {len(sessions_for_t)} razy", size=14, margin=ft.Margin(left=10, right=10)),
                        ft.Column([
                            ft.Row([
                                ft.TextButton("▶ Start", on_click=ui.start_training, data=t.id),
                                ft.TextButton("🚀 Sesyjki", on_click=ui.show_sessions, data=t),
                                ft.TextButton("🥇 Maxy", on_click=ui.show_pb, data=t),
                            ]),
                            ft.Row([
                                ft.TextButton("✏ Edytuj", on_click=ui.edit_training, data=t.id),
                                ft.TextButton("🗑️ Usuń", on_click=ui.delete_training, data=t.id),
                                ft.TextButton(
                                    f"📂 {'Przywróć' if show_archived else 'Archiwizuj'}",
                                    on_click=ui.archive_training, data={
                                        "id": t.id,
                                        "dearchive": show_archived,
                                    }
                                ),
                            ]),
                            ft.Row([
                                ft.TextButton(
                                    "⬆ Wyżej",
                                    on_click=move_training,
                                    disabled=is_first,
                                    data={
                                        "id": t.id,
                                        "other": visible_trainings[i - 1].id if not is_first else t.id,
                                    },
                                ),
                                ft.TextButton(
                                    "⬇ Niżej",
                                    on_click=move_training,
                                    disabled=is_last,
                                    data={
                                        "id": t.id,
                                        "other": visible_trainings[i + 1].id if not is_last else t.id,
                                    },
                                ),
                            ]),
                        ])
                    ]),
                )
            )
        )

    async def _show_trainings(e):
        if show_archived:
            await home_ui(page, ui, False)
        else:
            await home_ui(page, ui, True)
    show_trainings = guard(page, _show_trainings)

    page.add(
        ft.Button(
            "Pokaż aktualne" if show_archived else "Pokaż zarchiwizowane",
            on_click=show_trainings, expand=True, width=4000, height=50
        ),
        ft.Text(
            f"v{VERSION} · {BUILD_DATETIME}",
            size=11,
            color="#555555",
            text_align="center",
            width=4000,
        ),
    )

    page.update()
