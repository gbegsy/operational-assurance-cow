from pathlib import Path
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

BASE = Path(__file__).parent

SITE_OPTIONS = [
    "Dimlington", "Cleeton", "Ravenspurn North", "Northern NUIs",
    "Bacton", "Leman 27BC", "Southern NUIs"
]
TEAM_OPTIONS = [
    "Dimlington", "Cleeton", "Ravenspurn North", "Northern NUIs",
    "Bacton", "Leman 27BC", "Southern NUIs"
]

_original_st_text_input = st.text_input
_original_dg_text_input = DeltaGenerator.text_input


def _dropdown(container, label, options, key=None):
    return container.selectbox(label, ["Select..."] + options, index=0, key=key)


def _st_text_input(label, *args, **kwargs):
    if label in ("SITE / INSTALLATION:", "Location / Team"):
        return _dropdown(st, label, SITE_OPTIONS, kwargs.get("key"))
    if label == "TEAM:":
        return _dropdown(st, label, TEAM_OPTIONS, kwargs.get("key"))
    return _original_st_text_input(label, *args, **kwargs)


def _dg_text_input(self, label, *args, **kwargs):
    if label in ("SITE / INSTALLATION:", "Location / Team"):
        return _dropdown(self, label, SITE_OPTIONS, kwargs.get("key"))
    if label == "TEAM:":
        return _dropdown(self, label, TEAM_OPTIONS, kwargs.get("key"))
    return _original_dg_text_input(self, label, *args, **kwargs)


st.text_input = _st_text_input
DeltaGenerator.text_input = _dg_text_input

source = (BASE / "core_app.py").read_text(encoding="utf-8")
exec(compile(source, "core_app.py", "exec"), {"__name__": "__main__", "__file__": str(BASE / "core_app.py")})
