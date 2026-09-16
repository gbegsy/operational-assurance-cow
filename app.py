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

# Perenco UK KPI 1 Site Controller groups from the July 2026 specification.
SITE_OPTIONS = [
    "Dimlington", "Cleeton", "Ravenspurn North", "Northern NUIs",
    "Bacton", "Leman 27BC", "Southern NUIs"
]
TEAM_OPTIONS = [
    "Dimlington", "Cleeton", "Ravenspurn North", "Northern NUIs",
    "Bacton", "Leman 27BC", "Southern NUIs"
]

# Existing manually-created UAT records may pre-date role selection. Give each audit
# family a sensible default KPI role so those records immediately feed the dashboard.
# Users can still change the mapping in KPI role configuration.
if DB.exists():
    try:
        con = sqlite3.connect(DB)
        rows = con.execute("SELECT DISTINCT form_name,auditor FROM audits WHERE auditor IS NOT NULL AND TRIM(auditor)<>''").fetchall()
        for form_name, auditor in rows:
            if form_name == "Control of Work: Permit Quality":
                kind, default_role = "permit", "Site Controller"
            elif "Toolbox Talk" in form_name:
                kind, default_role = "tbt", "W2W OOE"
            elif "Leadership Engagement" in form_name:
                kind, default_role = "lead", "Operations Director"
            else:
                continue
            existing = con.execute("SELECT role_name FROM roles WHERE mapping_type=? AND person_name=?", (kind,auditor)).fetchone()
            if existing is None or existing[0] == "Other":
                con.execute("INSERT OR REPLACE INTO roles(mapping_type,person_name,role_name) VALUES(?,?,?)", (kind,auditor,default_role))
        con.commit(); con.close()
    except Exception:
        pass

# Patch the legacy UI without changing the underlying assurance questions.
_original_st_toggle = st.toggle
_original_st_button = st.button
_original_dg_toggle = DeltaGenerator.toggle
_original_dg_button = DeltaGenerator.button
_original_st_text_input = st.text_input
_original_dg_text_input = DeltaGenerator.text_input


def _st_toggle(label, *args, **kwargs):
    if label == "Demo mode": return False
    return _original_st_toggle(label, *args, **kwargs)


def _st_button(label, *args, **kwargs):
    if label == "Load / refresh demonstration data": return False
    return _original_st_button(label, *args, **kwargs)


def _dg_toggle(self, label, *args, **kwargs):
    if label == "Demo mode": return False
    return _original_dg_toggle(self, label, *args, **kwargs)


def _dg_button(self, label, *args, **kwargs):
    if label == "Load / refresh demonstration data": return False
    return _original_dg_button(self, label, *args, **kwargs)


def _dropdown(container, label, options, key=None):
    return container.selectbox(label, ["Select..."] + options, index=0, key=key)


def _st_text_input(label, *args, **kwargs):
    if label in ("SITE / INSTALLATION:", "Location / Team"):
        return _dropdown(st, label, SITE_OPTIONS, kwargs.get("key"))
    if label == "TEAM:": return _dropdown(st, label, TEAM_OPTIONS, kwargs.get("key"))
    return _original_st_text_input(label, *args, **kwargs)


def _dg_text_input(self, label, *args, **kwargs):
    if label in ("SITE / INSTALLATION:", "Location / Team"):
        return _dropdown(self, label, SITE_OPTIONS, kwargs.get("key"))
    if label == "TEAM:": return _dropdown(self, label, TEAM_OPTIONS, kwargs.get("key"))
    return _original_dg_text_input(self, label, *args, **kwargs)


st.toggle = _st_toggle
st.button = _st_button
DeltaGenerator.toggle = _dg_toggle
DeltaGenerator.button = _dg_button
st.text_input = _st_text_input
DeltaGenerator.text_input = _dg_text_input

source = (BASE / "core_app.py").read_text(encoding="utf-8")
exec(compile(source, "core_app.py", "exec"), {"__name__": "__main__", "__file__": str(BASE / "core_app.py")})
