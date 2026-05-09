from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.screen import MDScreen
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDIconButton
from kivymd.uix.divider import MDDivider
from kivymd.uix.scrollview import MDScrollView
from kivy.metrics import dp
Builder.load_file("screens/students.kv")



class StudentRow(RecycleDataViewBehavior, MDBoxLayout):
    student_name = StringProperty()
    adm_no       = StringProperty()
    _data = ObjectProperty(allownone=True)

    def refresh_view_attrs(self, rv, index, data):
        self.student_name = data.get("name", "")
        self.adm_no       = f"Adm No: {data.get('id', '')}"
        self._data        = data
        return super().refresh_view_attrs(rv, index, data)

    def on_edit(self):
        if not self._data:
            return
        from kivy.app import App
        screen = (App.get_running_app().root
                  .get_screen("main").ids.content_manager
                  .get_screen("students"))
        screen._open_edit_dialog(self._data)

    def on_delete(self):
        if not self._data:
            return
        from kivy.app import App
        screen = (App.get_running_app().root
                  .get_screen("main").ids.content_manager
                  .get_screen("students"))
        screen._confirm_delete(self._data)


class StudentsScreen(MDScreen):
    admin: dict = {}
    _classes: list = []
    _sel_class = None

    def refresh(self, *args):
        self.ids.rv.data = []
        from api.client import get_classes
        get_classes(self._on_classes, self._err)

    def _on_classes(self, data):
        self._classes = data
        if data:
            if self._sel_class is None:
                self._sel_class = data[0]
            # Sync button text
            for child in self.ids.class_btn.children:
                if hasattr(child, "text"):
                    child.text = self._sel_class["name"]
                    break
            self._load_students(self._sel_class["id"])

    def open_class_menu(self):
        if not self._classes:
            return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.class_btn,
            items=[
                {"text": c["name"],
                 "on_release": lambda c=c: self._switch_class(c)}
                for c in self._classes
            ],
        )
        self._menu.open()

    def _switch_class(self, cls):
        self._sel_class = cls
        for child in self.ids.class_btn.children:
            if hasattr(child, "text"):
                child.text = cls["name"]
                break
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self._load_students(cls["id"])

    def _load_students(self, class_id):
        self.ids.rv.data = []
        self._show_spinner(True)
        from api.client import get_students
        get_students(class_id, self._on_students, self._err)

    def _show_spinner(self, val: bool):
        self.ids.spinner_box.height = "56dp" if val else "0dp"
        self.ids.spinner.active = val

    def _on_students(self, data):
        self._show_spinner(False)
        self.ids.count_lbl.text = f"{len(data)} students"
        self.ids.rv.data = list(data)

    def create_student(self):
        adm  = self.ids.adm_field.text.strip()
        name = self.ids.name_field.text.strip()
        if not (adm and name):
            from components.snackbar import show
            show("Fill in all fields")
            return
        if not self._sel_class:
            from components.snackbar import show
            show("Select a class")
            return
        self.ids.create_btn.disabled = True
        from api.client import create_student
        create_student(adm, name, self._sel_class["id"],
                       self._on_created, self._err)

    def _on_created(self, data):
        self.ids.adm_field.text = ""
        self.ids.name_field.text = ""
        self.ids.create_btn.disabled = False
        from components.snackbar import show
        show(f"Student '{data['name']}' added")
        if self._sel_class:
            self._load_students(self._sel_class["id"])

    def _open_edit_dialog(self, student: dict):
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogContentContainer,
            MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText
        from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
        from kivy.metrics import dp

        name_field = MDTextField(
            mode="outlined",
            size_hint_y=None,
            height="52dp",
        )
        name_field.add_widget(MDTextFieldHintText(text="Student full name"))
        name_field.text = student.get("name", "")

        def _save(*_):
            new_name = name_field.text.strip()
            if not new_name:
                from components.snackbar import show
                show("Name cannot be empty")
                return
            dlg.dismiss()
            from api.client import edit_student
            edit_student(
                self._sel_class["id"], student["id"], new_name,
                lambda _: self._load_students(self._sel_class["id"]),
                self._err,
            )

        dlg = MDDialog(
            MDDialogHeadlineText(text="Edit Student"),
            MDDialogSupportingText(text=f"Adm No: {student.get('id', '')}"),
            MDDialogContentContainer(name_field),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Save"), style="filled",
                         on_release=_save),
            ),
        )
        dlg.open()

    def _confirm_delete(self, s):
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText

        def _do(*_):
            dlg.dismiss()
            from api.client import delete_student
            delete_student(self._sel_class["id"], s["id"],
                           lambda _: self._load_students(self._sel_class["id"]),
                           self._err)
        dlg = MDDialog(
            MDDialogHeadlineText(text="Remove Student"),
            MDDialogSupportingText(
                text=f"Remove {s['name']} (Adm: {s['id']})?"),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Remove"), style="filled",
                         on_release=_do),
            ),
        )
        dlg.open()

    def _err(self, msg):
        self._show_spinner(False)
        self.ids.create_btn.disabled = False
        from components.snackbar import show
        show(str(msg))

    # ── Bulk Enrol ────────────────────────────────────────────────────────

    def open_bulk_dialog(self):
        if not self._sel_class:
            from components.snackbar import show
            show("Select a class first")
            return
        self._bulk_dialog = self._build_bulk_dialog()
        self._bulk_dialog.open()

    def _build_bulk_dialog(self):
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogContentContainer,
            MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText, MDButtonIcon
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
        from kivy.metrics import dp

        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(12),
            padding=[0, dp(8), 0, 0],
        )

        info = MDLabel(
            text=(
                "Upload a CSV or XLSX file with columns:\n"
                "  id (or admission_no / student_id)  and  name (or full_name)\n\n"
                "Or paste JSON below, e.g.\n"
                '  [{"id":"001","name":"Alice"}, …]'
            ),
            font_style="Body",
            role="medium",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        content.add_widget(info)

        # File pick button
        file_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
        )
        self._bulk_file_lbl = MDLabel(
            text="No file selected",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            adaptive_height=True,
            size_hint_x=1,
        )
        pick_btn = MDButton(style="tonal", size_hint_y=None, height="44dp")
        pick_btn.add_widget(MDButtonIcon(icon="folder-open-outline"))
        pick_btn.add_widget(MDButtonText(text="Choose file"))
        pick_btn.bind(on_release=lambda *_: self._pick_bulk_file())
        file_row.add_widget(pick_btn)
        file_row.add_widget(self._bulk_file_lbl)
        content.add_widget(file_row)

        # JSON textarea
        self._bulk_json_field = MDTextField(
            mode="outlined",
            multiline=True,
            size_hint_y=None,
            height="120dp",
        )
        hint = MDTextFieldHintText(text='JSON: [{"id":"001","name":"Alice"},…]')
        self._bulk_json_field.add_widget(hint)
        text_scroll = MDScrollView(size_hint_y = None, height = dp(400))
        text_scroll.add_widget(self._bulk_json_field)
        content.add_widget(text_scroll)

        self._bulk_status_lbl = MDLabel(
            text="",
            font_style="Body",
            role="medium",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        content.add_widget(self._bulk_status_lbl)

        self._bulk_file_path = None

        dlg = MDDialog(
            MDDialogHeadlineText(
                text=f"Bulk Enrol — {self._sel_class['name']}"),
            MDDialogSupportingText(text=""),
            MDDialogContentContainer(content),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Cancel"), style="text",
                    on_release=lambda *_: dlg.dismiss() if hasattr(self, "_bulk_dialog") else None,
                ),
                MDButton(
                    MDButtonText(text="Import"), style="filled",
                    on_release=lambda *_: self._do_bulk_import(),
                ),
            ),
        )
        # patch cancel now that dlg exists
        dlg.children[0].children[-1].children[1].bind(
            on_release=lambda *_: dlg.dismiss())
        return dlg

    def _pick_bulk_file(self):
        """Open a native file chooser dialog for CSV/XLSX."""
        from kivymd.uix.filemanager import MDFileManager
        self._fm = MDFileManager(
            exit_manager=self._fm_exit,
            select_path=self._fm_select,
            ext=[".csv", ".xlsx"],
        )
        import os
        self._fm.show(os.path.expanduser("~"))

    def _fm_exit(self, *args):
        self._fm.close()

    def _fm_select(self, path: str):
        self._fm.close()
        self._bulk_file_path = path
        import os
        self._bulk_file_lbl.text = os.path.basename(path)

    def _do_bulk_import(self):
        if not self._sel_class:
            return
        class_id = self._sel_class["id"]

        # File takes priority over JSON text
        if self._bulk_file_path:
            self._bulk_import_file(class_id, self._bulk_file_path)
        else:
            raw = (self._bulk_json_field.text or "").strip()
            if not raw:
                from components.snackbar import show
                show("Choose a file or paste JSON")
                return
            self._bulk_import_json(class_id, raw)

    def _bulk_import_file(self, class_id: str, path: str):
        self._bulk_status_lbl.text = "Uploading…"
        import threading, httpx
        from api.client import BASE_URL, _h

        def worker():
            from kivy.clock import Clock
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                import os
                fname = os.path.basename(path)
                ct = "text/csv" if fname.lower().endswith(".csv") else (
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet")
                resp = httpx.post(
                    f"{BASE_URL}/classes/{class_id}/students/import-file",
                    headers=_h(),
                    files={"file": (fname, data, ct)},
                    timeout=30,
                )
                resp.raise_for_status()
                n = resp.json().get("inserted", "?")
                Clock.schedule_once(lambda dt: self._bulk_done(n))
            except httpx.HTTPStatusError as exc:
                try:
                    detail = exc.response.json().get("detail", str(exc))
                except Exception:
                    detail = str(exc)
                Clock.schedule_once(lambda dt: self._bulk_err(detail))
            except Exception as exc:
                Clock.schedule_once(lambda dt: self._bulk_err(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _bulk_import_json(self, class_id: str, raw: str):
        self._bulk_status_lbl.text = "Sending…"
        import threading, httpx, json
        from api.client import BASE_URL, _h

        try:
            students = json.loads(raw)
        except json.JSONDecodeError as exc:
            from components.snackbar import show
            show(f"Invalid JSON: {exc}")
            return

        def worker():
            from kivy.clock import Clock
            try:
                resp = httpx.post(
                    f"{BASE_URL}/classes/{class_id}/students/import",
                    headers=_h(),
                    json={"students": students},
                    timeout=30,
                )
                resp.raise_for_status()
                n = resp.json().get("inserted", "?")
                Clock.schedule_once(lambda dt: self._bulk_done(n))
            except httpx.HTTPStatusError as exc:
                try:
                    detail = exc.response.json().get("detail", str(exc))
                except Exception:
                    detail = str(exc)
                Clock.schedule_once(lambda dt: self._bulk_err(detail))
            except Exception as exc:
                Clock.schedule_once(lambda dt: self._bulk_err(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _bulk_done(self, n):
        self._bulk_status_lbl.text = f"✓ {n} student(s) enrolled"
        from components.snackbar import show
        show(f"Bulk enrol complete: {n} students added")
        if self._sel_class:
            self._load_students(self._sel_class["id"])

    def _bulk_err(self, msg: str):
        self._bulk_status_lbl.text = f"Error: {msg}"
        from components.snackbar import show
        show(str(msg))
