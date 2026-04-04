import flet as ft
import re
from typing import Callable
import asyncio


class StorageError(Exception):
    pass


async def show_fatal_error(page: ft.Page, message: str):
    page.controls.clear()
    page.add(
        ft.Text("Błąd krytyczny!", size=28, color=ft.Colors.RED, text_align="center", width=4000, margin=20),
        ft.Text(message, size=16, text_align="center", width=4000),
        ft.Text("Uruchom aplikację ponownie.", size=18, weight="bold", text_align="center", width=4000, margin=20),
    )
    page.update()


def guard(page: ft.Page, fn):
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except StorageError as e:
            await show_fatal_error(page, str(e))
    return wrapper


async def vibrate():
    hf = ft.HapticFeedback()
    try:
        await asyncio.wait_for(hf.vibrate(), timeout=1)
    except (asyncio.TimeoutError, Exception):
        pass


async def show_dialog(page: ft.Page, title: str, content: str, action: str, action_cb: Callable | None = None):
    async def callback(e):
        if action_cb:
            await action_cb()
        page.pop_dialog()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(content),
        actions=[
            ft.TextButton(
                action,
                on_click=callback,
            )
        ],
        open=True,
    ))
    await vibrate()


def normalize_string(value: str | int | float) -> float:
    if isinstance(value, int) or isinstance(value, float):
        return float(value)

    cleaned = re.sub(r"[^0-9.,]", "", value)
    cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0

