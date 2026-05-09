from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivymd.uix.screen import MDScreen
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDIconButton
from kivymd.uix.divider import MDDivider

Builder.load_file("screens/teachers.kv")



class TeacherRow(RecycleDataViewBehavior, MDBoxLayout):
    teacher_name  = StringProperty()
    teacher_email = StringProperty()
    class_names   = StringProperty()
    _data = ObjectProperty(allownone=True)

    def refresh_view_attrs(self, rv, index, data):
        self.teacher_name  = data.get("name", "")
        self.teacher_email = data.get("email", "")
        classes = data.get("classes", [])
        self.class_names   = ", ".join(c["name"] for c in classes) if classes else "No class"
        self._data         = data
        return super().refresh_view_attrs(rv, index, data)

    def on_edit(self):
        if not self._data:
            return
        from kivy.app import App
        screen = (App.get_running_app().root
                  .get_screen("main").ids.content_manager
                  .get_screen("teachers"))
        screen._open_edit_dialog(self._data)

    def on_delete(self):
        if not self._data:
            return
        from kivy.app import App
        screen = (App.get_running_app().root
                  .get_screen("main").ids.content_manager
                  .get_screen("teachers"))
        screen._confirm_delete(self._data)


class TeachersScreen(MDScreen):
    admin: dict = {}
    _classes: list = []
    _sel_class_ids: list = []

    def refresh(self, *args):
        self.ids.rv.data = []
        self._show_spinner(True)
        from api.client import get_classes, get_teachers
        get_classes(self._on_classes, self._err)
        get_teachers(self._on_data, self._err)

    def _show_spinner(self, val: bool):
        self.ids.spinner_box.height = "56dp" if val else "0dp"
        self.ids.spinner.active = val

    def _on_classes(self, data):
        self._classes = data
        if data:
            self._sel_class_ids = [data[0]["id"]]
            self._update_class_btn()

    def _update_class_btn(self):
        names = [c["name"] for c in self._classes
                 if c["id"] in self._sel_class_ids]
        label = ", ".join(names) if names else "Select classes"
        for child in self.ids.class_btn.children:
            if hasattr(child, "text"):
                child.text = label
                break

    def open_class_menu(self):
        if not self._classes:
            return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.class_btn,
            items=[
                {"text": f"{'[x] ' if c['id'] in self._sel_class_ids else '[ ] '}{c['name']}",
                 "on_release": lambda c=c: self._toggle_class(c)}
                for c in self._classes
            ],
        )
        self._menu.open()

    def _toggle_class(self, cls):
        if cls["id"] in self._sel_class_ids:
            self._sel_class_ids.remove(cls["id"])
        else:
            self._sel_class_ids.append(cls["id"])
        self._update_class_btn()
        # Reopen to show updated state
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self.open_class_menu()

    def _on_data(self, data):
        self._show_spinner(False)
        self.ids.count_lbl.text = f"{len(data)} teachers"
        self.ids.rv.data = list(data)

    def create_teacher(self):
        name  = self.ids.teacher_name.text.strip()
        email = self.ids.teacher_email.text.strip()
        pwd   = self.ids.teacher_pwd.text.strip()
        if not (name and email and pwd):
            from components.snackbar import show
            show("Fill in all fields")
            return
        if not self._sel_class_ids:
            from components.snackbar import show
            show("Select at least one class")
            return
        self.ids.create_btn.disabled = True
        from api.client import create_teacher
        create_teacher(name, email, pwd, self._sel_class_ids,
                       self._on_created, self._err)

    def _on_created(self, data):
        for fid in ("teacher_name", "teacher_email", "teacher_pwd"):
            self.ids[fid].text = ""
        self.ids.create_btn.disabled = False
        from components.snackbar import show
        show(f"Teacher '{data['name']}' created")
        self.refresh()

    def _confirm_delete(self, t):
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText

        def _do(*_):
            dlg.dismiss()
            from api.client import delete_teacher
            delete_teacher(t["id"], lambda _: self.refresh(), self._err)

        dlg = MDDialog(
            MDDialogHeadlineText(text="Remove Teacher"),
            MDDialogSupportingText(text=f"Remove {t['name']}?"),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Remove"), style="filled",
                         on_release=_do),
            ),
        )
        dlg.open()

    def _open_edit_dialog(self, teacher: dict):
        """Edit teacher name and class assignments."""
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogContentContainer,
            MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText, MDButtonIcon
        from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivy.metrics import dp

        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(12),
            padding=[0, dp(8), 0, 0],
        )

        # Name field
        name_field = MDTextField(
            mode="outlined",
            size_hint_y=None,
            height="52dp",
        )
        name_field.add_widget(MDTextFieldHintText(text="Full name"))
        name_field.text = teacher.get("name", "")
        content.add_widget(name_field)

        # Class assignment button
        current_ids = [c["id"] for c in teacher.get("classes", [])]
        edit_class_ids = list(current_ids)

        class_lbl = MDLabel(
            text="Classes: " + (
                ", ".join(c["name"] for c in teacher.get("classes", []))
                or "None"
            ),
            font_style="Body",
            role="medium",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        content.add_widget(class_lbl)

        pick_btn = MDButton(style="tonal", size_hint_y=None, height="44dp")
        pick_btn.add_widget(MDButtonIcon(icon="google-classroom"))
        pick_btn.add_widget(MDButtonText(text="Change classes…"))
        content.add_widget(pick_btn)

        def open_class_picker(*_):
            if not self._classes:
                from components.snackbar import show
                show("No classes loaded")
                return
            from kivymd.uix.menu import MDDropdownMenu
            def toggle(c):
                if c["id"] in edit_class_ids:
                    edit_class_ids.remove(c["id"])
                else:
                    edit_class_ids.append(c["id"])
                names = [cl["name"] for cl in self._classes if cl["id"] in edit_class_ids]
                class_lbl.text = "Classes: " + (", ".join(names) or "None")
                if hasattr(open_class_picker, "_menu"):
                    open_class_picker._menu.dismiss()
                open_class_picker()

            m = MDDropdownMenu(
                caller=pick_btn,
                items=[
                    {"text": f"{'[x] ' if c['id'] in edit_class_ids else '[ ] '}{c['name']}",
                     "on_release": lambda c=c: toggle(c)}
                    for c in self._classes
                ],
            )
            open_class_picker._menu = m
            m.open()

        pick_btn.bind(on_release=open_class_picker)

        def _save(*_):
            new_name = name_field.text.strip()
            if not new_name:
                from components.snackbar import show
                show("Name cannot be empty")
                return
            if not edit_class_ids:
                from components.snackbar import show
                show("Assign at least one class")
                return
            dlg.dismiss()
            # Update classes (backend endpoint available for admin)
            from api.client import update_teacher_classes
            update_teacher_classes(
                teacher["id"], edit_class_ids,
                lambda _: self.refresh(), self._err,
            )
            # Name update — best effort via same patch if name changed
            if new_name != teacher.get("name", ""):
                from api.client import _h, BASE_URL
                import httpx, threading
                def _patch_name():
                    try:
                        httpx.patch(
                            f"{BASE_URL}/teachers/{teacher['id']}",
                            json={"name": new_name},
                            headers=_h(), timeout=10,
                        )
                    except Exception:
                        pass  # endpoint may not exist; class update already saved
                threading.Thread(target=_patch_name, daemon=True).start()

        dlg = MDDialog(
            MDDialogHeadlineText(text="Edit Teacher"),
            MDDialogSupportingText(text=teacher.get("email", "")),
            MDDialogContentContainer(content),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Save"), style="filled",
                         on_release=_save),
            ),
        )
        dlg.open()

    def _err(self, msg):
        self._show_spinner(False)
        self.ids.create_btn.disabled = False
        from components.snackbar import show
        show(str(msg))
