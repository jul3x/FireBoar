import os
import flet as ft
import asyncio
import json
from fireboar.storage import (
    load_trainings,
    load_sessions,
    get_training,
    delete_training_from_list,
    archive_training_instance,
    dearchive_training_instance,
)
from fireboar.utils import show_dialog
from fireboar.pages.training_edit import training_edit_ui, training_add_ui
from fireboar.pages.home import UI, home_ui
from fireboar.pages.sessions import sessions_show_ui, pb_show_ui
from fireboar.pages.start import start_entry_ui


async def main(page: ft.Page):
    page.title = "FireBoar"
    page.scroll = "auto"

    os.makedirs("uploads", exist_ok=True)

    async def show_sessions(e):
        sessions = await load_sessions()
        training_data = e.control.data
        sessions_for_t = training_data.get_sessions(sessions)
        await sessions_show_ui(training_data, sessions_for_t, page, home_function=show_home)

    async def show_pb(e):
        sessions = await load_sessions()
        training_data = e.control.data
        sessions_for_t = training_data.get_sessions(sessions)
        await pb_show_ui(training_data, sessions_for_t, page, home_function=show_home)

    async def show_add_training(e):
        await training_add_ui(page, home_function=show_home)

    async def edit_training(event):
        await training_edit_ui(training_id=event.control.data, page=page, home_function=show_home)

    async def delete_training(event):
        async def delete_training_confirmed():
            await delete_training_from_list(event.control.data)
            await show_home()
        await show_dialog(
            page,
            "Trening do kosza?",
            "Kończysz karierę, siostro w wierze?",
            "Boję się cierpienia",
            action_cb=delete_training_confirmed,
        )

    async def start_training(event):
        training = await get_training(event.control.data)
        sessions = await load_sessions()
        await start_entry_ui(training, sessions, page, home_function=show_home)

    async def archive_training(event):
        if event.control.data["dearchive"]:
            await dearchive_training_instance(event.control.data["id"])
            await show_dialog(page, "Trening przywrócony", "Wracasz do tatusia?", "Yes daddy")
        else:
            await archive_training_instance(event.control.data["id"])
            await show_dialog(page, "Trening zarchiwizowany", "Ładujesz coś nowego byku?", "Keep grinding")
        await show_home()

    async def show_home():
        ui = UI(
            show_home=show_home,
            add_training=show_add_training,
            edit_training=edit_training,
            delete_training=delete_training,
            start_training=start_training,
            show_sessions=show_sessions,
            show_pb=show_pb,
            archive_training=archive_training,
        )

        await home_ui(page, ui, show_archived=False)

    await show_home()


ft.run(main, assets_dir="assets", upload_dir="uploads")

