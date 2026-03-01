import flet as ft
from fireboar.storage import load_trainings, save_trainings, get_training, save_training
from fireboar.utils import show_dialog, guard
from fireboar.training import Exercise, Training, ExerciseType, IntervalConfig


def string_to_hex_color(s: str) -> str:
    if not s:
        return "#000000"  # fallback for empty string

    first_char = s[0]
    char_code = ord(first_char) + len(s)

    # Map A-Z to 0-360 degrees hue
    hue = ((char_code - 65) % 26) * (360 / 7)

    # Hash the rest of the string for small tweaks
    hash_val = 0
    for c in s[1:]:
        hash_val = (hash_val * 31 + ord(c)) % 1000

    sat = 70 + (hash_val % 20)          # 70-89%
    light = 50 + (hash_val % 10)        # 50-59%

    final_hue = (hue + 360) % 360

    # Convert HSL to RGB
    r, g, b = hsl_to_rgb(final_hue, sat, light)
    return f"#{r:02x}{g:02x}{b:02x}"


def hsl_to_rgb(h, s, l):
    s /= 100
    l /= 100

    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if h < 60:
        r1, g1, b1 = c, x, 0
    elif h < 120:
        r1, g1, b1 = x, c, 0
    elif h < 180:
        r1, g1, b1 = 0, c, x
    elif h < 240:
        r1, g1, b1 = 0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x

    r = int((r1 + m) * 255)
    g = int((g1 + m) * 255)
    b = int((b1 + m) * 255)

    return r, g, b


async def training_edit_ui(training_id: str, page: ft.Page, home_function):
    page.controls.clear()
    training = await get_training(training_id)

    async def add_exercise(e):
        training.add_exercise()
        ex_id = training.exercises[-1].id
        ex_cards[ex_id] = create_card(training.exercises[-1], new=True)
        cards_container.controls.append(ex_cards[ex_id])
        page.update()

    async def move_exercise_up(e):
        training.move_exercise_up(e.control.data)
        cards_container.controls = []
        for ex in training.exercises:
            cards_container.controls.append(ex_cards[ex.id])
        page.update()

    async def move_exercise_down(e):
        training.move_exercise_down(e.control.data)
        cards_container.controls = []
        for ex in training.exercises:
            cards_container.controls.append(ex_cards[ex.id])
        page.update()

    async def remove_exercise(e):
        training.remove_exercise(e.control.data)
        cards_container.controls = [c for c in cards_container.controls if not c is ex_cards[e.control.data]]
        del ex_cards[e.control.data]
        page.update()

    def set_superset(ex: Exercise, superset: str):
        ex.set_superset(superset)
        ex_cards[ex.id].content.bgcolor = ft.Colors.with_opacity(0.1, string_to_hex_color(superset))

    def set_exercise_type(ex: Exercise, type: ExerciseType, interval_fields: list):
        ex.type = type
        for f in interval_fields:
            f.visible = ex.type == ExerciseType.INTERVAL

    async def _save_training_button(e):
        await save_training(training)
        await show_dialog(page, "Ćwiczenia ogarnięte", "Teraz tylko ładować.", "Ok")
        await home_function()
    save_training_button = guard(page, _save_training_button)

    def create_card(ex: Exercise, new: bool = False):
        header = ft.Text(ex.name or 'Kliknij by rozwinąć')

        interval_fields = [
            ft.TextField(
                label="Liczba interwałów w serii",
                expand=True,
                value=str(ex.interval_config.intervals),
                visible=ex.type == ExerciseType.INTERVAL,
                border_color="#555555",
                color="#ffffff",
                bgcolor="#111111",
                on_change=lambda e, ex=ex: ex.interval_config.set_intervals(e.control.value),
            ),
            ft.TextField(
                label="Czas trwania wysiłku w interwale",
                expand=True,
                value=str(ex.interval_config.working_time),
                visible=ex.type == ExerciseType.INTERVAL,
                border_color="#555555",
                color="#ffffff",
                bgcolor="#111111",
                on_change=lambda e, ex=ex: ex.interval_config.set_working_time(e.control.value),
            ),
            ft.TextField(
                label="Czas restu pomiędzy",
                expand=True,
                value=str(ex.interval_config.rest_time),
                visible=ex.type == ExerciseType.INTERVAL,
                border_color="#555555",
                color="#ffffff",
                bgcolor="#111111",
                on_change=lambda e, ex=ex: ex.interval_config.set_rest_time(e.control.value),
            ),
        ]

        return ft.Card(
            ft.Container(
                    padding=10,
                    expand=True,
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.1, string_to_hex_color(ex.superset_id)),
                    content=ft.ExpansionTile(
                        title=ft.Row(controls=[
                            header,
                        ]),
                        controls=ft.Column(
                            controls=[
                            ft.Container(),
                            ft.Row([
                                ft.Button("Usuń", on_click=remove_exercise, data=ex.id, height=50),
                                ft.Button("Wyżej", on_click=move_exercise_up, data=ex.id, height=50),
                                ft.Button("Niżej", on_click=move_exercise_down, data=ex.id, height=50),
                            ]),
                            ft.RadioGroup(
                                expand=True,
                                value=ex.type,
                                content=ft.Row([
                                    ft.Radio(value=ExerciseType.NORMAL, label="normalnie"),
                                    ft.Radio(value=ExerciseType.INTERVAL, label="interwały"),
                                ]),
                                on_change=lambda e, ex=ex, fields=interval_fields: set_exercise_type(ex, e.control.value, fields),
                            ),
                            ft.Container(),
                            ft.TextField(
                                label="Nazwa",
                                expand=True,
                                value=ex.name,
                                border_color="#555555",
                                color="#ffffff",
                                bgcolor="#111111",
                                on_change=lambda e, ex=ex, header=header: ex.set_name(e.control.value, header),
                            ),
                            ft.TextField(
                                label="Serie",
                                expand=True,
                                value=str(ex.sets),
                                border_color="#555555",
                                color="#ffffff",
                                bgcolor="#111111",
                                on_change=lambda e, ex=ex: ex.set_sets(e.control.value),
                            ),
                            ft.TextField(
                                label="Propozycja obciążenia",
                                expand=True,
                                value=ex.suggested_weight,
                                border_color="#555555",
                                color="#ffffff",
                                bgcolor="#111111",
                                on_change=lambda e, ex=ex: ex.set_weight(e.control.value),
                            ),
                            ft.TextField(
                                label="Propozycja powtórzeń",
                                expand=True,
                                value=ex.suggested_reps,
                                border_color="#555555",
                                color="#ffffff",
                                bgcolor="#111111",
                                on_change=lambda e, ex=ex: ex.set_reps(e.control.value),
                            ),
                            ft.TextField(
                                label="Rest pomiędzy seriami (sek)",
                                expand=True,
                                value=str(ex.rest_seconds),
                                border_color="#555555",
                                color="#ffffff",
                                bgcolor="#111111",
                                on_change=lambda e, ex=ex: ex.set_rest(e.control.value),
                            ),
                            ft.TextField(
                                label="Identyfikator superserii (dodaj taki sam dla ćwiczeń naprzemiennych)",
                                expand=True,
                                value=str(ex.superset_id),
                                border_color="#555555",
                                color="#ffffff",
                                bgcolor="#111111",
                                on_change=lambda e, ex=ex: set_superset(ex, e.control.value),
                            ),
                            *interval_fields,
                            ft.Text(""),
                        ]),
                        expanded=new,
                        expanded_alignment=ft.Alignment.CENTER_LEFT,
                    )
                )
            )


    page.add(
        ft.Text("Edycja treningu:", size=24, margin=10, text_align="center", width=4000),
        ft.Text(f"{training.name}", size=24, text_align="center", width=4000),
        ft.Text(""),
        ft.Button("➕ Dodaj ćwiczenie", on_click=add_exercise, width=4000, height=50),
    )

    ex_headers = {}
    ex_cards = {}
    cards_container = ft.Column([])
    for ex in training.exercises:
        ex_cards[ex.id] = create_card(ex)
        cards_container.controls.append(ex_cards[ex.id])

    page.add(cards_container)
    page.add(ft.Row([
        ft.Button("Zapisz", on_click=save_training_button),
        ft.TextButton("⬅ Wróć", on_click=home_function)
    ]))
    page.update()


async def training_add_ui(page: ft.Page, home_function):
    name = ft.TextField(label="Nazwa treningu", border_color="#888888", color="#ffffff", bgcolor="#444444", expand=True)

    async def _save(e):
        trainings = await load_trainings()
        trainings.append(Training(name=name.value))
        await save_trainings(trainings)
        await show_dialog(
            page,
            "Trening dodany",
            "Dodaj ćwiczenia drapichruście.",
            "Będę łoił",
        )
        await home_function()
    save = guard(page, _save)

    page.controls.clear()
    page.add(
        ft.Text("Nowy trening", size=24, width=4000, text_align="center", margin=10),
        name,
        ft.Row([
            ft.Button("Zapisz", on_click=save),
            ft.TextButton("⬅ Wróć", on_click=home_function)
        ]),
    )
    page.update()
