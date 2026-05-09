"""
API client — AttendEase Admin Dashboard.

Roles:
  platform  → /platform/auth  (superadmin, no school context)
  admin     → /auth/login     (school admin, school_slug required)

Every backend endpoint is mapped here.
_dispatch() runs the call on a daemon thread and delivers the result
to the Kivy main thread via Clock.
"""
import threading
import httpx
from typing import Callable

BASE_URL = "http://127.0.0.1:8000"

_token:     str | None = None
_role:      str | None = None   # "platform" | "admin"
_school_id: str | None = None


def set_token(token: str, role: str, school_id: str = "") -> None:
    global _token, _role, _school_id
    _token     = token
    _role      = role
    _school_id = school_id


def clear_token() -> None:
    global _token, _role, _school_id
    _token = _role = _school_id = None


def get_role()      -> str | None: return _role
def get_school_id() -> str | None: return _school_id


def _h() -> dict:
    return {"Authorization": f"Bearer {_token}"} if _token else {}


def _dispatch(fn: Callable, on_success: Callable, on_error: Callable) -> None:
    from kivy.clock import Clock

    def worker():
        try:
            result = fn()
            Clock.schedule_once(lambda dt: on_success(result))
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            Clock.schedule_once(lambda dt: on_error(detail))
        except Exception as exc:
            Clock.schedule_once(lambda dt, exc = exc: on_error(str(exc)))

    threading.Thread(target=worker, daemon=True).start()


def _items(resp) -> list:
    if isinstance(resp, dict):
        return resp.get("items", [])
    return resp if isinstance(resp, list) else []


# ══════════════════════════════════════════════════════════════════════════════
# Auth
# ══════════════════════════════════════════════════════════════════════════════

def platform_login(platform_secret: str, on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/platform/auth",
                       json={"platform_secret": platform_secret}, timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def admin_login(email: str, password: str, school_slug: str,
                on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/auth/login",
                       json={"email": email, "password": password,
                             "school_slug": school_slug}, timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_me(on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/admins/me", headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Platform — schools
# ══════════════════════════════════════════════════════════════════════════════

def get_schools(on_success: Callable, on_error: Callable,
                page: int = 1, page_size: int = 200):
    def call():
        r = httpx.get(f"{BASE_URL}/platform/schools",
                      params={"page": page, "page_size": page_size},
                      headers=_h(), timeout=15)
        r.raise_for_status()
        return _items(r.json())
    _dispatch(call, on_success, on_error)


def provision_school(school_name: str, school_slug: str,
                     admin_name: str, admin_email: str, admin_password: str,
                     on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/platform/schools",
                       json={"school_name": school_name,
                             "school_slug": school_slug,
                             "admin_name":  admin_name,
                             "admin_email": admin_email,
                             "admin_password": admin_password},
                       headers=_h(), timeout=15)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def set_school_active(school_id: str, is_active: bool,
                      on_success: Callable, on_error: Callable):
    def call():
        r = httpx.patch(f"{BASE_URL}/platform/schools/{school_id}/active",
                        json={"is_active": is_active},
                        headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def delete_school(school_id: str, on_success: Callable, on_error: Callable):
    def call():
        r = httpx.delete(f"{BASE_URL}/platform/schools/{school_id}",
                         headers=_h(), timeout=10)
        r.raise_for_status()
        return {}
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Classes
# ══════════════════════════════════════════════════════════════════════════════

def get_classes(on_success: Callable, on_error: Callable,
                page: int = 1, page_size: int = 500):
    def call():
        r = httpx.get(f"{BASE_URL}/classes/",
                      params={"page": page, "page_size": page_size},
                      headers=_h(), timeout=15)
        r.raise_for_status()
        return _items(r.json())
    _dispatch(call, on_success, on_error)


def create_class(name: str, on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/classes/",
                       json={"name": name}, headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def rename_class(class_id: str, name: str, on_success: Callable, on_error: Callable):
    def call():
        r = httpx.patch(f"{BASE_URL}/classes/{class_id}",
                        json={"name": name}, headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def delete_class(class_id: str, on_success: Callable, on_error: Callable):
    def call():
        r = httpx.delete(f"{BASE_URL}/classes/{class_id}",
                         headers=_h(), timeout=10)
        r.raise_for_status()
        return {}
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Teachers
# ══════════════════════════════════════════════════════════════════════════════

def get_teachers(on_success: Callable, on_error: Callable,
                 page: int = 1, page_size: int = 500):
    def call():
        r = httpx.get(f"{BASE_URL}/teachers/",
                      params={"page": page, "page_size": page_size},
                      headers=_h(), timeout=15)
        r.raise_for_status()
        return _items(r.json())
    _dispatch(call, on_success, on_error)


def create_teacher(name: str, email: str, password: str, class_ids: list,
                   on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/auth/teacher/register",
                       json={"name": name, "email": email,
                             "password": password, "class_ids": class_ids},
                       headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def update_teacher_classes(teacher_id: str, class_ids: list,
                           on_success: Callable, on_error: Callable):
    def call():
        r = httpx.patch(f"{BASE_URL}/teachers/{teacher_id}/classes",
                        json={"class_ids": class_ids},
                        headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def delete_teacher(teacher_id: str, on_success: Callable, on_error: Callable):
    def call():
        r = httpx.delete(f"{BASE_URL}/teachers/{teacher_id}/admin",
                         headers=_h(), timeout=10)
        r.raise_for_status()
        return {}
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Students
# ══════════════════════════════════════════════════════════════════════════════

def get_students(class_id: str, on_success: Callable, on_error: Callable,
                 page: int = 1, page_size: int = 1000):
    def call():
        r = httpx.get(f"{BASE_URL}/classes/{class_id}/students/",
                      params={"page": page, "page_size": page_size},
                      headers=_h(), timeout=15)
        r.raise_for_status()
        return _items(r.json())
    _dispatch(call, on_success, on_error)


def create_student(adm: str, name: str, c_id: str,
                   on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/classes/{c_id}/students/",
                       json={"id": adm, "name": name},
                       headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def edit_student(class_id: str, student_id: str, name: str,
                 on_success: Callable, on_error: Callable):
    def call():
        r = httpx.patch(f"{BASE_URL}/classes/{class_id}/students/{student_id}",
                        json={"name": name}, headers=_h(), timeout=10)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def delete_student(class_id: str, student_id: str,
                   on_success: Callable, on_error: Callable):
    def call():
        r = httpx.delete(f"{BASE_URL}/classes/{class_id}/students/{student_id}",
                         headers=_h(), timeout=10)
        r.raise_for_status()
        return {}
    _dispatch(call, on_success, on_error)


def bulk_enroll_json(class_id: str, students: list,
                     on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(f"{BASE_URL}/classes/{class_id}/students/import",
                       json={"students": students},
                       headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def bulk_enroll_file(class_id: str, filename: str, data: bytes,
                     on_success: Callable, on_error: Callable):
    def call():
        ct = ("text/csv" if filename.lower().endswith(".csv") else
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r = httpx.post(f"{BASE_URL}/classes/{class_id}/students/import-file",
                       files={"file": (filename, data, ct)},
                       headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Attendance
# ══════════════════════════════════════════════════════════════════════════════

def get_class_attendance(class_id: str, period: str,
                         on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/attendance/class/{class_id}",
                      params={"period": period}, headers=_h(), timeout=15)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Analysis  (new /analysis/* endpoints)
# ══════════════════════════════════════════════════════════════════════════════

def get_class_analysis(class_id: str, start: str, end: str,
                       on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/analysis/classes/{class_id}",
                      params={"start": start, "end": end},
                      headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_student_analysis(student_id: str, start: str, end: str,
                         on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/analysis/students/{student_id}",
                      params={"start": start, "end": end},
                      headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_teacher_analysis(teacher_id: str, start: str, end: str,
                         on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/analysis/teachers/{teacher_id}",
                      params={"start": start, "end": end},
                      headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_all_teachers_analysis(start: str, end: str,
                               on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/analysis/teachers",
                      params={"start": start, "end": end},
                      headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_school_overview_analysis(school_id: str, start: str, end: str,
                                  on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(f"{BASE_URL}/analysis/schools/{school_id}/overview",
                      params={"start": start, "end": end},
                      headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Reports — file downloads (all return raw bytes via on_success)
# ══════════════════════════════════════════════════════════════════════════════

def _download(url: str, params: dict, on_success: Callable, on_error: Callable):
    """Generic binary download helper."""
    def call():
        r = httpx.get(url, params=params, headers=_h(), timeout=60)
        r.raise_for_status()
        return r.content
    _dispatch(call, on_success, on_error)


def download_class_attendance_csv(class_id: str, start: str, end: str,
                                   period: str | None,
                                   on_success: Callable, on_error: Callable):
    params = {"start": start, "end": end}
    if period:
        params["period"] = period
    _download(f"{BASE_URL}/reports/classes/{class_id}/attendance.csv",
              params, on_success, on_error)


def download_class_attendance_pdf(class_id: str, start: str, end: str,
                                   period: str | None,
                                   on_success: Callable, on_error: Callable):
    params = {"start": start, "end": end}
    if period:
        params["period"] = period
    _download(f"{BASE_URL}/reports/classes/{class_id}/attendance.pdf",
              params, on_success, on_error)


def download_class_analysis_pdf(class_id: str, start: str, end: str,
                                 on_success: Callable, on_error: Callable):
    _download(f"{BASE_URL}/reports/classes/{class_id}/analysis.pdf",
              {"start": start, "end": end}, on_success, on_error)


def download_student_analysis_pdf(student_id: str, start: str, end: str,
                                   on_success: Callable, on_error: Callable):
    _download(f"{BASE_URL}/reports/students/{student_id}/analysis.pdf",
              {"start": start, "end": end}, on_success, on_error)


def download_teacher_activity_pdf(teacher_id: str, start: str, end: str,
                                   on_success: Callable, on_error: Callable):
    _download(f"{BASE_URL}/reports/teachers/{teacher_id}/activity.pdf",
              {"start": start, "end": end}, on_success, on_error)


def download_teacher_comparison_pdf(start: str, end: str,
                                     on_success: Callable, on_error: Callable):
    _download(f"{BASE_URL}/reports/teachers/comparison.pdf",
              {"start": start, "end": end}, on_success, on_error)


def download_school_overview_pdf(school_id: str, start: str, end: str,
                                  on_success: Callable, on_error: Callable):
    _download(f"{BASE_URL}/reports/schools/{school_id}/overview.pdf",
              {"start": start, "end": end}, on_success, on_error)


# ══════════════════════════════════════════════════════════════════════════════
# Payments & Subscriptions
# ══════════════════════════════════════════════════════════════════════════════

def initiate_payment(school_id: str, email: str,
                     on_success: Callable, on_error: Callable):
    def call():
        r = httpx.post(
            f"{BASE_URL}/platform/schools/{school_id}/payments/initiate",
            json={"email": email},
            headers=_h(), timeout=20,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def verify_payment(school_id: str, reference: str,
                   on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(
            f"{BASE_URL}/platform/schools/{school_id}/payments/verify",
            params={"reference": reference},
            headers=_h(), timeout=20,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_school_subscription(school_id: str,
                             on_success: Callable, on_error: Callable):
    def call():
        r = httpx.get(
            f"{BASE_URL}/platform/schools/{school_id}/subscription",
            headers=_h(), timeout=15,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_school_payment_logs(school_id: str,
                             on_success: Callable, on_error: Callable,
                             limit: int = 50, offset: int = 0):
    def call():
        r = httpx.get(
            f"{BASE_URL}/platform/schools/{school_id}/payments/logs",
            params={"limit": limit, "offset": offset},
            headers=_h(), timeout=15,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_all_payment_logs(on_success: Callable, on_error: Callable,
                         limit: int = 100, offset: int = 0):
    def call():
        r = httpx.get(
            f"{BASE_URL}/platform/payments/logs",
            params={"limit": limit, "offset": offset},
            headers=_h(), timeout=15,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def admin_initiate_payment(email: str, on_success: Callable, on_error: Callable):
    """School admin initiates payment for their own school."""
    def call():
        r = httpx.post(
            f"{BASE_URL}/schools/me/payments/initiate",
            json={"email": email},
            headers=_h(), timeout=20,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def admin_verify_payment(reference: str, on_success: Callable, on_error: Callable):
    """School admin verifies their own payment."""
    def call():
        r = httpx.get(
            f"{BASE_URL}/schools/me/payments/verify",
            params={"reference": reference},
            headers=_h(), timeout=20,
        )
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_my_subscription(on_success: Callable, on_error: Callable):
    """School admin — own subscription status."""
    def call():
        r = httpx.get(f"{BASE_URL}/schools/me/subscription",
                      headers=_h(), timeout=15)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)


def get_my_payment_logs(on_success: Callable, on_error: Callable,
                        limit: int = 50):
    """School admin — own payment history."""
    def call():
        r = httpx.get(f"{BASE_URL}/schools/me/payments/logs",
                      params={"limit": limit},
                      headers=_h(), timeout=15)
        r.raise_for_status()
        return r.json()
    _dispatch(call, on_success, on_error)
