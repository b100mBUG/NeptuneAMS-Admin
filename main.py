import os
os.environ.setdefault("KIVY_ORIENTATION", "landscape")


from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivy.uix.screenmanager import NoTransition

from screens.login           import AdminLoginScreen
from screens.main            import MainScreen
from screens.overview        import OverviewScreen
from screens.schools         import SchoolsScreen
from screens.classes         import ClassesScreen
from screens.teachers        import TeachersScreen
from screens.students        import StudentsScreen
from screens.attendance      import AttendanceViewScreen
from screens.analytics       import AnalyticsScreen
from screens.reports         import ReportsScreen
from screens.platform_reports import PlatformReportsScreen
from screens.payments      import PaymentsScreen
from screens.subscription  import SubscriptionScreen


class AdminApp(MDApp):

    def build(self):
        self.title = "NeptuneAMS"
        self.theme_cls.dynamic_color = False

        from theme.manager import apply
        apply(self)

        sm = MDScreenManager(transition=NoTransition())
        sm.add_widget(AdminLoginScreen(name="login"))

        main = MainScreen(name="main")
        sm.add_widget(main)

        cm = main.ids.content_manager
        for screen in [
            # Admin screens
            OverviewScreen(name="overview"),
            ClassesScreen(name="classes"),
            TeachersScreen(name="teachers"),
            StudentsScreen(name="students"),
            AttendanceViewScreen(name="attendance"),
            AnalyticsScreen(name="analytics"),
            ReportsScreen(name="reports"),
            # Platform screens
            SchoolsScreen(name="schools"),
            PlatformReportsScreen(name="platform_reports"),
            PaymentsScreen(name="payments"),
            # Admin screens (subscription view)
            SubscriptionScreen(name="subscription"),
        ]:
            cm.add_widget(screen)

        # Restore session
        from utils.session import load
        from api.client import set_token
        session = load()
        token   = session["token"]
        role    = session["role"]
        if token and role:
            set_token(token, role, session.get("school_id", ""))
            main.role        = role
            main.user        = session.get("user", {})
            main.school_name = session.get("school_name", "")
            main.school_id   = session.get("school_id", "")
            sm.current = "main"
        else:
            sm.current = "login"

        return sm


if __name__ == "__main__":
    AdminApp().run()
