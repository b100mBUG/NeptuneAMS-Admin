import json, os

_FILE = os.path.join(os.path.dirname(__file__), "..", ".theme.json")
_DEFAULTS = {"palette": "teal", "style": "Light"}


def load() -> dict:
    try:
        with open(_FILE) as f:
            return {**_DEFAULTS, **json.load(f)}
    except Exception:
        return dict(_DEFAULTS)


def apply(app) -> None:
    prefs = load()
    app.theme_cls.primary_palette = prefs["palette"]
    app.theme_cls.theme_style     = prefs["style"]
