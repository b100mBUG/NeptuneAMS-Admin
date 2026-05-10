from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.widget import Widget
from kivymd.uix.dialog import MDDialog, MDDialogIcon, MDDialogHeadlineText, MDDialogButtonContainer, MDDialogContentContainer
from kivymd.uix.button import MDButton, MDButtonText
from kivy.metrics import dp, sp
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
import asyncio
import webbrowser
import urllib.parse
from kivymd.app import MDApp

Builder.load_file("screens/login.kv")


class AdminLoginScreen(MDScreen):
    _mode: str = "admin"

    def on_enter(self, *args):
        # Always reset form state when entering — fixes spinner persisting after logout
        self.ids.login_btn.disabled = False
        self.ids.spinner.active     = False
        for fid in ("email_field", "password_field",
                    "school_slug_field", "secret_field"):
            self.ids[fid].text = ""

        form = self.ids.form_box
        form.opacity = 0
        Clock.schedule_once(
            lambda dt: Animation(opacity=1, duration=0.35, t="out_quad").start(form),
            0.05,
        )
        self.carousel_event = Clock.schedule_interval(self.auto_scroll, 5)

    def on_leave(self, *args):
        if hasattr(self, "carousel_event"):
            self.carousel_event.cancel()

    def auto_scroll(self, dt):
        carousel = self.ids.carousel

        if carousel.index is None:
            return

        next_index = (carousel.index + 1) % len(carousel.slides)
        carousel.load_slide(carousel.slides[next_index])
    
    def whatsapp_form(self):

        self.phone_number = MDTextField(MDTextFieldHintText(text = "Your WhatsApp number: "), input_filter="int")
        self.wa_message = MDTextField(MDTextFieldHintText(text = "Your Message: "))

        cont = MDDialogContentContainer(orientation = "vertical", spacing = dp(10))

        cont.add_widget(self.phone_number)
        cont.add_widget(self.wa_message)
        cont.add_widget(Widget())

        self.wa_dialog = MDDialog(
            MDDialogIcon(icon = "whatsapp"),
            MDDialogHeadlineText(text = "Text Us On WhatsApp!"),
            cont,
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(
                        text = "CANCEL",
                        theme_text_color = "Custom",
                        text_color = "white"
                    ),
                    theme_bg_color = "Custom",
                    md_bg_color = "red",
                    on_release = lambda x: self.wa_dialog.dismiss()
                ),
                MDButton(
                    MDButtonText(
                        text = "SEND",
                        theme_text_color = "Custom",
                        text_color = "white"
                    ),
                    theme_bg_color = "Custom",
                    md_bg_color = "green",
                    on_release = lambda x: self.send_to_whatsapp()
                ),
                spacing = dp(10)
            ),
            auto_dismiss = False
        )

        self.wa_dialog.open()
    
    def email_form(self):

        self.email_address = MDTextField(MDTextFieldHintText(text = "Your Email Address: "))
        self.email_message = MDTextField(MDTextFieldHintText(text = "Your Message: "))

        cont = MDDialogContentContainer(orientation = "vertical", spacing = dp(10))

        cont.add_widget(self.email_address)
        cont.add_widget(self.email_message)
        cont.add_widget(Widget())

        self.email_dialog = MDDialog(
            MDDialogIcon(icon = "gmail"),
            MDDialogHeadlineText(text = "Reach Us Via Email!"),
            cont,
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(
                        text = "CANCEL",
                        theme_text_color = "Custom",
                        text_color = "white"
                    ),
                    theme_bg_color = "Custom",
                    md_bg_color = "red",
                    on_release = lambda x: self.email_dialog.dismiss()
                ),
                MDButton(
                    MDButtonText(
                        text = "SEND",
                        theme_text_color = "Custom",
                        text_color = "white"
                    ),
                    theme_bg_color = "Custom",
                    md_bg_color = "green",
                    on_release = lambda x: self.send_to_email()
                ),
                spacing = dp(10)
            ),
            auto_dismiss = False
        )

        self.email_dialog.open()
        

    def send_to_whatsapp(self):
        sender = self.phone_number.text.strip()
        receiver = "254768724595"  # use international format (Kenya = 254)
        message = self.wa_message.text.strip()

        if not sender:
            show_error("You must input sending number")
            return

        if not message:
            show_error("You must provide message to send")
            return

        encoded_message = urllib.parse.quote(message)

        wa_url = f"https://wa.me/{receiver}?text={encoded_message}"

        webbrowser.open(wa_url)
        show_success("Redirecting to WhatsApp...")
    
    def send_to_email(self):
        sender = self.email_address.text.strip()
        receiver = "werecastro2006@gmail.com"
        message = self.email_message.text.strip()

        if not sender:
            show_error("You must input sender email")
            return

        if not message:
            show_error("You must provide message to send")
            return

        subject = "NeptunePCS Message"
        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(message)

        email_url = f"mailto:{receiver}?subject={encoded_subject}&body={encoded_body}"

        webbrowser.open(email_url)
        show_success("Opening email client...")

    def set_mode(self, mode: str):
        self._mode = mode
        is_platform = mode == "platform"
        self.ids.slug_row.opacity   = 0 if is_platform else 1
        self.ids.slug_row.height    = "0dp" if is_platform else "56dp"
        self.ids.email_row.opacity  = 0 if is_platform else 1
        self.ids.email_row.height   = "0dp" if is_platform else "56dp"
        self.ids.pwd_row.opacity    = 0 if is_platform else 1
        self.ids.pwd_row.height     = "0dp" if is_platform else "56dp"
        self.ids.secret_row.opacity = 1 if is_platform else 0
        self.ids.secret_row.height  = "56dp" if is_platform else "0dp"
        self.ids.panel_subtitle.text = (
            "Platform Admin" if is_platform else "School Admin"
        )
        self.ids.panel_desc.text = (
            "Manage all schools.\nProvision new tenants.\nControl platform access."
            if is_platform else
            "Manage your school.\nMonitor attendance.\nOversee everything."
        )

    def do_login(self):
        self.ids.login_btn.disabled = True
        self.ids.spinner.active     = True

        if self._mode == "platform":
            secret = self.ids.secret_field.text.strip()
            if not secret:
                self._on_error("Enter the platform key")
                return
            from api.client import platform_login
            platform_login(secret, self._on_platform_success, self._on_error)
        else:
            email = self.ids.email_field.text.strip()
            pwd   = self.ids.password_field.text.strip()
            slug  = self.ids.school_slug_field.text.strip()
            if not (email and pwd and slug):
                self._on_error("Please fill in all fields")
                return
            from api.client import admin_login
            admin_login(email, pwd, slug, self._on_admin_success, self._on_error)

    def _on_platform_success(self, data):
        if data.get("role") != "platform":
            self._on_error("Invalid platform credentials.")
            return
        from api.client import set_token
        from utils.session import save
        set_token(data["access_token"], "platform", "")
        save(data["access_token"], "platform")
        self._go_main(role="platform", user={},
                      school_id="", school_name="Platform")

    def _on_admin_success(self, data):
        if data.get("role") != "admin":
            self._on_error("Only admins can access.")
            return
        from api.client import set_token, get_me
        set_token(data["access_token"], "admin", data.get("school_id", ""))
        get_me(lambda user: self._on_got_me(data, user), self._on_error)

    def _on_got_me(self, token_data, user):
        from utils.session import save
        save(
            token_data["access_token"], "admin", user,
            token_data.get("school_id", ""),
            token_data.get("school_name", ""),
        )
        self._go_main(
            role="admin", user=user,
            school_id=token_data.get("school_id", ""),
            school_name=token_data.get("school_name", ""),
        )

    def _go_main(self, role, user, school_id, school_name):
        main = self.manager.get_screen("main")
        main.role        = role
        main.user        = user
        main.school_name = school_name
        main.school_id = school_id
        self.manager.current = "main"

    def _on_error(self, msg):
        self.ids.login_btn.disabled = False
        self.ids.spinner.active     = False
        from components.snackbar import show
        show(str(msg))
