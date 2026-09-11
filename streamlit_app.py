from pathlib import Path
import sqlite3
import streamlit as st

BASE = Path(__file__).parent
DB = BASE / "assurance.db"

# Remove any synthetic demonstration records from the deployed UAT database.
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

# Hide the built-in demo controls while leaving every real audit/form control unchanged.
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

# Execute the application source without Streamlit's top-level expression
# transformation. This also prevents DeltaGenerator objects from being rendered
# as visible debug/documentation output.
source = (BASE / "app.py").read_text(encoding="utf-8")
exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": str(BASE / "app.py")})
