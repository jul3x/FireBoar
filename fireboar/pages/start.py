import asyncio
import math
import time
import flet as ft
import flet_audio as fta
from fireboar.storage import load_trainings, load_sessions, save_sessions, save_training
from fireboar.utils import show_dialog, guard, normalize_string
from fireboar.training import Training, Session, PersonalBest, SessionSet, TrainingAction, TrainingActionType
try:
    from js import navigator
except ImportError:
    navigator = None


def add_set_header(page: ft.Page, ex: SessionSet, action: TrainingAction | None, is_next: bool = False):
    card = ft.Card(
       ft.Container(
           padding=20,
           margin=10,
           content=ft.Column([
           ]),
       ),
       margin=ft.Margin(bottom=15, top=15),
    )

    if is_next:
        card.content.content.controls.append(ft.Text("Następne:", size=22, width=4000, text_align="center"))
    for header in ex.get_header(action):
        card.content.content.controls.append(ft.Text(header, weight="bold", size=22, width=4000, text_align="center"))
        card.content.content.controls.append(ft.Divider(color="#aaaaaa"))

    # Last is always divider. remove it.
    card.content.content.controls = card.content.content.controls[:-1]
    page.add(card)


def add_set_metadata(page: ft.Page, ex: SessionSet, sessions: list[Session], last_session: Session | None):
    card = ft.Card(
       ft.Container(
           padding=20,
           margin=5,
           content=ft.Column([
           ]),
       ),
       margin=ft.Margin(bottom=15, top=15),
    )
    has_progression = bool(ex.exercise and ex.exercise.progression)
    suggestion_color = None if has_progression else "#88ff88"
    card.content.content.controls.append(ft.Text(ex.get_suggestions(), size=22, width=4000, text_align="center", color=suggestion_color))
    pb = PersonalBest.get_pb_for_training(sessions, ex.exercise.id)
    if pb:
        card.content.content.controls.append(ft.Divider(color="#aaaaaa"))
        card.content.content.controls.append(ft.Text("🥇 Twój max: " + pb.get_str(), size=22, width=4000, text_align="center"))
    if last_session and ex.set_index < len(last_session.sets):
        card.content.content.controls.append(ft.Divider(color="#aaaaaa"))
        last_set = last_session.sets[ex.set_index]
        card.content.content.controls.append(ft.Text(last_set.get_last_info(), size=22, width=4000, text_align="center"))

    if last_session and ex.exercise and ex.exercise.progression:
        prog = ex.exercise.progression
        prog_last_set = None
        for s in last_session.sets:
            if s.get_id() == ex.get_id() and s.set_index == ex.set_index:
                prog_last_set = s
                break
        if prog_last_set:
            last_w = normalize_string(prog_last_set.weight)
            last_r = int(normalize_string(prog_last_set.reps))
            new_w = last_w + prog.weight_increment
            new_r = last_r + prog.reps_increment
            w_str = f"{new_w:g} kg" if new_w > 0 else "brak"
            card.content.content.controls.append(ft.Divider(color="#aaaaaa"))
            card.content.content.controls.append(
                ft.Text(f"📈 Na dziś: {w_str} x {new_r}", size=22, width=4000, text_align="center", color="#88ff88")
            )

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

    async def start_training(e):
        await start_ui(training, sessions, last_session, page, home_function)

    page.add(
        ft.Text(""),
        ft.Text(f"Trening: {training.name}", size=26, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
        ft.Text("Lecimy z tematem.", size=26, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
        ft.Text("Jeśliś rozgrzany to dawaj.", size=26, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
    )

    exercises_with_plans = [ex for ex in training.exercises if ex.has_session_plans()]
    if exercises_with_plans:
        page.add(ft.Text("Wybierz plan sesji:", size=20, width=4000, text_align="center", color="#ffaa44"))
        for ex in exercises_with_plans:
            plan_col = ft.Column([])

            def make_plan_callbacks(ex, plan_col):
                def build():
                    plan_col.controls.clear()
                    idx = ex.current_plan_index % len(ex.session_plans)
                    plan = ex.session_plans[idx]
                    plan_col.controls.append(
                        ft.Text(
                            f"Sesja {idx + 1} / {len(ex.session_plans)}",
                            size=18, width=4000, text_align="center", weight=ft.FontWeight.BOLD,
                        )
                    )
                    for i, es in enumerate(plan.sets):
                        w = es.suggested_weight or "brak"
                        r = es.suggested_reps or "?"
                        plan_col.controls.append(
                            ft.Text(f"S{i + 1}: {w} x {r}", size=16, width=4000, text_align="center")
                        )

                def prev_plan(e):
                    ex.current_plan_index = (ex.current_plan_index - 1) % len(ex.session_plans)
                    build()
                    page.update()

                def next_plan(e):
                    ex.current_plan_index = (ex.current_plan_index + 1) % len(ex.session_plans)
                    build()
                    page.update()

                build()
                return prev_plan, next_plan

            prev_cb, next_cb = make_plan_callbacks(ex, plan_col)
            page.add(
                ft.Card(
                    ft.Container(
                        padding=15,
                        content=ft.Column([
                            ft.Text(ex.name, size=20, width=4000, text_align="center", weight=ft.FontWeight.BOLD),
                            plan_col,
                            ft.Row([
                                ft.Button("← Poprzednia", on_click=prev_cb, expand=True),
                                ft.Button("Następna →", on_click=next_cb, expand=True),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                        ]),
                    )
                )
            )

    add_set_header(page, ex=sets[0], action=None)
    if not sets[0].exercise.has_session_plans():
        add_set_metadata(page, ex=sets[0], sessions=last_sessions, last_session=last_session)
    page.add(
        ft.Button("Jedziesz dziku!", on_click=start_training, width=4000, height=50),
        ft.Button("Wróć", on_click=home_function, width=4000, height=50),
    )
    page.update()


async def start_ui(training: Training, sessions: list[Session], last_session: Session | None, page: ft.Page, home_function):
    page.controls.clear()
    beep=fta.Audio("beep.mp3", release_mode=fta.ReleaseMode.STOP)

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

    async def _end_session(e):
        nonlocal session
        sessions.append(session)
        await save_sessions(sessions)
        for ex in training.exercises:
            if ex.has_session_plans():
                ex.current_plan_index = (ex.current_plan_index + 1) % len(ex.session_plans)
        await save_training(training)
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
    end_session = guard(page, _end_session)

    async def play_beep():
        try:
            await asyncio.wait_for(beep.play(), timeout=3)
        except asyncio.TimeoutError:
            print("Timeouted waiting for beep to play")
        except Exception as e:
            print(f"Failed to play beep: {e}")

    async def _acquire_wake_lock():
        if navigator is None:
            return None
        try:
            return await navigator.wakeLock.request("screen")
        except Exception as e:
            print(f"Wake lock not available: {e}")
            return None

    def _release_wake_lock(wake_lock):
        if wake_lock is not None:
            try:
                wake_lock.release()
            except Exception:
                pass

    async def _run_timer(timer_seconds: int, label_fn, prepare_text: str):
        """Wall-clock countdown. Returns when timer expires or skip button is pressed.
        label_fn(secs) -> str  builds the timer_text value for a given remaining seconds."""
        skip_event = asyncio.Event()

        async def skip(e):
            skip_event.set()

        page.add(ft.Button("⏭ Pomiń", on_click=skip, width=4000, height=50))
        page.update()

        end_time = time.time() + timer_seconds
        beep_played = False
        wake_lock = await _acquire_wake_lock()
        try:
            while not skip_event.is_set():
                remaining = end_time - time.time()
                if remaining <= 0:
                    break

                display_secs = math.ceil(remaining)

                if display_secs <= 3 and not beep_played:
                    await play_beep()
                    beep_played = True

                timer_text.value = label_fn(display_secs)
                if display_secs < 4:
                    timer_text.value += prepare_text
                page.update()

                try:
                    await asyncio.wait_for(skip_event.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
        finally:
            _release_wake_lock(wake_lock)

        hf = ft.HapticFeedback()
        try:
            await asyncio.wait_for(hf.heavy_impact(), timeout=1)
        except (asyncio.TimeoutError, Exception):
            pass

    async def start_rest(action=None, is_start=False, next_set=None):
        page.controls.clear()
        page.bgcolor = "#004422"

        ex = sets[set_index]
        page.add(timer_text)
        add_set_header(page, ex=next_set or ex, action=action, is_next=next_set is not None)
        add_set_metadata(page, ex=next_set or ex, sessions=sessions, last_session=last_session)

        timer_seconds = ex.get_rest_seconds() if not is_start else 10
        label = (lambda s: f"\nStartujemy za: \n⏱ {s}s\n") if is_start else (lambda s: f"\nRest: \n⏱ {s}s\n")
        await _run_timer(timer_seconds, label, "Przygotuj się!\n")

    async def start_rest_interval(action):
        page.controls.clear()
        page.bgcolor = "#996600"

        ex = sets[set_index]
        page.add(timer_text)
        add_set_header(page, ex=ex, action=action, is_next=False)
        add_set_metadata(page, ex=ex, sessions=sessions, last_session=last_session)

        await _run_timer(
            ex.exercise.interval_config.rest_time,
            lambda s: f"\nRest interwałowy: \n⏱ {s}s\n",
            "Przygotuj się!\n",
        )

    async def start_working_interval(action):
        page.controls.clear()
        page.bgcolor = "#550000"

        ex = sets[set_index]
        page.add(timer_text)
        add_set_header(page, ex=ex, action=action, is_next=False)
        add_set_metadata(page, ex=ex, sessions=sessions, last_session=last_session)

        await _run_timer(
            ex.exercise.interval_config.working_time,
            lambda s: f"\nŁaduj: ⏱ {s}s\n",
            "Już prawie...\n",
        )

    async def show_set_input(saved, exited, action):
        ex = sets[set_index]
        timer_text.value = f"\nŁaduj i podsumuj!"

        # Pre-fill with the most recent set of this exercise already done in the current session
        prev_set = None
        for s in reversed(session.sets):
            if s.get_id() == ex.get_id():
                prev_set = s
                break
        weight.value = prev_set.weight if prev_set else ""
        reps.value = str(prev_set.reps) if prev_set else ""
        notes.value = prev_set.notes if prev_set else ""

        page.controls.clear()
        page.bgcolor = "#222222"
        page.add(timer_text)
        add_set_header(page, ex=ex, action=action, is_next=False)

        page.add(
            weight,
            reps,
            notes,
            ft.Column([
                ft.Button("Zapisz serię", on_click=save_set, data=saved, width=4000, height=50),
                ft.Button("Zakończ trening (bez ostatniej serii)", on_click=end_session, data=[saved, exited], width=4000, height=50),
            ]),
        )
        add_set_metadata(page, ex=ex, sessions=sessions, last_session=last_session)
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
