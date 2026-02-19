import flet as ft
import asyncio


async def vibrate():
    hf = ft.HapticFeedback()
    await hf.vibrate()


async def show_dialog(page: ft.Page, title: str, content: str, action: str):
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(content),
        actions=[
            ft.TextButton(action, on_click=lambda e: page.pop_dialog()),
        ],
        open=True,
    ))
    await vibrate()
