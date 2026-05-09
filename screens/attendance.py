from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.screen import MDScreen
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

Builder.load_file("screens/attendance.kv")

STATUS_COLOR = {
    "present": (0.13, 0.69, 0.30, 1),
    "absent":  (0.83, 0.18, 0.18, 1),
    "late":    (0.87, 0.55, 0.06, 1),
    "excused": (0.20, 0.50, 0.85, 1),
}



class AttendanceRow(RecycleDataViewBehavior, MDBoxLayout):
    student_name = StringProperty()
    adm_no       = StringProperty()
    session_date = StringProperty()
    status_text  = StringProperty()
    status_color = ObjectProperty((0.5, 0.5, 0.5, 1))

    def refresh_view_attrs(self, rv, index, data):
        self.student_name = data.get("student_name") or data.get("std_id", "")
        self.adm_no       = data.get("std_id", "")
        self.session_date = str(data.get("session_date", ""))
        status = data.get("status", "—")
        self.status_text  = status.capitalize()
        self.status_color = STATUS_COLOR.get(status, (0.5, 0.5, 0.5, 1))
        return super().refresh_view_attrs(rv, index, data)


class AttendanceViewScreen(MDScreen):
    admin: dict = {}
    _classes:  list = []
    _sel_class = None
    _period:   str  = "morning"

    def refresh(self, *args):
        from api.client import get_classes
        get_classes(self._on_classes, self._err)

    def _on_classes(self, data):
        self._classes = data
        if data and self._sel_class is None:
            self._sel_class = data[0]
            self._update_class_btn(data[0]["name"])
            self._load()

    def _update_class_btn(self, name: str):
        for child in self.ids.class_btn.children:
            if hasattr(child, "text"):
                child.text = name
                break

    def open_class_menu(self):
        if not self._classes:
            return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.class_btn,
            items=[{"text": c["name"],
                    "on_release": lambda c=c: self._switch_class(c)}
                   for c in self._classes],
        )
        self._menu.open()

    def _switch_class(self, cls):
        self._sel_class = cls
        self._update_class_btn(cls["name"])
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self._load()

    def set_period(self, period: str, active: bool):
        if not active:
            return
        self._period = period
        self._load()

    def _load(self):
        if not self._sel_class:
            return
        self.ids.rv.data = []
        self._show_spinner(True)
        for lbl_id in ("stat_present", "stat_absent", "stat_late",
                       "stat_excused", "stat_total"):
            self.ids[lbl_id].text = "—"
        self.ids.donut_box.clear_widgets()
        from api.client import get_class_attendance
        get_class_attendance(
            self._sel_class["id"], self._period,
            self._on_data, self._err,
        )

    def _show_spinner(self, val: bool):
        self.ids.spinner_box.height = "56dp" if val else "0dp"
        self.ids.spinner.active = val

    def _on_data(self, data):
        self._show_spinner(False)
        present = sum(1 for r in data if r["status"] == "present")
        absent  = sum(1 for r in data if r["status"] == "absent")
        late    = sum(1 for r in data if r["status"] == "late")
        excused = sum(1 for r in data if r["status"] == "excused")
        total   = len(data)

        self.ids.stat_present.text = str(present)
        self.ids.stat_absent.text  = str(absent)
        self.ids.stat_late.text    = str(late)
        self.ids.stat_excused.text = str(excused)
        self.ids.stat_total.text   = str(total)

        dark = self._is_dark()
        from components.chart import donut_chart

        def put_donut(w):
            box = self.ids.donut_box
            box.clear_widgets()
            box.add_widget(w)

        donut_chart(present, absent, late, "", dark, on_done=put_donut)
        self.ids.rv.data = list(data)

    def _is_dark(self):
        from kivy.app import App
        return App.get_running_app().theme_cls.theme_style == "Dark"

    def _err(self, msg):
        self._show_spinner(False)
        from components.snackbar import show
        show(str(msg))
