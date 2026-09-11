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

# The legacy dashboard creates these controls inside Streamlit columns, so patch
# DeltaGenerator as well as the top-level Streamlit API. All other controls remain unchanged.
_original_st_toggle = st.toggle
_original_st_button = st.button
_original_dg_toggle = DeltaGenerator.toggle
_original_dg_button = DeltaGenerator.button

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

st.toggle = _st_toggle
st.button = _st_button
DeltaGenerator.toggle = _dg_toggle
DeltaGenerator.button = _dg_button

source = (BASE / "core_app.py").read_text(encoding="utf-8")
exec(compile(source, "core_app.py", "exec"), {"__name__": "__main__", "__file__": str(BASE / "core_app.py")})
