import flet as ft
import re
from typing import Callable
import asyncio


async def vibrate():
    hf = ft.HapticFeedback()
    await hf.vibrate()


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

