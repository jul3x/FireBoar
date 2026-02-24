import flet as ft
from dataclasses import dataclass
from typing import Callable
from fireboar.storage import load_trainings, load_sessions, get_archived_trainings
from fireboar.imports import export_json, import_json, import_kate_entry
from fireboar.utils import show_dialog
from fireboar.training import Training, Session


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
    trainings = await load_trainings()
    archived_trainings = await get_archived_trainings()
    sessions = await load_sessions()
    page.controls.clear()
    page.bgcolor = "#222222"

    file_picker = ft.FilePicker()
    async def import_json_file(e):
        files = await file_picker.pick_files(
            allow_multiple=False,
            with_data=True,
        )
        await import_json(page, files)
        await home_ui(page, ui, show_archived=show_archived)

    async def import_kate_file(e):
        await import_kate_entry(page, home_function=ui.show_home)
        await home_ui(page, ui, show_archived=show_archived)

    async def export_json_file(e):
        await export_json(file_picker)

    kate_button = ft.Button("↗ Wgraj arkusz Google", on_click=import_kate_file, expand=True, width=4000, height=50)
    page.add(
        ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Column([
                    logo,
                    ft.Text("Poczuj w sobie siłę dzika!", size=20, weight="bold", text_align="center"),
                    ft.Text(""),
                    ft.Button("➕ Dodaj trening", on_click=ui.add_training, expand=True, width=4000, height=50),
                    kate_button,
                    ft.Button("↗ Wgraj backup", on_click=import_json_file, expand=True, width=4000, height=50),
                    ft.Button("↘ Zrób backup", on_click=export_json_file, expand=True, width=4000, height=50),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )

    for t in trainings:
        if not show_archived and t.id in archived_trainings:
            continue

        if show_archived and t.id not in archived_trainings:
            continue

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
                        ])
                    ]),
                )
            )
        )

    async def show_trainings(e):
        if show_archived:
            await home_ui(page, ui, False)
        else:
            await home_ui(page, ui, True)

    page.add(
        ft.Button(
            "Pokaż aktualne" if show_archived else "Pokaż zarchiwizowane",
            on_click=show_trainings, expand=True, width=4000, height=50
        ),
    )

    page.update()
