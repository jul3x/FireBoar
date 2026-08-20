import math
import flet as ft
import flet_charts as fch
from fireboar.training import Exercise, Session, SessionSet
from fireboar.utils import normalize_string


SURFACE = "#222222"
GRID_COLOR = "#333333"
LABEL_COLOR = "#aaaaaa"

# Categorical palette (dark steps), validated against the #222222 surface:
# lightness band, chroma floor, adjacent-pair CVD separation, normal-vision
# separation and 3:1 contrast all pass. Slots are handed out in this fixed
# order and never recycled for a different meaning - the Nth set always keeps
# its color. Past 8 sets the hue repeats but the line is drawn dashed, so the
# pair stays distinguishable.
SERIES_COLORS = [
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
    "#e66767",  # red
]

CHART_HEIGHT = 240
COMPACT_CHART_HEIGHT = 180
MIN_CHART_WIDTH = 320
PX_PER_SESSION = 46
COMPACT_PX_PER_SESSION = 38
AXIS_PADDING = 60
# page padding + card margin + card container padding around the chart
CARD_INSET = 64


def _series_color(slot: int) -> str:
    return SERIES_COLORS[slot % len(SERIES_COLORS)]


def _series_dash(slot: int) -> list[int] | None:
    return [6, 4] if slot >= len(SERIES_COLORS) else None


def _nice_step(rough: float) -> float:
    if rough <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(rough))
    for mult in (1, 2, 2.5, 5):
        if rough <= magnitude * mult:
            return magnitude * mult
    return magnitude * 10


def _format_number(value: float) -> str:
    return f"{value:g}"


def _collect_series(exercise: Exercise, sessions: list[Session]) -> dict[int, list[tuple[int, float, SessionSet, str]]]:
    """Weight per set index across sessions: {set_index: [(session_no, weight, set, date)]}."""
    series: dict[int, list[tuple[int, float, SessionSet, str]]] = {}
    for session_no, session in enumerate(sessions, start=1):
        date = session.get_date()
        for s in session.sets:
            if s.get_id() != exercise.id:
                continue
            # "brak" / empty (bodyweight) counts as 0 kg - the set still gets plotted
            weight = normalize_string(s.weight)
            series.setdefault(s.set_index, []).append((session_no, weight, s, date))
    return series


def _tooltip_text(session_no: int, set_index: int, s: SessionSet, date: str) -> str:
    weight = str(s.weight).strip() or "brak"
    reps = str(s.reps).strip() or "?"
    notes = str(s.notes).strip() or "brak uwag"
    return (
        f"Sesja {session_no} · Seria {set_index}\n"
        f"Data: {date}\n"
        f"Obciążenie: {weight}\n"
        f"Powtórzenia: {reps}\n"
        f"Uwagi: {notes}"
    )


def _axis_label(text: str) -> fch.ChartAxisLabel:
    return fch.ChartAxisLabel(label=ft.Text(text, size=11, color=LABEL_COLOR))


def _legend(set_indexes: list[int]) -> ft.Control:
    items = []
    for slot, set_index in enumerate(set_indexes):
        items.append(
            ft.Row(
                [
                    ft.Container(width=10, height=10, border_radius=5, bgcolor=_series_color(slot)),
                    ft.Text(f"Seria {set_index}", size=12, color=LABEL_COLOR),
                ],
                spacing=5,
                tight=True,
            )
        )
    return ft.Row(
        items,
        wrap=True,
        spacing=14,
        run_spacing=4,
        alignment=ft.MainAxisAlignment.CENTER,
        run_alignment=ft.MainAxisAlignment.CENTER,
    )


def _fits(chart_width: float, page: ft.Page | None) -> bool:
    """Whether the chart at its natural width still fits inside the card it lives in."""
    page_width = getattr(page, "width", None)
    if not page_width:
        # Width not reported yet: only a chart at its minimum width is safe to assume fits.
        return chart_width <= MIN_CHART_WIDTH
    return chart_width <= page_width - CARD_INSET


def has_progress_data(exercise: Exercise, sessions: list[Session]) -> bool:
    """Whether there is anything to plot for this exercise."""
    return bool(_collect_series(exercise, sessions))


def build_progress_chart(
    exercise: Exercise,
    sessions: list[Session],
    compact: bool = False,
    page: ft.Page | None = None,
) -> ft.Control:
    """Weight progress of a single exercise: X = session number, Y = weight, one line per set.

    `compact` trims the height, the per-session width and the axis titles - used mid-workout,
    where the chart shares the screen with the timer and the set details.
    `page` is needed to tell whether the history fits on screen or has to scroll.
    """
    series = _collect_series(exercise, sessions)
    if not series:
        return ft.Text(
            "📉 Brak zapisanych obciążeń do wykresu",
            size=14,
            color=LABEL_COLOR,
            margin=10,
            width=4000,
            text_align="center",
        )

    sessions_count = len(sessions)
    weights = [weight for points in series.values() for _, weight, _, _ in points]
    min_weight, max_weight = min(weights), max(weights)

    # a flat history (or a single session) still needs a sane band around the value;
    # an all-bodyweight history is flat at 0 and gets a plain 0-1 kg band
    spread = (max_weight - min_weight) or max_weight * 0.2 or 3
    step = _nice_step(spread / 3)
    min_y = math.floor(min_weight / step - 0.5) * step
    max_y = math.ceil(max_weight / step + 0.5) * step
    if min_y < 0:
        # weights are never negative, but a 0 kg dot still needs room under it
        min_y = -step / 2

    set_indexes = sorted(series.keys())
    data_series = []
    for slot, set_index in enumerate(set_indexes):
        color = _series_color(slot)
        data_series.append(
            fch.LineChartData(
                color=color,
                stroke_width=2,
                dash_pattern=_series_dash(slot),
                rounded_stroke_cap=True,
                rounded_stroke_join=True,
                # 2px surface ring keeps overlapping dots readable
                point=fch.ChartCirclePoint(color=color, radius=4.5, stroke_color=SURFACE, stroke_width=2),
                points=[
                    fch.LineChartDataPoint(
                        x=session_no,
                        y=weight,
                        tooltip=fch.LineChartDataPointTooltip(
                            text=_tooltip_text(session_no, set_index, s, date),
                            text_style=ft.TextStyle(color="#ffffff", size=12),
                            text_align=ft.TextAlign.LEFT,
                        ),
                    )
                    for session_no, weight, s, date in series[set_index]
                ],
            )
        )

    y_labels = []
    value = max(min_y, 0.0)  # the half-step below zero is breathing room, not a labelled value
    while value <= max_y + step / 2:
        y_labels.append(fch.ChartAxisLabel(value=value, label=ft.Text(_format_number(value), size=11, color=LABEL_COLOR)))
        value += step

    x_spacing = max(1, math.ceil(sessions_count / 12))
    x_labels = [
        fch.ChartAxisLabel(value=session_no, label=ft.Text(str(session_no), size=11, color=LABEL_COLOR))
        for session_no in range(1, sessions_count + 1)
        if (sessions_count - session_no) % x_spacing == 0
    ]

    chart = fch.LineChart(
        data_series=data_series,
        min_x=0.5,
        max_x=sessions_count + 0.5,
        min_y=min_y,
        max_y=max_y,
        interactive=True,
        horizontal_grid_lines=fch.ChartGridLines(interval=step, color=GRID_COLOR, width=1),
        left_axis=fch.ChartAxis(
            labels=y_labels,
            label_size=42,
            title=None if compact else ft.Text("kg", size=11, color=LABEL_COLOR),
            title_size=0 if compact else 18,
        ),
        bottom_axis=fch.ChartAxis(
            labels=x_labels,
            label_size=24,
            title=None if compact else ft.Text("nr sesji", size=11, color=LABEL_COLOR),
            title_size=0 if compact else 18,
        ),
        top_axis=fch.ChartAxis(show_labels=False),
        right_axis=fch.ChartAxis(show_labels=False),
        tooltip=fch.LineChartTooltip(
            bgcolor="#EE111111",
            border_radius=8,
            border_side=ft.BorderSide(1, "#555555"),
            max_width=230,
            fit_inside_horizontally=True,
            fit_inside_vertically=True,
        ),
        expand=True,
    )

    px_per_session = COMPACT_PX_PER_SESSION if compact else PX_PER_SESSION
    chart_width = max(MIN_CHART_WIDTH, AXIS_PADDING + px_per_session * sessions_count)
    height = COMPACT_CHART_HEIGHT if compact else CHART_HEIGHT

    if _fits(chart_width, page):
        # Fills the card, so the plot sits centered between its edges. A scrollable Row
        # cannot do this: flet wraps it in a horizontal scroll view, which leaves the Row
        # unbounded and makes `alignment` a no-op - the chart would hug the left edge.
        chart_body = ft.Row([ft.Container(height=height, content=chart, expand=True)])
    else:
        # Long history: keep the per-session spacing readable and scroll instead.
        chart_body = ft.Row(
            [ft.Container(width=chart_width, height=height, content=chart)],
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,
        )

    controls = [chart_body]
    if len(set_indexes) > 1:
        controls.append(_legend(set_indexes))

    return ft.Column(controls, spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
