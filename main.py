import os
import flet as ft
import asyncio
import json
from fireboar.storage import (
    load_trainings,
    load_sessions,
    get_training,
    delete_training_from_list,
)
from fireboar.utils import show_dialog
from fireboar.pages.training_edit import training_edit_ui, training_add_ui
from fireboar.pages.home import home_ui
from fireboar.pages.sessions import sessions_show_ui
from fireboar.pages.start import start_ui

# TODO: Sounds of beeping for sessions
# TODO: Rewrite this for better DB structure
# TODO: Add fingerboarding / cluster pullups intervals type training
# TODO: Handle Core training exercises
# TODO: Mark sessions with PB and historical PB
# TODO: Propose existing superseries
# TODO: Mark superseries the same color
# TODO: Add info during rest: Next exercise
# TODO: Import from XLSX
# TODO: Export to XLSX

async def main(page: ft.Page):
    page.title = "FireBoar"
    page.scroll = "auto"

    os.makedirs("uploads", exist_ok=True)
    async def show_home():
        await home_ui(page, show_add_training, edit_training, delete_training, start_training, show_sessions)

    async def show_sessions(e):
        sessions = await load_sessions()
        training_data = e.control.data
        sessions_for_t = training_data.get_sessions(sessions)
        await sessions_show_ui(training_data, sessions_for_t, page, home_function=show_home)

    async def show_add_training(e):
        await training_add_ui(page, home_function=show_home)

    async def edit_training(event):
        await training_edit_ui(training_id=event.control.data, page=page, home_function=show_home)

    async def delete_training(event):
        await delete_training_from_list(event.control.data)
        await show_dialog(page, "Trening usunięty", "W sumie smutno.", "Ok")
        await show_home()

    async def start_training(event):
        training = await get_training(event.control.data)
        sessions = await load_sessions()
        await start_ui(training, sessions, page, home_function=show_home)

    await show_home()


ft.run(main, upload_dir="uploads")

