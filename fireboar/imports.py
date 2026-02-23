import flet as ft
import json
import re
from datetime import datetime
import asyncio
from openpyxl import load_workbook
from io import BytesIO
from fireboar.training import Training, Exercise, Session
from fireboar.storage import save_trainings, save_sessions, load_trainings, load_sessions
from fireboar.utils import show_dialog, normalize_string


async def import_json(e, page, json_file_picker):
    files = await json_file_picker.pick_files(
        allow_multiple=False,
        with_data=True
    )
    if not files:
        return

    file = files[0]
    if not file.bytes:
        await show_dialog(
            page,
            "Coś nie pykło",
            "Wrzuciłeś mi pusty plik?",
            "Oczy widzą, usta milczą",
        )
        return

    try:
        file_bytes = file.bytes.decode('utf-8')
        data = json.loads(file_bytes)
        trainings = [Training.from_json(t) for t in data["trainings"]]
        sessions = [Session.from_json(s) for s in data["sessions"]]
        await save_trainings(trainings)
        await save_sessions(sessions)
    except Exception as e:
        print(e)
        await show_dialog(
            page,
            "Taki cwany?",
            "Wrzuć mi coś normalnego, to było zepsute.",
            "Ok",
        )
        return

    await show_dialog(
        page,
        "Dane zaimportowane",
        "Poprzednie dane zostały wyczyszczone!",
        "Ok",
    )


async def export_json(e, json_file_picker):
    trainings = [t.to_json() for t in await load_trainings()]
    sessions = [s.to_json() for s in await load_sessions()]
    await json_file_picker.save_file(
        dialog_title="Zapisz treningi",
        file_name="fireboar_trainings.json",
        src_bytes=json.dumps({"trainings": trainings, "sessions": sessions}).encode("utf-8"),
    )


async def import_kate(e, page, file_picker, home_function):
    files = await file_picker.pick_files(
        allow_multiple=False,
        with_data=True
    )
    if not files:
        return

    file = files[0]
    if not file.bytes:
        await show_dialog(
            page,
            "Coś nie pykło",
            "Wrzuciłeś mi pusty plik?",
            "Oczy widzą, usta milczą",
        )
        return

    try:
        file_memory = BytesIO(file.bytes)
        wb = load_workbook(file_memory)
    except Exception as e:
        print(e)
        await show_dialog(
            page,
            "Taki cwany?",
            "Wrzuć mi coś normalnego, to było zepsute.",
            "Ok",
        )
        return

    exit_event = asyncio.Event()
    sheet_picker = ft.RadioGroup(
        expand=True,
        content=ft.Column([
            ft.Radio(value=sheet_name, label=sheet_name)
            for sheet_name in wb.sheetnames
        ]),
        on_change=lambda e: None,
    )
    page.controls.clear()
    page.add(ft.Text("Plik załadowany.", size=24, weight="bold", width=4000, text_align="center"))
    page.add(ft.Text("Który trening chcesz zaimportować?", size=20, width=4000, text_align="center"))
    page.add(sheet_picker)

    async def continue_import():
        training = await process_kate_sheet(page, wb, sheet_picker.value)
        exit_event.set()

    async def exit():
        exit_event.set()

    page.add(
        ft.Row([
            ft.Button("Kontynuuj", on_click=continue_import),
            ft.TextButton("⬅ Wróć", on_click=exit)
        ]),
    )

    await exit_event.wait()


async def process_kate_sheet(page, wb, sheet_name: str | None) -> Training:
    if sheet_name not in wb.sheetnames:
        await show_dialog(
            page,
            "Zły wybór",
            "Spróbuj ponownie byczq!",
            "Ok",
        )
        return

    sheet = wb[sheet_name]
    rows = list(sheet.iter_rows())
    training = Training(name=sheet_name)
    for idx, row in enumerate(rows):
        if not row[0] or not row[0].value:
            continue

        if "TRENING" == str(row[0].value).strip().upper():
            try:
                sets = str(rows[idx + 1][1].value or 1)
                sets = int(float(normalize_string(sets.split("L")[0].split("P")[0] or "")))

                reps_to_parse = rows[idx + 1][2].value
                # Weird but valid
                if isinstance(reps_to_parse, datetime):
                    suggested_reps = f"{reps_to_parse.day} - {reps_to_parse.month}"
                else:
                    suggested_reps = str(reps_to_parse or "")
                suggested_weight = str(rows[idx + 1][3].value or "")

                header_idx = idx - 1
                while header_idx >= 0 and idx - header_idx < 7 and not rows[header_idx][0].value:
                    header_idx -= 1

                superset = str(rows[header_idx][0].value or "")
                superset = re.sub(r"[0-9]", "", superset)
                rest = get_rest(rows[header_idx][0])
                names = rows[header_idx][1].value.split('\n')
                parsed_names = []
                if "core" in superset.lower().strip():
                    for name in names:
                        for n in name.split(','):
                            n = str(n.split('http')[0])
                            parsed_names.append(n.strip().strip(':'))
                else:
                    for name in names:
                        name = str(name.split('http')[0])
                        parsed_names.append(name.strip().strip(':'))

                for name in parsed_names:
                    exercise = Exercise(
                        name=name,
                        sets=sets,
                        suggested_weight=suggested_weight,
                        suggested_reps=suggested_reps,
                        rest_seconds=rest,
                        superset_id=superset,
                    )
                    training.exercises.append(exercise)
            except:
                pass

    trainings = await load_trainings()
    trainings = [training] + trainings
    await save_trainings(trainings)
    await show_dialog(
        page,
        "Trening dodany",
        "Zobacz proszę, czy wszystko zostało dodane odpowiednio. Zwróć uwagę szczególnie na ćwiczenia CORE i ćwiczenia, które powinny być interwałowymi (podciąganie klastrowe / chwyto). Sprawdź czy resty są ustawione odpowiednio.",
        "Ładuj",
    )

def excel_rgb_to_tuple(argb):
    if argb is None:
        return None
    argb = argb[-6:]  # remove alpha
    return tuple(int(argb[i:i+2], 16) for i in (0, 2, 4))


def get_rest(cell) -> int:
    fill = cell.fill
    color = fill.fgColor.rgb

    rgb = excel_rgb_to_tuple(color)

    def color_distance_sq(c1, c2):
        return sum((a - b) ** 2 for a, b in zip(c1, c2))

    targets = {
        180: (74, 134, 232),
        60: (201, 218, 248),
        20: (217, 234, 211),
    }

    closest = min(
        targets.items(),
        key=lambda item: color_distance_sq(rgb, item[1])
    )

    return closest[0]
