"""
Non-blocking matplotlib charts.
chart_* functions accept an on_done(canvas_widget) callback.
The figure is built in a background thread; the widget is
delivered on the Kivy main thread via Clock.
"""
import threading
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from kivy.clock import Clock


# ── Colour scheme ─────────────────────────────────────────────────────────────
_C_PRESENT = "#4CAF50"
_C_ABSENT  = "#F44336"
_C_LATE    = "#FF9800"


def _style(fig, ax, dark: bool):
    bg   = "#1C1B1F" if dark else "#FAFAFA"
    fg   = "#E6E1E5" if dark else "#1C1B1F"
    grid = "#48454E" if dark else "#CAC4D0"
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.tick_params(colors=fg, labelsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(grid)
    ax.spines["bottom"].set_color(grid)
    ax.yaxis.grid(True, color=grid, linewidth=0.5, linestyle="--")
    ax.set_axisbelow(True)
    ax.title.set_color(fg)
    ax.xaxis.label.set_color(fg)
    ax.yaxis.label.set_color(fg)


def _make_canvas(fig):
    """Create a Kivy canvas widget from a matplotlib figure.
    MUST be called on the main thread — Kivy graphics are not thread-safe.
    """
    from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
    canvas = FigureCanvasKivyAgg(fig)
    canvas.size_hint = (1, 1)
    plt.close(fig)
    return canvas


def _run(build_fn, on_done):
    """Build the matplotlib figure in a background thread (pure data work),
    then create the Kivy canvas widget on the main thread via Clock."""
    def worker():
        try:
            fig = build_fn()          # returns a Figure, NOT a widget
            Clock.schedule_once(lambda dt: on_done(_make_canvas(fig)))
        except Exception as e:
            print(f"[chart] error: {e}")
    threading.Thread(target=worker, daemon=True).start()


# ── Public API ────────────────────────────────────────────────────────────────

def attendance_bar_chart(labels, present, absent, late,
                         title="Attendance Overview",
                         dark=False, on_done=None):
    def build():
        fig, ax = plt.subplots(figsize=(6, 3.2), dpi=90)
        x, w = range(len(labels)), 0.25
        ax.bar([i - w for i in x], present, w, color=_C_PRESENT,
               label="Present", zorder=3)
        ax.bar(list(x),            absent,  w, color=_C_ABSENT,
               label="Absent",  zorder=3)
        ax.bar([i + w for i in x], late,    w, color=_C_LATE,
               label="Late",    zorder=3)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=28, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.legend(fontsize=8, framealpha=0)
        _style(fig, ax, dark)
        fig.tight_layout()
        return fig   # return fig; canvas is made on main thread by _run

    if on_done:
        _run(build, on_done)
    else:
        return _make_canvas(build())


def rate_bar_chart(labels, rates, title="Attendance Rate (%)",
                   dark=False, on_done=None):
    def build():
        fig, ax = plt.subplots(figsize=(6, 3.2), dpi=90)
        colors = [_C_PRESENT if r >= 80 else _C_LATE if r >= 60 else _C_ABSENT
                  for r in rates]
        x = list(range(len(labels)))
        ax.bar(x, rates, color=colors, zorder=3)
        ax.set_ylim(0, 105)
        ax.axhline(80, color=_C_PRESENT, lw=1, ls="--", alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=28, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.set_ylabel("%", fontsize=9)
        _style(fig, ax, dark)
        fig.tight_layout()
        return fig

    if on_done:
        _run(build, on_done)
    else:
        return _make_canvas(build())


def donut_chart(present, absent, late, title="", dark=False, on_done=None):
    def build():
        total = present + absent + late
        fig, ax = plt.subplots(figsize=(3, 3), dpi=90)

        bg = "#1C1B1F" if dark else "#FAFAFA"
        fg = "#E6E1E5" if dark else "#1C1B1F"
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)

        if total == 0:
            ax.pie(
                [1],
                colors=["#444444" if dark else "#D9D9D9"],
                startangle=90,
                wedgeprops=dict(width=0.42, edgecolor="none"),
            )
            center_text = "No Data"
        else:
            ax.pie(
                [present, absent, late],
                colors=[_C_PRESENT, _C_ABSENT, _C_LATE],
                startangle=90,
                wedgeprops=dict(width=0.42, edgecolor="none"),
            )
            rate = round(present / total * 100, 1)
            center_text = f"{rate}%"

        ax.text(0, 0, center_text, ha="center", va="center",
                fontsize=15, fontweight="bold", color=fg)

        if title:
            ax.set_title(title, fontsize=9, color=fg, pad=4)

        fig.tight_layout(pad=0.5)
        return fig

    if on_done:
        _run(build, on_done)
    else:
        return _make_canvas(build())

def line_chart(labels, series: dict, title="Trend",
               ylabel="Value", dark=False, on_done=None):
    """
    series: {"Label": [values, ...], ...}
    """
    palette = ["#4CAF50", "#F44336", "#FF9800", "#2196F3"]

    def build():
        fig, ax = plt.subplots(figsize=(6, 3.2), dpi=90)
        x = list(range(len(labels)))
        for idx, (name, vals) in enumerate(series.items()):
            ax.plot(x, vals, marker="o", markersize=3, linewidth=1.4,
                    label=name, color=palette[idx % len(palette)])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=28, ha="right", fontsize=8)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.legend(fontsize=8, framealpha=0)
        _style(fig, ax, dark)
        fig.tight_layout()
        return fig

    if on_done:
        _run(build, on_done)
    else:
        return _make_canvas(build())


def horizontal_bar_chart(labels, values, title="Rates (%)",
                         dark=False, on_done=None):
    """Horizontal bar chart coloured by threshold (green/amber/red)."""
    def build():
        n = len(labels)
        fig_h = max(3.0, n * 0.35)
        fig, ax = plt.subplots(figsize=(6, fig_h), dpi=90)
        y = list(range(n))
        clrs = [_C_PRESENT if v >= 90 else _C_LATE if v >= 75
                else _C_ABSENT for v in values]
        ax.barh(y, values, color=clrs, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlim(0, 105)
        ax.axvline(75, color=_C_ABSENT, lw=0.8, ls="--", alpha=0.6)
        ax.axvline(90, color=_C_PRESENT, lw=0.8, ls="--", alpha=0.6)
        ax.set_xlabel("%", fontsize=9)
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        _style(fig, ax, dark)
        fig.tight_layout()
        return fig

    if on_done:
        _run(build, on_done)
    else:
        return _make_canvas(build())
