import flet as ft
from fireboar.storage import delete_session_from_list, load_sessions
from fireboar.utils import show_dialog
from fireboar.training import Training, Session


async def sessions_show_ui(training: Training, sessions: list[Session], page: ft.Page, home_function):
    page.controls.clear()
    page.add(
        ft.Text(f"Sesyjki dla treningu: {training.name}", size=24),
    )

    async def delete_session(e):
        await delete_session_from_list(e.control.data)
        e.control.data = training
        await show_dialog(
            page,
            "Sesyjka usunięta",
            "Wstydzisz się ciężaru?",
            "Dzień chrabonszcza",
        )
        sessions = await load_sessions()
        await sessions_show_ui(training, sessions, page, home_function)

    for session_idx, s in enumerate(sessions):
        sets_text = [
            ft.Text(f"{set_idx+1}. Ćw. {set.get_name()}, Seria {set.set_index}, {set.weight} x {set.reps}, uwagi: {set.notes}") for set_idx, set in enumerate(s.sets)
        ]
        page.add(
            ft.Card(
                ft.Container(
                    padding=10,
                    content=ft.ExpansionTile(
                        title=ft.Row(controls=[
                            ft.Text(f"{session_idx + 1}. Data: {s.get_date()}", size=18, weight="bold"),
                            ft.Button("Usuń", on_click=delete_session, data=s.id)
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
        ft.TextButton("⬅ Wróć", on_click=home_function)
    )
    page.update()
