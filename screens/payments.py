"""
Platform Payments screen.

Two tabs:
  • "By School"   — pick a school, see its subscription status, initiate/verify
                    a payment, view its payment history
  • "All Logs"    — paginated log of every payment across all schools
"""
import webbrowser
from datetime import date

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/payments.kv")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_kes(amount: int) -> str:
    """Format integer KES with thousands separator."""
    return f"KES {amount:,}"


def _status_color(status: str) -> tuple:
    return {
        "success": (0.13, 0.69, 0.3, 1),
        "failed":  (0.83, 0.18, 0.18, 1),
        "pending": (0.95, 0.61, 0.07, 1),
    }.get(status.lower(), (0.5, 0.5, 0.5, 1))


def _sub_color(is_expired: bool, has_sub: bool) -> tuple:
    if not has_sub:
        return (0.83, 0.18, 0.18, 1)
    return (0.83, 0.18, 0.18, 1) if is_expired else (0.13, 0.69, 0.3, 1)


# ── RecycleView row for payment logs ─────────────────────────────────────────

class PaymentLogRow(RecycleDataViewBehavior, MDBoxLayout):
    ref_text     = StringProperty()
    amount_text  = StringProperty()
    students_text= StringProperty()
    status_text  = StringProperty()
    date_text    = StringProperty()
    school_text  = StringProperty()   # only shown in "all logs" tab
    status_color = ObjectProperty((0.5, 0.5, 0.5, 1))
    show_school  = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        self.ref_text      = data.get("paystack_reference", "")[-16:]
        self.amount_text   = _fmt_kes(data.get("amount", 0))
        self.students_text = f"{data.get('student_count', 0)} students"
        self.status_text   = data.get("status", "").capitalize()
        self.status_color  = _status_color(data.get("status", ""))
        self.school_text   = data.get("school_name", data.get("school_id", ""))
        self.show_school   = data.get("_show_school", False)
        paid_at = data.get("paid_at") or data.get("created_at", "")
        self.date_text = paid_at[:10] if paid_at else "—"
        return super().refresh_view_attrs(rv, index, data)


# ── Main screen ───────────────────────────────────────────────────────────────

class PaymentsScreen(MDScreen):
    role: str = "platform"

    _schools:     list = []
    _sel_school:  dict | None = None
    _sub:         dict | None = None
    _pending_ref: str = ""

    def refresh(self, *args):
        self._schools    = []
        self._sel_school = None
        self._sub        = None
        self._pending_ref = ""
        self._clear_sub_ui()
        self.ids.school_logs_rv.data = []
        self.ids.all_logs_rv.data    = []
        self.ids.lbl_school_pick.text = "Select a school"

        from api.client import get_schools, get_all_payment_logs
        get_schools(self._on_schools, self._err)
        self._set_all_loading(True)
        get_all_payment_logs(self._on_all_logs, self._err)

    # ── School picker ─────────────────────────────────────────────────────

    def _on_schools(self, data):
        self._schools = data

    def open_school_menu(self):
        if not self._schools:
            from components.snackbar import show
            show("No schools loaded yet")
            return
        from kivymd.uix.menu import MDDropdownMenu
        self._menu = MDDropdownMenu(
            caller=self.ids.btn_school_pick,
            items=[
                {"text": s["name"], "on_release": lambda s=s: self._pick_school(s)}
                for s in self._schools
            ],
        )
        self._menu.open()

    def _pick_school(self, school: dict):
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self._sel_school = school
        self.ids.lbl_school_pick.text = school["name"]
        self._load_school_data()

    def _load_school_data(self):
        if not self._sel_school:
            return
        sid = self._sel_school["id"]
        self._clear_sub_ui()
        self.ids.school_logs_rv.data = []
        self._set_school_loading(True)

        from api.client import get_school_subscription, get_school_payment_logs
        get_school_subscription(sid, self._on_sub, self._err)
        get_school_payment_logs(sid, self._on_school_logs, self._err)

    # ── Subscription display ──────────────────────────────────────────────

    def _on_sub(self, data: dict):
        self._set_school_loading(False)
        self._sub = data

        has_sub = data.get("subscription_end") is not None
        expired = data.get("is_expired", True)
        days    = data.get("days_remaining")

        if not has_sub:
            status_txt  = "No subscription"
            sub_color   = (0.83, 0.18, 0.18, 1)
        elif expired:
            status_txt  = f"Expired — {data.get('subscription_end', '')}"
            sub_color   = (0.83, 0.18, 0.18, 1)
        else:
            status_txt  = f"Active · {days} days remaining"
            sub_color   = (0.13, 0.69, 0.3, 1)

        self.ids.lbl_sub_status.text  = status_txt
        self.ids.lbl_sub_status.color = sub_color
        self.ids.lbl_sub_dates.text   = (
            f"{data.get('subscription_start', '—')}  →  "
            f"{data.get('subscription_end', '—')}"
        )
        self.ids.lbl_sub_students.text = (
            f"{data.get('student_count_at_payment', 0)} students at last payment"
        )
        self.ids.lbl_sub_amount.text = (
            _fmt_kes(data.get("amount_paid", 0)) + " last paid"
        )
        self.ids.sub_card.opacity = 1

    def _clear_sub_ui(self):
        for lid in ("lbl_sub_status", "lbl_sub_dates",
                    "lbl_sub_students", "lbl_sub_amount"):
            w = self.ids.get(lid)
            if w:
                w.text = "—"
        if self.ids.get("sub_card"):
            self.ids.sub_card.opacity = 0.4
        self.ids.billing_email.text = ""
        self.ids.lbl_pay_status.text = ""

    # ── Payment initiation ────────────────────────────────────────────────

    def initiate_payment(self):
        if not self._sel_school:
            from components.snackbar import show
            show("Select a school first")
            return
        email = self.ids.billing_email.text.strip()
        if not email or "@" not in email:
            from components.snackbar import show
            show("Enter a valid billing email")
            return

        self.ids.btn_pay.disabled = True
        self.ids.lbl_pay_status.text = "Initiating payment…"
        from api.client import initiate_payment
        initiate_payment(
            self._sel_school["id"], email,
            self._on_initiated, self._pay_err,
        )

    def _on_initiated(self, data: dict):
        self.ids.btn_pay.disabled = False
        url = data.get("authorization_url", "")
        ref = data.get("reference", "")
        amt = _fmt_kes(data.get("amount", 0))
        cnt = data.get("student_count", 0)
        self._pending_ref = ref

        self.ids.lbl_pay_status.text = (
            f"Paystack checkout opened — {amt} for {cnt} students\n"
            f"Reference: {ref}"
        )
        self.ids.btn_verify.disabled = False

        # Start local callback server so Paystack can redirect back
        from utils.callback_server import start_callback_server
        start_callback_server(on_reference=self._on_callback_reference)

        if url:
            webbrowser.open(url)
            from components.snackbar import show
            show("Paystack checkout opened — verifying automatically on return")

    def _on_callback_reference(self, reference: str):
        """Called automatically when Paystack redirects to the local server."""
        self.ids.verify_ref.text = reference
        self._pending_ref = reference
        self.ids.lbl_pay_status.text = f"Payment returned — verifying {reference}…"
        self.verify_payment()

    def verify_payment(self):
        ref = self.ids.verify_ref.text.strip() or self._pending_ref
        if not ref:
            from components.snackbar import show
            show("Enter the Paystack reference to verify")
            return
        if not self._sel_school:
            from components.snackbar import show
            show("Select a school first")
            return

        self.ids.btn_verify.disabled = True
        self.ids.lbl_pay_status.text = "Verifying…"
        from api.client import verify_payment
        verify_payment(
            self._sel_school["id"], ref,
            self._on_verified, self._pay_err,
        )

    def _on_verified(self, data: dict):
        self.ids.btn_verify.disabled = False
        success = data.get("success", False)
        msg = data.get("message", "")
        self.ids.lbl_pay_status.text = ("✓ " if success else "✗ ") + msg
        from components.snackbar import show
        show(msg)
        if success:
            self._load_school_data()

    def _pay_err(self, msg: str):
        self.ids.btn_pay.disabled    = False
        self.ids.btn_verify.disabled = False
        self.ids.lbl_pay_status.text = f"Error: {msg}"
        from components.snackbar import show
        show(str(msg))

    # ── School payment logs ───────────────────────────────────────────────

    def _on_school_logs(self, data: list):
        self._set_school_loading(False)
        rows = [dict(r, _show_school=False) for r in data]
        self.ids.school_logs_rv.data = rows

    # ── All logs tab ──────────────────────────────────────────────────────

    def _on_all_logs(self, data: list):
        self._set_all_loading(False)
        rows = [dict(r, _show_school=True) for r in data]
        self.ids.all_logs_rv.data = rows

    # ── Spinners ──────────────────────────────────────────────────────────

    def _set_school_loading(self, val: bool):
        self.ids.school_spinner_box.height = "48dp" if val else "0dp"
        self.ids.school_spinner.active = val

    def _set_all_loading(self, val: bool):
        self.ids.all_spinner_box.height = "48dp" if val else "0dp"
        self.ids.all_spinner.active = val

    def _err(self, msg: str):
        self._set_school_loading(False)
        self._set_all_loading(False)
        from components.snackbar import show
        show(str(msg))
