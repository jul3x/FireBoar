import asyncio
import flet as ft
from fireboar.storage import load_trainings, load_sessions, save_sessions
from fireboar.utils import show_dialog
from fireboar.training import Training, Session, PersonalBest, SessionSet, TrainingAction, TrainingActionType


def add_set_header(page: ft.Page, ex: SessionSet, action: TrainingAction | None, sessions: list[Session], last_session: Session | None, set_index: int):
    pb = PersonalBest.get_pb_for_training(sessions, ex.exercise.id)
    card = ft.Card(
       ft.Container(
           padding=20,
           margin=10,
           content=ft.Column([
           ]),
       ),
       margin=ft.Margin(bottom=15, top=15),
    )
    for header in ex.get_header(action):
        card.content.content.controls.append(ft.Text(header, size=22, width=4000, text_align="center"))
        card.content.content.controls.append(ft.Divider(color="#aaaaaa"))

    if pb:
        card.content.content.controls.append(ft.Text("🥇 Twój max: " + pb.get_str(), size=22, width=4000, text_align="center"))
        card.content.content.controls.append(ft.Divider(color="#aaaaaa"))
    if last_session and set_index < len(last_session.sets):
        last_set = last_session.sets[set_index]
        card.content.content.controls.append(ft.Text(last_set.get_last_info(), size=22, width=4000, text_align="center"))
        card.content.content.controls.append(ft.Divider(color="#aaaaaa"))

    # Last is always divider. remove it.
    card.content.content.controls = card.content.content.controls[:-1]

    page.add(card)


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
        ft.Text(""),
        ft.Text(f"Trening: {training.name}", size=26, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
        ft.Text("Lecimy z tematem.", size=26, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
        ft.Text("Jeśliś rozgrzany to dawaj.", size=26, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
    )
    add_set_header(page, sets[0], None, sessions, last_session, 0)
    page.add(
        ft.Button("Jedziesz dziku!", on_click=start_training, width=4000, height=50),
        ft.Button("Wróć", on_click=home_function, width=4000, height=50),
    )
    page.update()


async def start_ui(training: Training, sessions: list[Session], last_session: Session | None, page: ft.Page, home_function):
    page.controls.clear()

    timer_text = ft.Text(size=40, weight="bold", width=4000, text_align="center")
    weight = ft.TextField(label="Obciążenie", border_color="#555555", color="#ffffff", bgcolor="#222222", expand=True)
    reps = ft.TextField(label="Powtórzenia", border_color="#555555", color="#ffffff", bgcolor="#222222", expand=True)
    notes = ft.TextField(label="Uwagi", border_color="#555555", color="#ffffff", bgcolor="#222222", expand=True)

    session = Session(training=training.id)
    sets = training.get_sets_list()

    async def save_set(e):
        exited_flag = e.control.data
        nonlocal session
        sets[set_index].weight = weight.value or "brak"
        sets[set_index].reps = reps.value or 0
        sets[set_index].notes = notes.value or "normalnie"
        session.sets.append(sets[set_index])
        exited_flag.set()

    async def end_session(e):
        nonlocal session
        sessions.append(session)
        await save_sessions(sessions)
        await show_dialog(
            page,
            "Trening zakończony",
            "Co by o Tobie nie mówili na mieście, jesteś w porządku.",
            "Odpocznij dziku",
        )
        if e:
            saved_flag, exited_flag = e.control.data
            # Please keep this order
            exited_flag.set()
            saved_flag.set()

    async def start_rest(action=None, is_start=False, next_set=None):
        page.controls.clear()
        page.bgcolor = "#004422"

        ex = sets[set_index]
        page.add(timer_text)
        add_set_header(page, next_set or ex, action, sessions, last_session, set_index)

        timer_seconds = ex.exercise.rest_seconds if not is_start else 10
        for i in range(timer_seconds, 0, -1):
            if is_start:
                timer_text.value = f"\nStartujemy za: \n⏱ {i}s\n"
            else:
                timer_text.value = f"\nRest: \n⏱ {i}s\n"
            if i < 4:
                timer_text.value += "Przygotuj się!\n"
            page.update()
            await asyncio.sleep(1)

        hf = ft.HapticFeedback()
        await hf.heavy_impact()

    async def start_rest_interval(action):
        page.controls.clear()
        page.bgcolor = "#996600"

        ex = sets[set_index]
        page.add(timer_text)
        add_set_header(page, ex, action, sessions, last_session, set_index)

        timer_seconds = ex.exercise.interval_config.rest_time
        for i in range(timer_seconds, 0, -1):
            timer_text.value = f"\nRest interwałowy: \n⏱ {i}s\n"
            if i < 4:
                timer_text.value += "Przygotuj się!\n"
            page.update()
            await asyncio.sleep(1)

        hf = ft.HapticFeedback()
        await hf.heavy_impact()

    async def start_working_interval(action):
        page.controls.clear()
        page.bgcolor = "#550000"

        ex = sets[set_index]
        page.add(timer_text)
        add_set_header(page, ex, action, sessions, last_session, set_index)

        timer_seconds = ex.exercise.interval_config.working_time
        for i in range(timer_seconds, 0, -1):
            timer_text.value = f"\nŁaduj: ⏱ {i}s\n"
            if i < 4:
                timer_text.value += "Już prawie...\n"
            page.update()
            await asyncio.sleep(1)

        hf = ft.HapticFeedback()
        await hf.heavy_impact()

    async def show_set_input(saved, exited, action):
        ex = sets[set_index]
        timer_text.value = f"\nŁaduj i podsumuj!"

        page.controls.clear()
        page.bgcolor = "#222222"

        page.add(
            timer_text,
            weight,
            reps,
            notes,
            ft.Column([
                ft.Button("Zapisz serię", on_click=save_set, data=saved, width=4000, height=50),
                ft.Button("Zakończ trening (bez ostatniej serii)", on_click=end_session, data=[saved, exited], width=4000, height=50),
            ]),
        )
        add_set_header(page, ex, action, sessions, last_session, set_index)
        page.update()

    for set_index in range(len(sets)):
        actions = sets[set_index].get_action_list()
        if set_index == 0:
            await start_rest(action=actions[0], is_start=True)

        for action_index, action in enumerate(actions):
            page.update()
            if action.action == TrainingActionType.REST:
                # No rest at the end of session
                if set_index == len(sets) - 1 and action_index == len(actions) - 1:
                    continue

                next_set = sets[set_index + 1] if set_index < len(sets) - 1 else None

                await start_rest(next_set=next_set, action=action)
            elif action.action == TrainingActionType.SUMMARY:
                saved = asyncio.Event()
                exited = asyncio.Event()
                await show_set_input(saved, exited, action=action)
                await saved.wait()

                if exited.is_set():
                    await home_function()
                    return
            elif action.action == TrainingActionType.INTERVAL_WORK:
                await start_working_interval(action=action)
            elif action.action == TrainingActionType.INTERVAL_REST:
                await start_rest_interval(action=action)

    await end_session(None)
    await home_function()
