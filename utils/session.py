import json, os

_FILE = os.path.join(os.path.dirname(__file__), "..", ".session.json")
_cache: dict = {}


def _load():
    global _cache
    try:
        with open(_FILE) as f:
            _cache = json.load(f)
    except Exception:
        _cache = {}


def _persist():
    with open(_FILE, "w") as f:
        json.dump(_cache, f)


def save(token: str, role: str, user: dict = None,
         school_id: str = "", school_name: str = "") -> None:
    _cache["token"]       = token
    _cache["role"]        = role
    _cache["user"]        = user or {}
    _cache["school_id"]   = school_id
    _cache["school_name"] = school_name
    _persist()


def load() -> dict:
    _load()
    return {
        "token":       _cache.get("token"),
        "role":        _cache.get("role"),
        "user":        _cache.get("user", {}),
        "school_id":   _cache.get("school_id", ""),
        "school_name": _cache.get("school_name", ""),
    }


def clear() -> None:
    global _cache
    _cache = {}
    try:
        os.remove(_FILE)
    except Exception:
        pass
