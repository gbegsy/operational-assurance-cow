from pathlib import Path
import sqlite3
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

BASE = Path(__file__).parent
DB = BASE / "assurance.db"

# Remove only synthetic demonstration records. Manually entered OA-* audits are retained.
if DB.exists():
    try:
        con = sqlite3.connect(DB)
        con.execute("DELETE FROM audits WHERE audit_id LIKE 'DEMO-%'")
        con.execute("DELETE FROM roles WHERE person_name LIKE 'Demo %'")
        con.execute("DELETE FROM kpi5 WHERE demo=1")
        con.commit()
        con.close()
    except Exception:
        pass

# Generic, client-neutral locations used by the KPI engine.
SITE_OPTIONS = [
    "Asset A", "Asset B", "Asset C", "North NUI Group", "Gas Terminal",
    "Offshore Hub", "South NUI Group", "North Flying Team", "North W2W",
    "South Flying Team", "South W2W"
]
TEAM_OPTIONS = [
    "Site Operations", "North Flying Team", "North W2W",
    "South Flying Team", "South W2W", "Offshore Hub Team"
]

# The legacy dashboard creates controls inside Streamlit columns, so patch
# DeltaGenerator as well as the top-level Streamlit API. All other controls remain unchanged.
_original_st_toggle = st.toggle
_original_st_button = st.button
_original_dg_toggle = DeltaGenerator.toggle
_original_dg_button = DeltaGenerator.button
_original_st_text_input = st.text_input
_original_dg_text_input = DeltaGenerator.text_input


def _st_toggle(label, *args, **kwargs):
    if label == "Demo mode":
        return False
    return _original_st_toggle(label, *args, **kwargs)


def _st_button(label, *args, **kwargs):
    if label == "Load / refresh demonstration data":
        return False
    return _original_st_button(label, *args, **kwargs)


def _dg_toggle(self, label, *args, **kwargs):
    if label == "Demo mode":
        return False
    return _original_dg_toggle(self, label, *args, **kwargs)


def _dg_button(self, label, *args, **kwargs):
    if label == "Load / refresh demonstration data":
        return False
    return _original_dg_button(self, label, *args, **kwargs)


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


st.toggle = _st_toggle
st.button = _st_button
DeltaGenerator.toggle = _dg_toggle
DeltaGenerator.button = _dg_button
st.text_input = _st_text_input
DeltaGenerator.text_input = _dg_text_input

source = (BASE / "core_app.py").read_text(encoding="utf-8")
exec(compile(source, "core_app.py", "exec"), {"__name__": "__main__", "__file__": str(BASE / "core_app.py")})
