from kivy.lang import Builder
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/overview.kv")


class OverviewScreen(MDScreen):
    role:      str  = "admin"
    user:      dict = {}
    school_id: str  = ""
    _classes:        list = []
    _chart_data:     dict = {}
    _chart_needed:   int  = 0
    _chart_done:     int  = 0
    _student_total:  int  = 0
    _students_needed:int  = 0
    _students_done:  int  = 0

    def refresh(self, *args):
        for wid_id in ("stat_classes", "stat_teachers",
                       "stat_students", "stat_present"):
            w = self.ids.get(wid_id)
            if w:
                w.text = "—"
        self.ids.chart_bar_box.clear_widgets()
        self.ids.chart_rate_box.clear_widgets()
        self._show_spinner(True)
        self._classes = []
        self._chart_data = {}
        self._student_total = 0

        from api.client import get_classes, get_teachers
        get_classes(self._on_classes, self._err)
        get_teachers(
            lambda d: setattr(self.ids.stat_teachers, "text", str(len(d))),
            self._err,
        )

    def _on_classes(self, data):
        self._classes = data
        self.ids.stat_classes.text = str(len(data))
        if not data:
            self._show_spinner(False)
            return
        self._student_total    = 0
        self._students_needed  = len(data)
        self._students_done    = 0
        for cls in data:
            from api.client import get_students
            get_students(
                cls["id"],
                lambda d, _c=cls: self._on_students(d),
                self._err,
            )

    def _on_students(self, data):
        self._student_total += len(data)
        self._students_done += 1
        self.ids.stat_students.text = str(self._student_total)
        if self._students_done >= self._students_needed:
            self._show_spinner(False)

    # ── Charts (loaded on demand via button) ─────────────────────────────

    def load_charts(self):
        if not self._classes:
            from components.snackbar import show
            show("No classes loaded yet — try again in a moment")
            return
        self._show_spinner(True)
        self.ids.chart_bar_box.clear_widgets()
        self.ids.chart_rate_box.clear_widgets()
        self._chart_data    = {}
        self._chart_needed  = len(self._classes)
        self._chart_done    = 0

        from api.client import get_class_analysis
        from datetime import date, timedelta
        start = (date.today() - timedelta(weeks=4)).isoformat()
        end   = date.today().isoformat()

        for cls in self._classes:
            get_class_analysis(
                cls["id"], start, end,
                lambda d, c=cls: self._on_chart_data(d, c),
                lambda msg: self._on_chart_err(msg),
            )

    def _on_chart_data(self, data, cls):
        self._chart_data[cls["name"]] = data.get("overall", {})
        self._chart_done += 1
        if self._chart_done >= self._chart_needed:
            self._show_spinner(False)
            Clock.schedule_once(lambda dt: self._render_charts())

    def _on_chart_err(self, msg):
        self._chart_done += 1
        if self._chart_done >= self._chart_needed:
            self._show_spinner(False)

    def _render_charts(self):
        if not self._chart_data:
            return
        labels  = list(self._chart_data.keys())
        present = [self._chart_data[l].get("present", 0) for l in labels]
        absent  = [self._chart_data[l].get("absent",  0) for l in labels]
        late    = [self._chart_data[l].get("late",    0) for l in labels]
        rates   = [self._chart_data[l].get("rate",    0) for l in labels]
        self.ids.stat_present.text = str(sum(present))

        dark = self._is_dark()
        from components.chart import attendance_bar_chart, rate_bar_chart
        bar_w  = attendance_bar_chart(labels, present, absent, late,
                                      "Attendance by Class (4 wks)", dark)
        rate_w = rate_bar_chart(labels, rates, "Attendance Rate (%)", dark)
        self.ids.chart_bar_box.add_widget(bar_w)
        self.ids.chart_rate_box.add_widget(rate_w)

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
