import flet as ft
from fireboar.storage import delete_session_from_list, load_sessions
from fireboar.utils import show_dialog, guard
from fireboar.training import Training, Session, PersonalBest


async def sessions_show_ui(training: Training, sessions: list[Session], page: ft.Page, home_function):
    page.controls.clear()
    page.add(
        ft.Text(f"Sesyjki dla treningu: {training.name}", size=24, width=4000, text_align="center", margin=10),
    )

    async def delete_session(e):
        async def _delete_session_confirmed():
            await delete_session_from_list(e.control.data)
            sessions = await load_sessions()
            sessions_for_t = training.get_sessions(sessions)
            await sessions_show_ui(training, sessions_for_t, page, home_function)
        delete_session_confirmed = guard(page, _delete_session_confirmed)
        await show_dialog(
            page,
            "Usunąć sesyjkę?",
            "Wstydzisz się ciężaru?",
            "Dzień chrabonszcza",
            action_cb=delete_session_confirmed,
        )

    pbs = {exercise.id: PersonalBest.get_pb_for_training(sessions, exercise.id) for exercise in training.exercises}
    for session_idx, s in enumerate(sessions):
        sets_text = []

        for set_idx, set in enumerate(s.sets):
            set_suffix = ""
            pb = pbs.get(set.get_id())
            if pb and pb.session.id == s.id and pb.session_set.set_index == set.set_index:
                set_suffix = " 🥇"
            sets_text.append(
                ft.Text(
                    f"{set_idx+1}. Ćw. {set.get_name()}, Seria {set.set_index}, {set.weight} x {set.reps}, uwagi: {set.notes}{set_suffix}",
                    margin=ft.Margin(left=10, right=10),
                )
            )
        session_suffix = ""
        if s.id in {pb.session.id for pb in pbs.values() if pb}:
            session_suffix = " 🥇"
        page.add(
            ft.Card(
                ft.Container(
                    padding=10,
                    content=ft.ExpansionTile(
                        title=ft.Text(f"{session_idx + 1}. Data: {s.get_date()}{session_suffix}", size=18, weight="bold"),
                        controls=ft.Column(
                            controls=[
                                ft.Text(""),
                                ft.Button("Usuń", on_click=delete_session, data=s.id),
                                ft.Text(""),
                                *sets_text,
                                ft.Text(""),
                            ]
                        ),
                        expanded=False,
                        expanded_alignment=ft.Alignment.CENTER_LEFT,
                    )
                )
            )
        )

    page.add(
        ft.TextButton("⬅ Wróć", on_click=home_function)
    )
    page.update()


async def pb_show_ui(training: Training, sessions: list[Session], page: ft.Page, home_function):
    page.controls.clear()
    page.add(
        ft.Text(f"Maxy dla: {training.name}", size=24, width=4000, text_align="center", margin=10),
    )

    last_sessions = training.get_sessions(sessions)
    if last_sessions:
        last_session = last_sessions[-1]
    else:
        last_session = None

    for exercise_idx, exercise in enumerate(training.exercises):
        personal_best = PersonalBest.get_pb_for_training(sessions, exercise.id)

        if last_session:
            last_session_best = PersonalBest.get_pb_for_training([last_session], exercise.id)
        else:
            last_session_best = None
        page.add(
            ft.Card(
                ft.Container(
                    padding=10,
                    content=ft.ExpansionTile(
                        title=ft.Text(f"{exercise.name}", size=18, weight="bold"),
                        controls=ft.Column(
                            controls=[
                                ft.Text("🥇 Twój max: " + (personal_best.get_str() if personal_best else "brak"), margin=10, size=16),
                                ft.Text("⌚ Ostatnio: " + (last_session_best.get_str() if last_session_best else "brak"), margin=10, size=16),
                            ]
                        ),
                        expanded=True,
                        expanded_alignment=ft.Alignment.CENTER_LEFT,
                    )
                )
            )
        )

    page.add(
        ft.TextButton("⬅ Wróć", on_click=home_function)
    )
    page.update()
