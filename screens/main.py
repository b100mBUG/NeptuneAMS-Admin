from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/main.kv")


class MainScreen(MDScreen):
    role:        str  = "admin"   # "admin" | "platform"
    user:        dict = {}
    school_name: str  = ""
    school_id:   str  = ""
    _current:    str  = ""

    # ── Sections visible per role ─────────────────────────────────────────
    _ADMIN_SECTIONS    = ("overview", "classes", "teachers", "students",
                          "attendance", "analytics", "reports", "subscription")
    _PLATFORM_SECTIONS = ("schools", "platform_reports", "payments")

    def on_enter(self, *args):
        name = self.user.get("name", "") if self.user else "King Kastro"
        self.ids.drawer_name.text  = (
            name or ("Platform Admin" if self.role == "platform" else "Admin"))
        self.ids.drawer_email.text  = self.user.get("email", "") if self.user else "werecastro2006@gmail.com"
        self.ids.drawer_school.text = (
            "Platform Management" if self.role == "platform" else self.school_name)

        self._sync_nav()
        self.ids.nav_drawer.set_state("open")

        default = "schools" if self.role == "platform" else "overview"
        self._go(default)

    def _sync_nav(self):
        is_platform = self.role == "platform"
        show  = lambda w: setattr(w, "height", "56dp") or setattr(w, "opacity", 1)
        hide  = lambda w: setattr(w, "height", "0dp")  or setattr(w, "opacity", 0)

        for item_id, platform_only in [
            ("nav_schools",          True),
            ("nav_platform_reports", True),
            ("nav_payments",         True),
            ("nav_overview",         False),
            ("nav_classes",          False),
            ("nav_teachers",         False),
            ("nav_students",         False),
            ("nav_attendance",       False),
            ("nav_analytics",        False),
            ("nav_reports",          False),
            ("nav_subscription",     False),
        ]:
            w = self.ids[item_id]
            (show if (is_platform == platform_only) else hide)(w)

    def _go(self, section: str):
        if self._current == section:
            return
        self._current = section
        self.ids.content_manager.current = section
        screen = self.ids.content_manager.get_screen(section)
        if hasattr(screen, "role"):
            screen.role = self.role
        if hasattr(screen, "school_id"):
            screen.school_id = self.school_id
        if hasattr(screen, "user"):
            screen.user = self.user
        if hasattr(screen, "refresh"):
            screen.refresh()

    def nav_to(self, section: str):
        self._go(section)

    def do_logout(self):
        from utils.session import clear
        from api.client import clear_token
        clear()
        clear_token()
        self._current = ""
        self.manager.current = "login"
