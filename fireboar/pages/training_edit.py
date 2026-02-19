import flet as ft
from fireboar.storage import load_trainings, save_trainings
from fireboar.utils import show_dialog
from fireboar.training import Exercise, Training


async def training_edit_ui(training_id: str, page: ft.Page, home_function):
    page.controls.clear()
    trainings = await load_trainings()
    idx = 0
    for i, t in enumerate(trainings):
        if t.id == training_id:
            idx = i

    async def add_exercise(e):
        trainings[idx].add_exercise()
        await save_trainings(trainings)
        await training_edit_ui(training_id, page, home_function)

    async def remove_exercise(e):
        trainings[idx].remove_exercise(e.control.data)
        await save_trainings(trainings)
        await training_edit_ui(training_id, page, home_function)

    async def save_training(e):
        await save_trainings(trainings)
        await show_dialog(page, "Ćwiczenia ogarnięte", "Teraz tylko ładować.", "Ok")
        await home_function()

    page.add(
        ft.Text(f"Edycja treningu: {trainings[idx].name}", size=22),
        ft.Button("➕ Dodaj ćwiczenie", on_click=add_exercise),
    )

    ex_headers = {}
    for ex in trainings[idx].exercises:
        ex_headers[ex.id] = ft.Text(ex.name or 'Kliknij by rozwinąć')
        page.add(
            ft.Card(
                ft.Container(
                    padding=10,
                    expand=True,
                    content=ft.ExpansionTile(
                        title=ft.Row(controls=[
                            ex_headers[ex.id],
                            ft.Button("Usuń", on_click=remove_exercise, data=ex.id),
                        ]),
                        controls=ft.Column(
                            controls=[
                            ft.Text(""),
                            ft.TextField(
                                label="Nazwa",
                                expand=True,
                                value=ex.name,
                                on_change=lambda e, ex=ex: ex.set_name(e.control.value, ex_headers[ex.id]),
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
        )

    page.add(ft.Row([
        ft.Button("Zapisz", on_click=save_training),
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
