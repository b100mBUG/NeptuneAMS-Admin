"""
Platform Reports screen — school overview PDF for superadmin.
Lets the platform admin pick a school, set a date range,
and download the school overview PDF.
"""
import os
from datetime import date, timedelta

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/platform_reports.kv")


def _save_dir() -> str:
    dl = os.path.join(os.path.expanduser("~"), "Downloads")
    return dl if os.path.isdir(dl) else os.path.expanduser("~")


def _save(filename: str, data: bytes) -> str:
    path = os.path.join(_save_dir(), filename)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def _safe(name: str) -> str:
    return name.replace(" ", "_").replace("/", "-")


class PlatformReportsScreen(MDScreen):
    role:      str  = "platform"
    _schools:  list = []
    _sel:      dict | None = None
    _start: date = date.today().replace(day=1)
    _end:   date = date.today()

    def refresh(self, *args):
        self._refresh_date_labels()
        from api.client import get_schools
        get_schools(self._on_schools, self._err)

    def _on_schools(self, data):
        self._schools = data
        if data and self._sel is None:
            self._sel = data[0]
        self._sync_btn()

    def _sync_btn(self):
        self.ids.lbl_school.text = (
            self._sel["name"] if self._sel else "Select school")

    def open_school_menu(self):
        if not self._schools:
            from components.snackbar import show; show("No schools loaded"); return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.btn_school,
            items=[{"text": s["name"],
                    "on_release": lambda s=s: self._pick(s)}
                   for s in self._schools],
        )
        self._menu.open()

    def _pick(self, s):
        self._sel = s
        self._sync_btn()
        if hasattr(self, "_menu"):
            self._menu.dismiss()

    # ── Date ──────────────────────────────────────────────────────────────

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

    # ── Download ──────────────────────────────────────────────────────────

    def download_overview(self):
        if not self._sel:
            from components.snackbar import show; show("Select a school"); return
        if self._end < self._start:
            from components.snackbar import show
            show("End date must be on or after start date"); return
        self.ids.btn_dl.disabled = True
        self._set_status("Generating…", True)
        s = self._sel
        from api.client import download_school_overview_pdf
        download_school_overview_pdf(
            s["id"], self._start.isoformat(), self._end.isoformat(),
            lambda data: self._done(s, data),
            lambda msg: self._on_err(msg),
        )

    def _done(self, school, data: bytes):
        self.ids.btn_dl.disabled = False
        fname = f"school_overview_{_safe(school['name'])}_{self._start}_{self._end}.pdf"
        path = _save(fname, data)
        self._set_status(f"✓ Saved: {fname}", False)
        from components.snackbar import show
        show(f"Saved to {path}")

    def _on_err(self, msg: str):
        self.ids.btn_dl.disabled = False
        self._set_status("", False)
        from components.snackbar import show; show(str(msg))

    def _set_status(self, text: str, loading: bool):
        self.ids.lbl_status.text    = text
        self.ids.spinner_box.height = "48dp" if loading else "0dp"
        self.ids.spinner.active     = loading

    def _err(self, msg):
        from components.snackbar import show; show(str(msg))
