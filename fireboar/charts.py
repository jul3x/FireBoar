import math
import re
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

MIN_CHART_WIDTH = 320
PX_PER_SESSION = 46
COMPACT_PX_PER_SESSION = 38
AXIS_PADDING = 60
# page padding + card margin + card container padding around the chart
CARD_INSET = 64

# fl_chart paints the tooltip on the chart's own canvas, so anything taller than the
# plotting area gets cut off - there is no z-index to escape with. The height is therefore
# derived from how tall the tallest tooltip of this exercise can get.
TOOLTIP_TEXT_SIZE = 11
TOOLTIP_LINE_HEIGHT = 15
# tooltip padding (2x6) + its margin above the point + a little slack
TOOLTIP_CHROME = 12 + 8 + 14
NOTE_LIMIT = 48  # notes are trimmed so one set never blows the tooltip up
NOTE_WRAP_CHARS = 26  # above this a note wraps onto a second line at max_width
MIN_PLOT_HEIGHT = 200
MAX_PLOT_HEIGHT = 320
COMPACT_MIN_PLOT_HEIGHT = 150
COMPACT_MAX_PLOT_HEIGHT = 260
X_LABEL_SIZE = 24
X_TITLE_SIZE = 18


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


def _format_weight(raw: str | int | float) -> str:
    text = str(raw).strip()
    if not text:
        return "brak"
    # only a bare number gets the unit appended - "brak" or "guma" must stay as typed
    return f"{text} kg" if re.fullmatch(r"\d+([.,]\d+)?", text) else text


def _note_text(s: SessionSet) -> str:
    note = " ".join(str(s.notes).split())
    if len(note) > NOTE_LIMIT:
        note = note[:NOTE_LIMIT - 1].rstrip() + "…"
    return note


def _point_lines(s: SessionSet) -> int:
    """How many text lines this set takes inside the tooltip."""
    note = _note_text(s)
    if not note:
        return 1
    return 2 + (len(note) > NOTE_WRAP_CHARS)


def _point_tooltip(
    session_no: int,
    set_index: int,
    s: SessionSet,
    date: str,
    with_header: bool,
) -> fch.LineChartDataPointTooltip:
    """One tooltip entry. All sets of a session are shown in a single tooltip box, so the
    session header (and the date) belongs to exactly one of them - see `_header_points`.

    Plain text only: `text_spans` would let the series color into the box, but flet_charts
    hands the raw list straight to `parseTextSpans(List<Control>)`, which throws on the
    cast at runtime and kills the whole tooltip. Identity comes from the "Seria N" prefix
    and the legend instead."""
    reps = str(s.reps).strip() or "?"
    lines = []
    if with_header:
        lines.append(f"Sesja {session_no} · {date}")
    lines.append(f"Seria {set_index}: {_format_weight(s.weight)} × {reps}")
    note = _note_text(s)
    if note:
        lines.append(note)
    return fch.LineChartDataPointTooltip(
        text="\n".join(lines),
        text_style=ft.TextStyle(color="#ffffff", size=TOOLTIP_TEXT_SIZE),
        text_align=ft.TextAlign.LEFT,
    )


def _header_points(series: dict[int, list[tuple[int, float, SessionSet, str]]]) -> dict[int, int]:
    """{session_no: set_index that carries the session header}.

    fl_chart hands the touched spots to the tooltip sorted by value, descending, and that
    sort is stable for the handful of sets we ever have - so the heaviest set (lowest set
    index on a tie) is the first line of the box and the right place for the header."""
    best: dict[int, tuple[float, int]] = {}
    for set_index, points in series.items():
        for session_no, weight, _, _ in points:
            current = best.get(session_no)
            if current is None or weight > current[0] or (weight == current[0] and set_index < current[1]):
                best[session_no] = (weight, set_index)
    return {session_no: set_index for session_no, (_, set_index) in best.items()}


def _tooltip_height(series: dict[int, list[tuple[int, float, SessionSet, str]]]) -> float:
    """Height of the tallest tooltip this exercise can pop up."""
    lines: dict[int, int] = {}
    for points in series.values():
        for session_no, _, s, _ in points:
            lines[session_no] = lines.get(session_no, 0) + _point_lines(s)
    tallest = max(lines.values(), default=1) + 1  # + the session header line
    return tallest * TOOLTIP_LINE_HEIGHT + TOOLTIP_CHROME


def _axis_values(min_v: float, max_v: float, interval: float) -> list[float]:
    """The values fl_chart will walk the axis with, reproduced exactly.

    Labels are matched to axis positions by `==` on the Dart side, so a value computed any
    other way (`index * interval`, say) can miss by one ULP and silently not render.
    Mirrors fl_chart's `Utils.getBestInitialIntervalValue` + `iterateThroughAxis`
    (baseline 0), down to the order of the arithmetic."""
    diff = -min_v
    mod = math.fmod(diff, interval)
    if mod < 0:
        mod += interval  # Dart's % on doubles is always non-negative
    initial = min_v if (abs(max_v - min_v) <= mod or mod == 0) else min_v + mod

    values = []
    seek = initial
    epsilon = interval / 100000
    while seek <= max_v + epsilon:
        values.append(seek)
        seek += interval
    return values


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
    # Half a step of air below the lowest and above the highest label: a label sitting
    # exactly on min_y/max_y is drawn centered on the edge of the plotting area and comes
    # out sliced in half. This also leaves room under a 0 kg dot.
    min_y = (math.floor(min_weight / step) - 0.5) * step
    max_y = (math.ceil(max_weight / step) + 0.5) * step

    header_points = _header_points(series)
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
                        tooltip=_point_tooltip(
                            session_no,
                            set_index,
                            s,
                            date,
                            with_header=header_points.get(session_no) == set_index,
                        ),
                    )
                    for session_no, weight, s, date in series[set_index]
                ],
            )
        )

    y_labels = [
        fch.ChartAxisLabel(value=value, label=ft.Text(_format_number(value), size=11, color=LABEL_COLOR))
        for value in _axis_values(min_y, max_y, step)
        if value >= 0  # the half-step below zero is breathing room, not a labelled value
    ]

    x_spacing = max(1, math.ceil(sessions_count / 12))
    min_x, max_x = 0.5, sessions_count + 0.5
    x_labels = [
        fch.ChartAxisLabel(value=value, label=ft.Text(_format_number(value), size=11, color=LABEL_COLOR))
        for value in _axis_values(min_x, max_x, x_spacing)
        if 1 <= value <= sessions_count
    ]

    chart = fch.LineChart(
        data_series=data_series,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        interactive=True,
        horizontal_grid_lines=fch.ChartGridLines(interval=step, color=GRID_COLOR, width=1),
        left_axis=fch.ChartAxis(
            labels=y_labels,
            # without an explicit spacing fl_chart picks its own interval from the pixel
            # height, and labels whose value it never lands on are simply not drawn
            label_spacing=step,
            label_size=42,
            title=None if compact else ft.Text("kg", size=11, color=LABEL_COLOR),
            title_size=0 if compact else X_TITLE_SIZE,
        ),
        bottom_axis=fch.ChartAxis(
            labels=x_labels,
            label_spacing=x_spacing,
            label_size=X_LABEL_SIZE,
            title=None if compact else ft.Text("nr sesji", size=11, color=LABEL_COLOR),
            title_size=0 if compact else X_TITLE_SIZE,
        ),
        top_axis=fch.ChartAxis(show_labels=False),
        right_axis=fch.ChartAxis(show_labels=False),
        tooltip=fch.LineChartTooltip(
            bgcolor="#EE111111",
            border_radius=8,
            border_side=ft.BorderSide(1, "#555555"),
            max_width=250,
            padding=ft.Padding.symmetric(vertical=6, horizontal=10),
            margin=8,
            fit_inside_horizontally=True,
            fit_inside_vertically=True,
            # pin the box to the top of the plotting area instead of floating it above the
            # dot, so it is drawn in the same place every time and never half off-chart
            show_on_top_of_chart_box_area=True,
        ),
        expand=True,
    )

    px_per_session = COMPACT_PX_PER_SESSION if compact else PX_PER_SESSION
    chart_width = max(MIN_CHART_WIDTH, AXIS_PADDING + px_per_session * sessions_count)
    # the plotting area has to hold the tallest tooltip, or fl_chart clips it
    plot_height = min(
        COMPACT_MAX_PLOT_HEIGHT if compact else MAX_PLOT_HEIGHT,
        max(COMPACT_MIN_PLOT_HEIGHT if compact else MIN_PLOT_HEIGHT, _tooltip_height(series)),
    )
    height = plot_height + X_LABEL_SIZE + (0 if compact else X_TITLE_SIZE)

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
