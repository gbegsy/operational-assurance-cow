from pathlib import Path
import sqlite3
import streamlit as st

BASE = Path(__file__).parent
DB = BASE / "assurance.db"

# Remove synthetic demonstration records, but leave manually entered OA-* audits untouched.
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

# Hide the old demo controls while preserving all normal form/dashboard controls.
_original_toggle = st.toggle
_original_button = st.button

def _toggle(label, *args, **kwargs):
    if label == "Demo mode":
        return False
    return _original_toggle(label, *args, **kwargs)

def _button(label, *args, **kwargs):
    if label == "Load / refresh demonstration data":
        return False
    return _original_button(label, *args, **kwargs)

st.toggle = _toggle
st.button = _button

source = (BASE / "core_app.py").read_text(encoding="utf-8")
exec(compile(source, "core_app.py", "exec"), {"__name__": "__main__", "__file__": str(BASE / "core_app.py")})
