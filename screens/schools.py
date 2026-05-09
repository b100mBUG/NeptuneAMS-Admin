from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivymd.uix.screen import MDScreen
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.divider import MDDivider

Builder.load_file("screens/schools.kv")



class SchoolRow(RecycleDataViewBehavior, MDBoxLayout):
    school_name  = StringProperty()
    school_slug  = StringProperty()
    school_stats = StringProperty()
    status_text  = StringProperty()
    status_color = ObjectProperty((0.13, 0.69, 0.3, 1))
    is_active    = BooleanProperty(True)
    _data = ObjectProperty(allownone=True)

    def refresh_view_attrs(self, rv, index, data):
        self.school_name  = data.get("name", "")
        self.school_slug  = data.get("slug", "")
        self.is_active    = data.get("is_active", True)
        self.status_text  = "Active" if self.is_active else "Inactive"
        self.status_color = (0.13, 0.69, 0.3, 1) if self.is_active else (0.83, 0.18, 0.18, 1)
        admins   = data.get("admin_count", 0)
        teachers = data.get("teacher_count", 0)
        students = data.get("student_count", 0)
        classes  = data.get("class_count", 0)
        self.school_stats = (
            f"{admins} admin{'s' if admins != 1 else ''}  ·  "
            f"{teachers} teacher{'s' if teachers != 1 else ''}  ·  "
            f"{classes} class{'es' if classes != 1 else ''}  ·  "
            f"{students} student{'s' if students != 1 else ''}"
        )
        self._data = data
        return super().refresh_view_attrs(rv, index, data)

    def on_edit(self):
        if not self._data:
            return
        from kivy.app import App
        screen = (App.get_running_app().root
                  .get_screen("main").ids.content_manager
                  .get_screen("schools"))
        screen._open_edit_dialog(self._data)

    def on_payment(self):
        """Jump to the Payments screen pre-selected on this school."""
        if not self._data:
            return
        from kivy.app import App
        main = App.get_running_app().root.get_screen("main")
        pay_screen = main.ids.content_manager.get_screen("payments")
        # pre-select this school then navigate
        pay_screen._sel_school = self._data
        pay_screen.ids.lbl_school_pick.text = self._data.get("name", "")
        pay_screen._load_school_data()
        main.nav_to("payments")

    def on_toggle(self):
        if not self._data:
            return
        from kivy.app import App
        screen = (App.get_running_app().root
                  .get_screen("main").ids.content_manager
                  .get_screen("schools"))
        screen.toggle_school(self._data)


class SchoolsScreen(MDScreen):
    role: str = "platform"

    def refresh(self, *args):
        self.ids.rv.data = []
        self._show_spinner(True)
        from api.client import get_schools
        get_schools(self._on_data, self._err)

    def _show_spinner(self, val: bool):
        self.ids.spinner_box.height = "56dp" if val else "0dp"
        self.ids.spinner.active = val

    def _on_data(self, data):
        self._show_spinner(False)
        self.ids.count_lbl.text = f"{len(data)} schools"
        self.ids.rv.data = list(data)

    def provision(self):
        school_name = self.ids.f_school_name.text.strip()
        school_slug = self.ids.f_school_slug.text.strip()
        admin_name  = self.ids.f_admin_name.text.strip()
        admin_email = self.ids.f_admin_email.text.strip()
        admin_pwd   = self.ids.f_admin_pwd.text.strip()

        if not all([school_name, school_slug, admin_name, admin_email, admin_pwd]):
            from components.snackbar import show
            show("Fill in all fields")
            return
        if len(admin_pwd) < 8:
            from components.snackbar import show
            show("Admin password must be at least 8 characters")
            return

        self.ids.provision_btn.disabled = True
        from api.client import provision_school
        provision_school(
            school_name, school_slug,
            admin_name, admin_email, admin_pwd,
            self._on_provisioned, self._err,
        )

    def _on_provisioned(self, data):
        self.ids.provision_btn.disabled = False
        for fid in ("f_school_name", "f_school_slug",
                    "f_admin_name", "f_admin_email", "f_admin_pwd"):
            self.ids[fid].text = ""
        from components.snackbar import show
        show(f"School provisioned! ID: {data.get('school_id', '')[:8]}…")
        self.refresh()

    def _open_edit_dialog(self, school: dict):
        """Edit school — currently allows resetting the admin password
        and toggling active state. Name/slug changes require DB migration."""
        from kivymd.uix.dialog import (MDDialog, MDDialogHeadlineText,
            MDDialogSupportingText, MDDialogContentContainer,
            MDDialogButtonContainer)
        from kivymd.uix.button import MDButton, MDButtonText, MDButtonIcon
        from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.selectioncontrol import MDSwitch
        from kivy.metrics import dp

        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(14),
            padding=[0, dp(8), 0, 0],
        )

        # School info (read-only display)
        info = MDLabel(
            text=f"Slug: {school.get('slug', '')}",
            font_style="Body", role="medium",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        content.add_widget(info)

        # Active toggle
        active_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(12),
        )
        active_lbl = MDLabel(
            text="Active",
            font_style="Body", role="large",
            adaptive_height=True, size_hint_x=1,
        )
        active_switch = MDSwitch(active=school.get("is_active", True))
        active_row.add_widget(active_lbl)
        active_row.add_widget(active_switch)
        content.add_widget(active_row)

        # New admin password (optional)
        sep = MDLabel(
            text="Reset school admin password (leave blank to keep current):",
            font_style="Body", role="small",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        content.add_widget(sep)

        admin_email_field = MDTextField(
            mode="outlined", size_hint_y=None, height="52dp",
        )
        admin_email_field.add_widget(MDTextFieldHintText(text="Admin email"))
        content.add_widget(admin_email_field)

        new_pwd_field = MDTextField(
            mode="outlined", password=True, size_hint_y=None, height="52dp",
        )
        new_pwd_field.add_widget(MDTextFieldHintText(text="New password (min 8)"))
        content.add_widget(new_pwd_field)

        status_lbl = MDLabel(
            text="", font_style="Body", role="small",
            theme_text_color="Secondary", adaptive_height=True,
        )
        content.add_widget(status_lbl)

        def _save(*_):
            # 1. Toggle active if changed
            new_active = active_switch.active
            if new_active != school.get("is_active", True):
                from api.client import set_school_active
                set_school_active(school["id"], new_active,
                                  lambda _: None, self._err)

            # 2. Register a new admin if email+pwd provided
            email = admin_email_field.text.strip()
            pwd   = new_pwd_field.text.strip()
            if email or pwd:
                if not email or not pwd:
                    status_lbl.text = "Provide both email and password to reset admin"
                    return
                if len(pwd) < 8:
                    status_lbl.text = "Password must be at least 8 characters"
                    return
                # Use provision_school route: we re-provision a new admin
                # (the old admin still exists; this adds a fresh one)
                import httpx, threading
                from api.client import BASE_URL, _h
                def _do():
                    from kivy.clock import Clock
                    try:
                        r = httpx.post(
                            f"{BASE_URL}/auth/admin/register",
                            json={"name": "Admin", "email": email, "password": pwd,
                                  "school_slug": school.get("slug", "")},
                            headers=_h(), timeout=10,
                        )
                        r.raise_for_status()
                        Clock.schedule_once(lambda dt: (
                            self.refresh(),
                            dlg.dismiss(),
                        ))
                    except httpx.HTTPStatusError as exc:
                        try: detail = exc.response.json().get("detail", str(exc))
                        except: detail = str(exc)
                        Clock.schedule_once(lambda dt: setattr(status_lbl, "text", detail))
                    except Exception as exc:
                        Clock.schedule_once(lambda dt: setattr(status_lbl, "text", str(exc)))
                threading.Thread(target=_do, daemon=True).start()
                return

            dlg.dismiss()
            self.refresh()

        dlg = MDDialog(
            MDDialogHeadlineText(text=school.get("name", "Edit School")),
            MDDialogSupportingText(text="School settings"),
            MDDialogContentContainer(content),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: dlg.dismiss()),
                MDButton(MDButtonText(text="Save"), style="filled",
                         on_release=_save),
            ),
        )
        dlg.open()

    def toggle_school(self, school: dict):
        new_state = not school.get("is_active", True)
        from api.client import set_school_active
        set_school_active(
            school["id"], new_state,
            lambda _: self.refresh(),
            self._err,
        )

    def _err(self, msg):
        self._show_spinner(False)
        self.ids.provision_btn.disabled = False
        from components.snackbar import show
        show(str(msg))
