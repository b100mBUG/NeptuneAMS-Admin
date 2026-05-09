from datetime import date, timedelta

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/analytics.kv")


class AnalyticsScreen(MDScreen):
    role:     str  = "admin"
    user:     dict = {}
    _classes: list = []
    _sel_cls        = None   # selected class dict
    _start: date    = date.today().replace(day=1)
    _end:   date    = date.today()
    _data:  dict    = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def refresh(self, *args):
        self._clear_charts()
        self._show_spinner(True)
        from api.client import get_classes
        get_classes(self._on_classes, self._err)
        self._refresh_date_labels()

    # ── Class list ────────────────────────────────────────────────────────

    def _on_classes(self, data):
        self._classes = data
        self._show_spinner(False)
        if data and self._sel_cls is None:
            self._sel_cls = data[0]
        self._sync_class_btn()

    def _sync_class_btn(self):
        if self._sel_cls:
            self.ids.lbl_class_btn.text = self._sel_cls["name"]

    def open_class_menu(self):
        if not self._classes:
            from components.snackbar import show
            show("No classes loaded")
            return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.btn_class,
            items=[
                {"text": c["name"],
                 "on_release": lambda c=c: self._pick_class(c)}
                for c in self._classes
            ],
        )
        self._menu.open()

    def _pick_class(self, cls):
        self._sel_cls = cls
        self._sync_class_btn()
        if hasattr(self, "_menu"):
            self._menu.dismiss()

    # ── Date range ────────────────────────────────────────────────────────

    def set_range_week(self):
        today = date.today()
        self._start = today - timedelta(days=today.weekday())
        self._end   = today
        self._refresh_date_labels()

    def set_range_month(self):
        today = date.today()
        self._start = today.replace(day=1)
        self._end   = today
        self._refresh_date_labels()

    def set_range_term(self):
        today = date.today()
        self._start = today - timedelta(weeks=13)
        self._end   = today
        self._refresh_date_labels()

    def _refresh_date_labels(self):
        self.ids.lbl_start.text = self._start.strftime("%d %b %Y")
        self.ids.lbl_end.text   = self._end.strftime("%d %b %Y")

    def pick_start(self):
        self._open_date_picker("start")

    def pick_end(self):
        self._open_date_picker("end")

    def _open_date_picker(self, which: str):
        from kivymd.uix.pickers import MDDockedDatePicker
        current = self._start if which == "start" else self._end
        picker  = MDDockedDatePicker(year=current.year,
                                     month=current.month,
                                     day=current.day)
        picker.bind(on_ok=lambda inst, *a: self._date_ok(inst, which))
        picker.bind(on_cancel=lambda inst, *a: inst.dismiss())
        picker.open()

    def _date_ok(self, picker, which: str):
        sel = picker.get_date()
        if not sel:
            picker.dismiss()
            return
        chosen = sel[0] if isinstance(sel, list) else sel
        if isinstance(chosen, date):
            if which == "start":
                self._start = chosen
                self.ids.lbl_start.text = chosen.strftime("%d %b %Y")
            else:
                self._end = chosen
                self.ids.lbl_end.text = chosen.strftime("%d %b %Y")
        picker.dismiss()

    # ── Load analysis ─────────────────────────────────────────────────────

    def run_analysis(self):
        if not self._sel_cls:
            from components.snackbar import show
            show("Select a class first")
            return
        if self._end < self._start:
            from components.snackbar import show
            show("End date must be after start date")
            return
        self._clear_charts()
        self._show_spinner(True)
        from api.client import get_class_analysis
        get_class_analysis(
            self._sel_cls["id"],
            self._start.isoformat(),
            self._end.isoformat(),
            self._on_data,
            self._err,
        )

    def _on_data(self, data):
        self._data = data
        self._show_spinner(False)
        Clock.schedule_once(lambda dt: self._render(data))

    # ── Render charts ─────────────────────────────────────────────────────

    def _render(self, d):
        """Build a sequential task queue so charts render one at a time.
        Each chart thread only starts after the previous widget is on screen,
        keeping the main thread free between renders and eliminating lag."""
        dark = self._is_dark()
        from components.chart import (
            attendance_bar_chart, rate_bar_chart,
            donut_chart, horizontal_bar_chart,
        )
        ov        = d.get("overall", {})
        container = self.ids.charts_container

        # Stat strip is instant (pure Kivy widgets, no matplotlib)
        self._add_stat_strip(container, ov)

        # ── Build the task queue ──────────────────────────────────────────
        # Each task is a callable(next_task) that renders one chart, then
        # calls next_task() from its on_done callback to trigger the next.
        from kivymd.uix.boxlayout import MDBoxLayout

        # Shared row widget for the donut + monthly side-by-side pair
        pair_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(300),
            spacing=dp(16),
        )
        container.add_widget(pair_row)   # add the row now; cards fill in later

        tasks = []

        # 1. Donut chart
        def task_donut(next_task):
            def on_done(w):
                pair_row.add_widget(
                    self._chart_card("Status Distribution", w,
                                     height=dp(300), size_hint_x=0.35))
                next_task()
            donut_chart(ov.get("present", 0), ov.get("absent", 0),
                        ov.get("late", 0), "", dark, on_done=on_done)
        tasks.append(task_donut)

        # 2. Monthly rate (only if data exists)
        if d.get("monthly_trend"):
            labels = [r["label"] for r in d["monthly_trend"]]
            rates  = [r["rate"]  for r in d["monthly_trend"]]
            def task_monthly(next_task, _l=labels, _r=rates):
                def on_done(w):
                    pair_row.add_widget(
                        self._chart_card("Monthly Attendance Rate (%)", w,
                                         height=dp(300), size_hint_x=0.65))
                    next_task()
                rate_bar_chart(_l, _r, "Monthly Attendance Rate (%)",
                               dark, on_done=on_done)
            tasks.append(task_monthly)

        # 3. Weekly breakdown
        if d.get("weekly_trend"):
            wl  = [r["label"]   for r in d["weekly_trend"]]
            wp  = [r["present"] for r in d["weekly_trend"]]
            wa  = [r["absent"]  for r in d["weekly_trend"]]
            wlt = [r["late"]    for r in d["weekly_trend"]]
            def task_weekly(next_task, _wl=wl, _wp=wp, _wa=wa, _wlt=wlt):
                def on_done(w):
                    container.add_widget(
                        self._chart_card("Weekly Attendance Breakdown", w))
                    next_task()
                attendance_bar_chart(_wl, _wp, _wa, _wlt,
                                     "Weekly Attendance Breakdown",
                                     dark, on_done=on_done)
            tasks.append(task_weekly)

        # 4. Per-student horizontal bar
        summaries = d.get("student_summaries", [])
        if summaries:
            s_names = [s["student_name"] for s in summaries]
            s_rates = [s["rate"]         for s in summaries]
            card_h  = dp(max(300, len(s_names) * 24 + 60))
            def task_hbar(next_task, _n=s_names, _r=s_rates, _h=card_h):
                def on_done(w):
                    container.add_widget(
                        self._chart_card("Student Attendance Rates (%)", w,
                                         height=_h))
                    next_task()
                horizontal_bar_chart(_n, _r,
                                     "Attendance Rate per Student (%)",
                                     dark, on_done=on_done)
            tasks.append(task_hbar)

        # 5. At-risk table (instant, no thread)
        at_risk = d.get("at_risk_students", [])
        if at_risk:
            def task_at_risk(next_task, _rows=at_risk):
                self._add_student_table(
                    container, "At-Risk Students (Rate < 75%)",
                    _rows, alert=True)
                next_task()
            tasks.append(task_at_risk)

        # 6. Perfect attendance table (instant, no thread)
        perfect = d.get("perfect_attendance", [])
        if perfect:
            def task_perfect(next_task, _rows=perfect):
                self._add_student_table(
                    container, "Perfect Attendance (100%)",
                    _rows, alert=False)
                next_task()
            tasks.append(task_perfect)

        # 7. Per-period bar
        by_period = d.get("by_period", [])
        if by_period:
            period_labels = [r["period"] for r in by_period]
            period_rates  = [r["rate"]   for r in by_period]
            def task_period(next_task, _l=period_labels, _r=period_rates):
                def on_done(w):
                    container.add_widget(
                        self._chart_card("Attendance Rate by Period (%)", w))
                    next_task()
                rate_bar_chart(_l, _r, "Attendance Rate by Period (%)",
                               dark, on_done=on_done)
            tasks.append(task_period)

        # ── Chain and kick off ────────────────────────────────────────────
        def run_next(task_list):
            if not task_list:
                return   # all done
            head, *tail = task_list
            # Small Clock delay (1 frame) between tasks so Kivy can redraw
            Clock.schedule_once(
                lambda dt: head(lambda: run_next(tail)), 0)

        run_next(tasks)

    # ── UI helpers ────────────────────────────────────────────────────────

    def _add_stat_strip(self, container, ov):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.divider import MDDivider
        from kivy.app import App

        strip = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(88),
            md_bg_color=App.get_running_app().theme_cls.surfaceContainerColor,
            radius=[dp(12)],
            spacing=dp(1),
        )
        stats = [
            ("Present", str(ov.get("present", 0)), (0.13, 0.69, 0.30, 1)),
            ("Absent",  str(ov.get("absent",  0)), (0.83, 0.18, 0.18, 1)),
            ("Late",    str(ov.get("late",    0)), (0.87, 0.55, 0.06, 1)),
            ("Excused", str(ov.get("excused", 0)), (0.20, 0.50, 0.85, 1)),
            ("Rate",    f"{ov.get('rate', 0)}%",    (0.13, 0.69, 0.30, 1)),
        ]
        for label, val, color in stats:
            col = MDBoxLayout(orientation="vertical",
                              padding=[dp(20), dp(10)])
            num = MDLabel(text=val, font_style="Headline", role="small",
                          bold=True, adaptive_height=True,
                          theme_text_color="Custom", text_color=color)
            lbl = MDLabel(text=label, font_style="Label", role="large",
                          theme_text_color="Secondary", adaptive_height=True)
            col.add_widget(num)
            col.add_widget(lbl)
            strip.add_widget(col)
            if label != "Rate":
                div = MDDivider(orientation="vertical",
                                size_hint_x=None, width=dp(1))
                strip.add_widget(div)

        container.add_widget(strip)

    def _add_student_table(self, container, title: str,
                           rows: list, alert: bool = False):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.card import MDCard
        from kivymd.uix.scrollview import MDScrollView
        from kivy.app import App

        # Cap the visible card height; rows scroll inside if they exceed it
        ROW_H      = dp(36)
        HEADER_H   = dp(32)
        TITLE_H    = dp(36)
        PADDING    = dp(32)   # top + bottom padding inside card
        MAX_ROWS_VISIBLE = 8

        content_h  = HEADER_H + len(rows) * ROW_H
        visible_h  = min(content_h, MAX_ROWS_VISIBLE * ROW_H + HEADER_H)
        card_h     = TITLE_H + visible_h + PADDING

        card = MDCard(
            orientation="vertical",
            style="elevated",
            radius=[dp(16)],
            padding=dp(16),
            spacing=dp(8),
            size_hint_y=None,
            height=max(dp(120), card_h),
        )

        hdr_color = (0.83, 0.18, 0.18, 0.12) if alert else \
                    App.get_running_app().theme_cls.surfaceContainerColor

        card.add_widget(MDLabel(
            text=title, font_style="Title", role="medium",
            bold=True, size_hint_y=None, height=TITLE_H))

        # ── Column header (outside the scroll so it stays fixed) ──────────
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=HEADER_H,
            md_bg_color=hdr_color, radius=[dp(4)],
            padding=[dp(8), 0])
        for col, sx in [("Student", 1), ("Adm No", 0.28),
                        ("Present", 0.15), ("Absent", 0.15), ("Rate", 0.15)]:
            header.add_widget(MDLabel(
                text=col, font_style="Label", role="large",
                bold=True, size_hint_y=None, height=HEADER_H,
                size_hint_x=sx))
        card.add_widget(header)

        # ── Scrollable rows ───────────────────────────────────────────────
        scroll = MDScrollView(
            size_hint=(1, None),
            height=visible_h,
            do_scroll_x=False,
        )

        rows_box = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=len(rows) * ROW_H,
            spacing=0,
        )

        for r in rows:
            row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None, height=ROW_H,
                padding=[dp(8), 0])

            # Student name — clipped to its column, no overflow
            row.add_widget(MDLabel(
                text=r.get("student_name", ""),
                font_style="Body", role="medium",
                size_hint=(1, None), height=ROW_H,
                shorten=True, shorten_from="right",
                text_size=(None, None)))   # resolved by layout
            row.add_widget(MDLabel(
                text=r.get("student_id", ""),
                font_style="Body", role="small",
                theme_text_color="Secondary",
                size_hint=(0.28, None), height=ROW_H,
                shorten=True, shorten_from="right"))
            row.add_widget(MDLabel(
                text=str(r.get("present", 0)),
                font_style="Body", role="medium",
                size_hint=(0.15, None), height=ROW_H))
            row.add_widget(MDLabel(
                text=str(r.get("absent", 0)),
                font_style="Body", role="medium",
                theme_text_color="Custom",
                text_color=(0.83, 0.18, 0.18, 1) if alert else (0, 0, 0, 0.87),
                size_hint=(0.15, None), height=ROW_H))
            color = ((0.83, 0.18, 0.18, 1) if r.get("rate", 100) < 75
                     else (0.87, 0.55, 0.06, 1) if r.get("rate", 100) < 90
                     else (0.13, 0.69, 0.30, 1))
            row.add_widget(MDLabel(
                text=f"{r.get('rate', 0)}%",
                font_style="Body", role="medium",
                theme_text_color="Custom", text_color=color,
                bold=True,
                size_hint=(0.15, None), height=ROW_H))
            rows_box.add_widget(row)

        scroll.add_widget(rows_box)
        card.add_widget(scroll)
        container.add_widget(card)

    def _chart_card(self, title: str, widget,
                    height=dp(340), size_hint_x=1.0):
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel
        TITLE_H = dp(32)
        card = MDCard(
            orientation="vertical",
            style="elevated",
            radius=[dp(16)],
            padding=dp(16),
            spacing=dp(8),
            size_hint_y=None,
            size_hint_x=size_hint_x,
            height=height,
        )
        card.add_widget(MDLabel(
            text=title, font_style="Title", role="medium",
            bold=True, size_hint_y=None, height=TITLE_H))
        # Give the chart widget the remaining vertical space inside the card
        widget.size_hint = (1, None)
        widget.height = height - TITLE_H - dp(48)  # subtract padding + title
        card.add_widget(widget)
        return card

    def _clear_charts(self):
        self.ids.charts_container.clear_widgets()

    def _show_spinner(self, val: bool):
        self.ids.spinner_box.height = "56dp" if val else "0dp"
        self.ids.spinner.active = val

    def _is_dark(self):
        from kivy.app import App
        return App.get_running_app().theme_cls.theme_style == "Dark"

    def _err(self, msg):
        self._show_spinner(False)
        from components.snackbar import show
        show(str(msg))