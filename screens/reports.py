"""
Reports screen — school admin view.

Maps every /reports/* endpoint:
  1. Class attendance CSV
  2. Class attendance PDF
  3. Class analysis PDF
  4. Student analysis PDF
  5. Teacher activity PDF       (single teacher)
  6. Teacher comparison PDF     (all teachers)
"""
import os
from datetime import date, timedelta

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/reports.kv")


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


class ReportsScreen(MDScreen):
    role:     str  = "admin"
    user:     dict = {}
    _classes:  list = []
    _teachers: list = []
    _students: list = []
    _sel_class:   dict | None = None
    _sel_teacher: dict | None = None
    _sel_student: dict | None = None
    _start: date = date.today().replace(day=1)
    _end:   date = date.today()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def refresh(self, *args):
        self._refresh_date_labels()
        from api.client import get_classes, get_teachers
        get_classes(self._on_classes, self._err)
        get_teachers(self._on_teachers, self._err)

    def _on_classes(self, data):
        self._classes = data
        if data and self._sel_class is None:
            self._sel_class = data[0]
        self._sync_class_lbl()

    def _on_teachers(self, data):
        self._teachers = data
        if data and self._sel_teacher is None:
            self._sel_teacher = data[0]
        self._sync_teacher_lbl()

    def _sync_class_lbl(self):
        self.ids.lbl_class.text = (
            self._sel_class["name"] if self._sel_class else "Select class")

    def _sync_teacher_lbl(self):
        self.ids.lbl_teacher.text = (
            self._sel_teacher["name"] if self._sel_teacher else "Select teacher")

    def _sync_student_lbl(self):
        self.ids.lbl_student.text = (
            self._sel_student["name"] if self._sel_student else "Select student")

    # ── Menus ──────────────────────────────────────────────────────────────

    def open_class_menu(self):
        if not self._classes:
            from components.snackbar import show; show("No classes loaded"); return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.btn_class,
            items=[{"text": c["name"],
                    "on_release": lambda c=c: self._pick_class(c)}
                   for c in self._classes],
        )
        self._menu.open()

    def _pick_class(self, cls):
        self._sel_class   = cls
        self._sel_student = None
        self._sync_class_lbl()
        self._sync_student_lbl()
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        # Load students for the newly selected class
        from api.client import get_students
        get_students(cls["id"], self._on_students, self._err)

    def _on_students(self, data):
        self._students = data
        if data and self._sel_student is None:
            self._sel_student = data[0]
        self._sync_student_lbl()

    def open_teacher_menu(self):
        if not self._teachers:
            from components.snackbar import show; show("No teachers loaded"); return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.btn_teacher,
            items=[{"text": t["name"],
                    "on_release": lambda t=t: self._pick_teacher(t)}
                   for t in self._teachers],
        )
        self._menu.open()

    def _pick_teacher(self, t):
        self._sel_teacher = t
        self._sync_teacher_lbl()
        if hasattr(self, "_menu"):
            self._menu.dismiss()

    def open_student_menu(self):
        if not self._students:
            from components.snackbar import show
            show("Select a class first (students load automatically)")
            return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.btn_student,
            items=[{"text": s["name"],
                    "on_release": lambda s=s: self._pick_student(s)}
                   for s in self._students],
        )
        self._menu.open()

    def _pick_student(self, s):
        self._sel_student = s
        self._sync_student_lbl()
        if hasattr(self, "_menu"):
            self._menu.dismiss()

    # ── Date helpers ───────────────────────────────────────────────────────

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

    # ── Download dispatchers ───────────────────────────────────────────────

    def _check_range(self) -> bool:
        if self._end < self._start:
            from components.snackbar import show
            show("End date must be on or after start date")
            return False
        return True

    def _begin(self, btn_id: str):
        self.ids[btn_id].disabled = True
        self._set_status("Generating…", True)

    def _finish(self, btn_id: str, path: str):
        self.ids[btn_id].disabled = False
        self._set_status(f"✓ Saved: {os.path.basename(path)}", False)
        from components.snackbar import show
        show(f"Saved to {path}")

    def _on_err(self, btn_id: str, msg: str):
        self.ids[btn_id].disabled = False
        self._set_status("", False)
        from components.snackbar import show
        show(str(msg))

    def _set_status(self, text: str, loading: bool):
        self.ids.lbl_status.text    = text
        self.ids.spinner_box.height = "48dp" if loading else "0dp"
        self.ids.spinner.active     = loading

    # 1. Class attendance CSV
    def dl_class_csv(self):
        if not self._sel_class or not self._check_range():
            return
        self._begin("btn_class_csv")
        cls = self._sel_class
        period = self.ids.tf_period.text.strip() or None
        from api.client import download_class_attendance_csv
        download_class_attendance_csv(
            cls["id"], self._start.isoformat(), self._end.isoformat(), period,
            lambda data: self._finish(
                "btn_class_csv",
                _save(f"attendance_{_safe(cls['name'])}_{self._start}_{self._end}.csv",
                      data)),
            lambda msg: self._on_err("btn_class_csv", msg),
        )

    # 2. Class attendance PDF
    def dl_class_att_pdf(self):
        if not self._sel_class or not self._check_range():
            return
        self._begin("btn_class_att_pdf")
        cls = self._sel_class
        period = self.ids.tf_period.text.strip() or None
        from api.client import download_class_attendance_pdf
        download_class_attendance_pdf(
            cls["id"], self._start.isoformat(), self._end.isoformat(), period,
            lambda data: self._finish(
                "btn_class_att_pdf",
                _save(f"attendance_{_safe(cls['name'])}_{self._start}_{self._end}.pdf",
                      data)),
            lambda msg: self._on_err("btn_class_att_pdf", msg),
        )

    # 3. Class analysis PDF
    def dl_class_analysis_pdf(self):
        if not self._sel_class or not self._check_range():
            return
        self._begin("btn_class_analysis")
        cls = self._sel_class
        from api.client import download_class_analysis_pdf
        download_class_analysis_pdf(
            cls["id"], self._start.isoformat(), self._end.isoformat(),
            lambda data: self._finish(
                "btn_class_analysis",
                _save(f"class_analysis_{_safe(cls['name'])}_{self._start}_{self._end}.pdf",
                      data)),
            lambda msg: self._on_err("btn_class_analysis", msg),
        )

    # 4. Student analysis PDF
    def dl_student_pdf(self):
        if not self._sel_student:
            from components.snackbar import show
            show("Select a student")
            return
        if not self._check_range():
            return
        self._begin("btn_student_pdf")
        stu = self._sel_student
        from api.client import download_student_analysis_pdf
        download_student_analysis_pdf(
            stu["id"], self._start.isoformat(), self._end.isoformat(),
            lambda data: self._finish(
                "btn_student_pdf",
                _save(f"student_{_safe(stu['name'])}_{self._start}_{self._end}.pdf",
                      data)),
            lambda msg: self._on_err("btn_student_pdf", msg),
        )

    # 5. Teacher activity PDF
    def dl_teacher_pdf(self):
        if not self._sel_teacher:
            from components.snackbar import show
            show("Select a teacher")
            return
        if not self._check_range():
            return
        self._begin("btn_teacher_pdf")
        t = self._sel_teacher
        from api.client import download_teacher_activity_pdf
        download_teacher_activity_pdf(
            t["id"], self._start.isoformat(), self._end.isoformat(),
            lambda data: self._finish(
                "btn_teacher_pdf",
                _save(f"teacher_{_safe(t['name'])}_{self._start}_{self._end}.pdf",
                      data)),
            lambda msg: self._on_err("btn_teacher_pdf", msg),
        )

    # 6. Teacher comparison PDF (all teachers)
    def dl_teacher_comparison_pdf(self):
        if not self._check_range():
            return
        self._begin("btn_teacher_comparison")
        from api.client import download_teacher_comparison_pdf
        download_teacher_comparison_pdf(
            self._start.isoformat(), self._end.isoformat(),
            lambda data: self._finish(
                "btn_teacher_comparison",
                _save(f"teacher_comparison_{self._start}_{self._end}.pdf",
                      data)),
            lambda msg: self._on_err("btn_teacher_comparison", msg),
        )

    def _err(self, msg):
        from components.snackbar import show
        show(str(msg))
