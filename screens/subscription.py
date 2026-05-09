"""
Subscription screen — school admin view.
Shows the school's own subscription status, payment history,
and allows the admin to initiate/verify payments directly.
"""
import webbrowser

from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen

Builder.load_file("screens/subscription.kv")


def _fmt_kes(amount: int) -> str:
    return f"KES {amount:,}"


def _status_color(status: str) -> tuple:
    return {
        "success": (0.13, 0.69, 0.3, 1),
        "failed":  (0.83, 0.18, 0.18, 1),
        "pending": (0.95, 0.61, 0.07, 1),
    }.get(status.lower(), (0.5, 0.5, 0.5, 1))


class SubLogRow(RecycleDataViewBehavior, MDBoxLayout):
    ref_text      = StringProperty()
    amount_text   = StringProperty()
    students_text = StringProperty()
    status_text   = StringProperty()
    date_text     = StringProperty()
    status_color  = ObjectProperty((0.5, 0.5, 0.5, 1))

    def refresh_view_attrs(self, rv, index, data):
        self.ref_text      = data.get("paystack_reference", "")[-16:]
        self.amount_text   = _fmt_kes(data.get("amount", 0))
        self.students_text = f"{data.get('student_count', 0)} students"
        self.status_text   = data.get("status", "").capitalize()
        self.status_color  = _status_color(data.get("status", ""))
        paid_at = data.get("paid_at") or data.get("created_at", "")
        self.date_text = paid_at[:10] if paid_at else "—"
        return super().refresh_view_attrs(rv, index, data)


class SubscriptionScreen(MDScreen):
    role:         str = "admin"
    _pending_ref: str = ""

    def refresh(self, *args):
        self._reset_ui()
        self._set_loading(True)
        from api.client import get_my_subscription, get_my_payment_logs
        get_my_subscription(self._on_sub, self._err)
        get_my_payment_logs(self._on_logs, self._err)

    def _reset_ui(self):
        for lid in ("lbl_status", "lbl_dates", "lbl_students",
                    "lbl_amount", "lbl_days", "lbl_pay_status"):
            w = self.ids.get(lid)
            if w:
                w.text = "—"
        self.ids.logs_rv.data = []

    def _on_sub(self, data: dict):
        self._set_loading(False)

        has_sub = data.get("subscription_end") is not None
        expired = data.get("is_expired", True)
        days    = data.get("days_remaining")

        if not has_sub:
            status_txt = "No active subscription"
            col        = (0.83, 0.18, 0.18, 1)
            days_txt   = "—"
        elif expired:
            status_txt = f"Expired on {data.get('subscription_end', '')}"
            col        = (0.83, 0.18, 0.18, 1)
            days_txt   = "Expired"
        else:
            status_txt = "Active"
            col        = (0.13, 0.69, 0.3, 1)
            days_txt   = f"{days} days remaining"

        self.ids.lbl_status.text  = status_txt
        self.ids.lbl_status.color = col
        self.ids.lbl_days.text    = days_txt
        self.ids.lbl_dates.text   = (
            f"{data.get('subscription_start', '—')}  to "
            f"{data.get('subscription_end', '—')}"
        )
        self.ids.lbl_students.text = f"{data.get('student_count_at_payment', 0)} students"
        self.ids.lbl_amount.text   = _fmt_kes(data.get("amount_paid", 0))

    def _on_logs(self, data: list):
        self._set_loading(False)
        self.ids.logs_rv.data = list(data)

    # ── Payment initiation ────────────────────────────────────────────────────

    def initiate_payment(self):
        email = self.ids.billing_email.text.strip()
        if not email or "@" not in email:
            from components.snackbar import show
            show("Enter a valid billing email")
            return

        self.ids.btn_pay.disabled = True
        self.ids.lbl_pay_status.text = "Initiating payment…"

        from api.client import admin_initiate_payment
        admin_initiate_payment(email, self._on_initiated, self._pay_err)

    def _on_initiated(self, data: dict):
        self.ids.btn_pay.disabled = False
        url = data.get("authorization_url", "")
        ref = data.get("reference", "")
        amt = _fmt_kes(data.get("amount", 0))
        cnt = data.get("student_count", 0)
        self._pending_ref = ref

        self.ids.lbl_pay_status.text = (
            f"Checkout opened — {amt} for {cnt} students\n"
            f"Reference: {ref}"
        )
        self.ids.btn_verify.disabled = False

        from utils.callback_server import start_callback_server
        start_callback_server(on_reference=self._on_callback_reference)

        if url:
            webbrowser.open(url)
            from components.snackbar import show
            show("Paystack checkout opened — verifying automatically on return")

    def _on_callback_reference(self, reference: str):
        self.ids.verify_ref.text = reference
        self._pending_ref = reference
        self.ids.lbl_pay_status.text = f"Payment returned — verifying…"
        self.verify_payment()

    def verify_payment(self):
        ref = self.ids.verify_ref.text.strip() or self._pending_ref
        if not ref:
            from components.snackbar import show
            show("Enter the Paystack reference to verify")
            return

        self.ids.btn_verify.disabled = True
        self.ids.lbl_pay_status.text = "Verifying…"

        from api.client import admin_verify_payment
        admin_verify_payment(ref, self._on_verified, self._pay_err)

    def _on_verified(self, data: dict):
        self.ids.btn_verify.disabled = False
        success = data.get("success", False)
        msg = data.get("message", "")
        self.ids.lbl_pay_status.text = ("✓ " if success else "✗ ") + msg
        from components.snackbar import show
        show(msg)
        if success:
            self.refresh()

    def _pay_err(self, msg: str):
        self.ids.btn_pay.disabled    = False
        self.ids.btn_verify.disabled = False
        self.ids.lbl_pay_status.text = f"Error: {msg}"
        from components.snackbar import show
        show(str(msg))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_loading(self, val: bool):
        self.ids.spinner_box.height = "48dp" if val else "0dp"
        self.ids.spinner.active = val

    def _err(self, msg: str):
        self._set_loading(False)
        from components.snackbar import show
        show(str(msg))
