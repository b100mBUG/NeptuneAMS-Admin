from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.screen import MDScreen
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout

Builder.load_file("screens/classes.kv")


class ClassRow(RecycleDataViewBehavior, MDBoxLayout):
    name     = StringProperty()
    class_id = StringProperty()
    _cls_data = ObjectProperty(allownone=True)

    def refresh_view_attrs(self, rv, index, data):
        self.name      = data.get("name", "")
        self.class_id  = f"ID: {data.get('id', '')[:8]}…"
        self._cls_data = data
        return super().refresh_view_attrs(rv, index, data)

    def on_delete(self):
        if self._cls_data:
            self._get_screen()._confirm_delete(self._cls_data)

    def on_rename(self):
        if self._cls_data:
            self._get_screen()._open_rename_dialog(self._cls_data)

    def _get_screen(self):
        from kivy.app import App
        return (App.get_running_app().root
                .get_screen("main").ids.content_manager
                .get_screen("classes"))


class ClassesScreen(MDScreen):
    role:     str  = "admin"
    _classes: list = []

    def refresh(self, *args):
        self.ids.rv.data = []
        self._show_spinner(True)
        from api.client import get_classes
        get_classes(self._on_data, self._err)

    def _show_spinner(self, val: bool):
        self.ids.spinner_box.height = "56dp" if val else "0dp"
        self.ids.spinner.active = val

    def _on_data(self, data):
        self._classes = data
        self._show_spinner(False)
        self.ids.count_lbl.text = f"{len(data)} classes"
        self.ids.rv.data = [dict(c) for c in data]

    def create_class(self):
        name = self.ids.class_name_field.text.strip()
        if not name:
            from components.snackbar import show
            show("Enter a class name")
            return
        self.ids.create_btn.disabled = True
        from api.client import create_class
        create_class(name, self._on_created, self._err)

    def _on_created(self, data):
        self.ids.class_name_field.text = ""
        self.ids.create_btn.disabled = False
        from components.snackbar import show
        show(f"Class '{data['name']}' created")
        self.refresh()

    def _open_rename_dialog(self, cls: dict):
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogContentContainer,
            MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText
        from kivymd.uix.textfield import MDTextField, MDTextFieldHintText

        field = MDTextField(mode="outlined", size_hint_y=None, height="52dp")
        field.add_widget(MDTextFieldHintText(text="New class name"))
        field.text = cls.get("name", "")

        def _save(*_):
            new_name = field.text.strip()
            if not new_name:
                return
            dlg.dismiss()
            from api.client import rename_class
            rename_class(cls["id"], new_name,
                         lambda _: self.refresh(), self._err)

        dlg = MDDialog(
            MDDialogHeadlineText(text="Rename Class"),
            MDDialogSupportingText(text=cls.get("name", "")),
            MDDialogContentContainer(field),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Rename"), style="filled",
                         on_release=_save),
            ),
        )
        dlg.open()

    def _confirm_delete(self, cls: dict):
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText

        def _do(*_):
            dlg.dismiss()
            from api.client import delete_class
            delete_class(cls["id"], lambda _: self.refresh(), self._err)

        dlg = MDDialog(
            MDDialogHeadlineText(text="Delete Class"),
            MDDialogSupportingText(
                text=f"Delete '{cls['name']}'? This cannot be undone."),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Delete"), style="filled",
                         on_release=_do),
            ),
        )
        dlg.open()

    def _err(self, msg):
        self._show_spinner(False)
        self.ids.create_btn.disabled = False
        from components.snackbar import show
        show(str(msg))
