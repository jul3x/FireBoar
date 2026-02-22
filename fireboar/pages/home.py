import flet as ft
from fireboar.storage import load_trainings, load_sessions, upload_json, export_json, import_json
from fireboar.utils import show_dialog
from fireboar.training import Training, Session


logo = ft.Image(
    src="logo.png",
    width=300,
    height=300,
)

async def home_ui(page: ft.Page, add_training, edit_training, delete_training, start_training, show_sessions, show_pb):
    trainings = await load_trainings()
    sessions = await load_sessions()
    page.controls.clear()
    page.bgcolor = "#222222"

    async def upload_json_file(e):
        await upload_json(e, page)
        await home_ui(page, add_training, edit_training, delete_training, start_training, show_sessions)

    json_file_picker = ft.FilePicker(on_upload=upload_json_file)

    async def import_json_file(e):
        await import_json(e, page, json_file_picker)

    async def export_json_file(e):
        await export_json(e, json_file_picker)

    page.add(
        ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Column([
                    logo,
                    ft.Text("Poczuj w sobie siłę dzika!", size=20, weight="bold", text_align="center"),
                    ft.Text(""),
                    ft.Button("➕ Dodaj trening", on_click=add_training, expand=True, width=4000, height=50),
                    ft.Button("↗ Importuj JSON", on_click=import_json_file, expand=True, width=4000, height=50),
                    ft.Button("↘ Eksportuj JSON", on_click=export_json_file, expand=True, width=4000, height=50)

                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )

    for t in trainings:
        sessions_for_t = t.get_sessions(sessions)
        page.add(
            ft.Card(
                ft.Container(
                    padding=10,
                    content=ft.Column([
                        ft.Row([ft.Text(t.name, size=18, weight="bold", margin=10),
                                ft.Text(f"ćwiczeń: {len(t.exercises)}, było łojone: {len(sessions_for_t)} razy", size=14),
                        ]),
                        ft.Column([
                            ft.Row([
                                ft.TextButton("▶ Start", on_click=start_training, data=t.id),
                                ft.TextButton("🚀 Sesyjki", on_click=show_sessions, data=t),
                                ft.TextButton("🥇 Maxy", on_click=show_pb, data=t),
                            ]),
                            ft.Row([
                                ft.TextButton("✏ Edytuj", on_click=edit_training, data=t.id),
                                ft.TextButton("🗑️ Usuń", on_click=delete_training, data=t.id),
                            ]),
                        ])
                    ]),
                )
            )
        )

    page.update()
