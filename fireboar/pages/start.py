import asyncio
import flet as ft
from fireboar.storage import load_trainings, load_sessions, save_sessions
from fireboar.utils import show_dialog
from fireboar.training import Training, Session, PersonalBest, SessionSet


def add_set_header(page: ft.Page, ex: SessionSet, sessions: list[Session], last_session: Session | None, set_index: int):
    pb = PersonalBest.get_pb_for_training(sessions, ex.exercise.id)
    for header in ex.get_header():
        page.add(ft.Text(header, size=22, width=2000, text_align="center"))
        page.add(ft.Divider())
    if pb:
        page.add(ft.Text(pb.get_str(), size=22, width=2000, text_align="center"))
        page.add(ft.Divider())
    if last_session and set_index < len(last_session.sets):
        last_set = last_session.sets[set_index]
        page.add(ft.Text(last_set.get_last_info(), size=22, width=2000, text_align="center"))
        page.add(ft.Divider())


async def start_entry_ui(training: Training, sessions: list[Session], page: ft.Page, home_function):
    page.controls.clear()
    sets = training.get_sets_list()
    if not sets:
        await show_dialog(page, "Trening pusty", "Wypełnij go ćwiczeniami dziku.", "Ogarnij")
        await home_function()
        return

    last_sessions = training.get_sessions(sessions)
    if last_sessions:
        last_session = last_sessions[-1]
    else:
        last_session = None

    async def start_training():
        await start_ui(training, sessions, last_session, page, home_function)

    page.add(
        ft.Text(f"Trening: {training.name}", size=26, width=2000, text_align="center", weight=ft.FontWeight.BOLD),
        ft.Text("Lecimy z tematem.", size=26, width=2000, text_align="center", weight=ft.FontWeight.BOLD),
    )
    add_set_header(page, sets[0], sessions, last_session, 0)
    page.add(
        ft.Button("Jedziesz dziku!", on_click=start_training, width=2000, height=50),
        ft.Button("Wróć", on_click=home_function, width=2000, height=50),
    )
    page.update()


async def start_ui(training: Training, sessions: list[Session], last_session: Session | None, page: ft.Page, home_function):
    page.controls.clear()

    set_index = 0

    timer_text = ft.Text(size=40, weight="bold", width=2000, text_align="center")
    weight = ft.TextField(label="Obciążenie", expand=True)
    reps = ft.TextField(label="Powtórzenia", expand=True)
    notes = ft.TextField(label="Uwagi", expand=True)

    session = Session(training=training.id)
    sets = training.get_sets_list()

    async def start_rest():
        nonlocal set_index
        page.controls.clear()
        page.bgcolor = "#550022"

        ex = sets[set_index]
        add_set_header(page, ex, sessions, last_session, set_index)
        page.add(timer_text)

        for i in range(ex.exercise.rest_seconds, -1, -1):
            timer_text.value = f"Rest: ⏱ {i}s"
            if i < 4:
                timer_text.value += "\nPrzygotuj się!"
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
            sets[set_index].weight = weight.value or "brak"
            sets[set_index].reps = reps.value or 0
            sets[set_index].notes = notes.value or "normalnie"
            session.sets.append(sets[set_index])

            set_index += 1
            if set_index >= len(sets):
                await end_session(e)
                return

            await start_rest()

        async def end_session(e):
            nonlocal set_index, session
            sessions.append(session)
            await save_sessions(sessions)
            await show_dialog(
                page,
                "Trening zakończony",
                "Co by o Tobie nie mówili na mieście, jesteś w porządku.",
                "Odpocznij dziku",
            )
            await home_function()
            return

        page.controls.clear()
        page.bgcolor = "#002255"

        add_set_header(page, ex, sessions, last_session, set_index)
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


