from kivy.metrics import dp
def show(message: str, duration: int = 3) -> None:
    from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
    sb = MDSnackbar(
        MDSnackbarText(text=message),
        y=dp(24), pos_hint={"center_x": 0.5},
        size_hint_x=0.5, duration=duration,
    )
    sb.open()
