import flet as ft
from fireboar.storage import load_trainings, save_trainings, get_training, save_training
from fireboar.utils import show_dialog
from fireboar.training import Exercise, Training


async def training_edit_ui(training_id: str, page: ft.Page, home_function):
    page.controls.clear()
    training = await get_training(training_id)

    async def add_exercise(e):
        training.add_exercise()
        ex_id = training.exercises[-1].id
        ex_cards[ex_id] = create_card(training.exercises[-1])
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

    async def save_training_button(e):
        await save_training(training)
        await show_dialog(page, "Ćwiczenia ogarnięte", "Teraz tylko ładować.", "Ok")
        await home_function()

    def create_card(ex: Exercise):
        header = ft.Text(ex.name or 'Kliknij by rozwinąć')
        return ft.Card(
            ft.Container(
                    padding=10,
                    expand=True,
                    content=ft.ExpansionTile(
                        title=ft.Row(controls=[
                            header,
                        ]),
                        controls=ft.Column(
                            controls=[
                            ft.Row([
                                ft.Button("Usuń", on_click=remove_exercise, data=ex.id, height=50),
                                ft.Button("Wyżej", on_click=move_exercise_up, data=ex.id, height=50),
                                ft.Button("Niżej", on_click=move_exercise_down, data=ex.id, height=50),
                            ]),
                            ft.TextField(
                                label="Nazwa",
                                expand=True,
                                value=ex.name,
                                on_change=lambda e, ex=ex, header=header: ex.set_name(e.control.value, header),
                            ),
                            ft.TextField(
                                label="Serie",
                                expand=True,
                                value=str(ex.sets),
                                on_change=lambda e, ex=ex: ex.set_sets(e.control.value),
                            ),
                            ft.TextField(
                                label="Propozycja obciążenia",
                                expand=True,
                                value=ex.suggested_weight,
                                on_change=lambda e, ex=ex: ex.set_weight(e.control.value),
                            ),
                            ft.TextField(
                                label="Propozycja powtórzeń",
                                expand=True,
                                value=ex.suggested_reps,
                                on_change=lambda e, ex=ex: ex.set_reps(e.control.value),
                            ),
                            ft.TextField(
                                label="Rest (sek)",
                                expand=True,
                                value=str(ex.rest_seconds),
                                on_change=lambda e, ex=ex: ex.set_rest(e.control.value),
                            ),
                            ft.TextField(
                                label="Identyfikator superserii (dodaj taki sam dla ćwiczeń naprzemiennych)",
                                expand=True,
                                value=str(ex.superset_id),
                                on_change=lambda e, ex=ex: ex.set_superset(e.control.value),
                            ),
                            ft.Text(""),
                        ]),
                        expanded=False, # Controls initial state
                        expanded_alignment=ft.Alignment.CENTER_LEFT,
                    )
                )
            )


    page.add(
        ft.Text("Edycja treningu:", size=22),
        ft.Text(f"{training.name}", size=22),
        ft.Button("➕ Dodaj ćwiczenie", on_click=add_exercise),
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
    name = ft.TextField(label="Nazwa treningu")

    async def save(e):
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

    page.controls.clear()
    page.add(
        ft.Text("Nowy trening", size=24),
        name,
        ft.Row([
            ft.Button("Zapisz", on_click=save),
            ft.TextButton("⬅ Wróć", on_click=home_function)
        ]),
    )
    page.update()
