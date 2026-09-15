import streamlit as st
import streamlit as st
import pandas as pd
import sqlite3, json, uuid, calendar, os
from pathlib import Path

try:
    import psycopg
except ImportError:
    psycopg = None
from datetime import date, datetime

BASE = Path(__file__).parent
DATA = json.loads((BASE / "questions.json").read_text(encoding="utf-8"))
DB = BASE / "assurance.db"

# The deployed demo uses PostgreSQL when DATABASE_URL is configured in
# Streamlit Secrets. SQLite remains available for local development.
try:
    DATABASE_URL = st.secrets.get("DATABASE_URL", "")
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "")


class DatabaseConnection:
    """Small compatibility layer for SQLite and PostgreSQL."""

    def __init__(self):
        if DATABASE_URL:
            if psycopg is None:
                raise RuntimeError("PostgreSQL support is not installed.")
            self.connection = psycopg.connect(DATABASE_URL)
            self.postgres = True
        else:
            self.connection = sqlite3.connect(DB)
            self.postgres = False

    def execute(self, query, params=()):
        if self.postgres:
            if query == "INSERT OR REPLACE INTO roles VALUES(?,?,?)":
                query = (
                    "INSERT INTO roles(mapping_type,person_name,role_name) "
                    "VALUES(%s,%s,%s) ON CONFLICT(mapping_type,person_name) "
                    "DO UPDATE SET role_name=EXCLUDED.role_name"
                )
            elif query.startswith("INSERT OR REPLACE INTO kpi5 VALUES("):
                query = query.replace("INSERT OR REPLACE INTO kpi5", "INSERT INTO kpi5")
                query = query.replace("?", "%s")
                query += (
                    " ON CONFLICT(record_id) DO UPDATE SET "
                    "submitted_at=EXCLUDED.submitted_at, reporting_month=EXCLUDED.reporting_month, "
                    "site=EXCLUDED.site, current_count=EXCLUDED.current_count, "
                    "previous_count=EXCLUDED.previous_count, hipo=EXCLUDED.hipo, "
                    "injury=EXCLUDED.injury, loc=EXCLUDED.loc, major_loc=EXCLUDED.major_loc, "
                    "repeat_theme=EXCLUDED.repeat_theme, recurring_failure=EXCLUDED.recurring_failure, "
                    "significant_increase=EXCLUDED.significant_increase, comments=EXCLUDED.comments, "
                    "demo=EXCLUDED.demo"
                )
            else:
                query = query.replace("?", "%s")
        return self.connection.execute(query, params)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


st.set_page_config(page_title="Operational Assurance - Control of Work", page_icon="🔒", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:1.5rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#f7f9fb,#edf2f6);border-right:1px solid #d8e1e7}
[data-testid="stSidebar"] div[role="radiogroup"] label{background:#fff;border:1px solid #d7e1e8;border-radius:9px;padding:8px 10px;margin:2px 0}
.oa-banner{background:#000;color:#fff;min-height:118px;display:flex;align-items:center;justify-content:center;text-align:center;margin-bottom:8px}
.oa-title{font-size:23px;font-weight:800;line-height:1.35;padding:20px}.oa-sub{font-size:20px;margin-top:8px}
.purpose{border:1px solid #222;padding:9px 11px;font-size:13px;line-height:1.4;margin-bottom:8px;background:#fff}
.blackbar{background:#000;color:#fff;font-weight:800;padding:7px 10px;margin-top:8px}.section-title{font-size:18px;font-weight:800;margin:16px 0 6px}.qrow{padding:8px 0 2px;font-size:15px}
.dash{background:linear-gradient(135deg,#102b40,#173f5c 70%,#1d5d82);color:#fff;border-radius:15px;padding:23px 26px;margin-bottom:16px}.dash h1{font-size:31px;margin:0 0 4px}.dash p{margin:0;color:#d6e5ef}
.kpi{background:#fff;border:1px solid #d8e2e8;border-top:5px solid #a8b7c2;border-radius:12px;padding:14px;min-height:170px;box-shadow:0 3px 12px rgba(20,50,70,.06)}.kpi.green{border-top-color:#2f9e62}.kpi.amber{border-top-color:#d4a72c}.kpi.red{border-top-color:#cf4c45}.kt{font-size:10px;font-weight:800;color:#718594;text-transform:uppercase}.kv{font-size:28px;font-weight:800;color:#102b40;margin:10px 0 4px}.kd{font-size:11px;color:#657a88;line-height:1.4}.ks{font-size:11px;font-weight:800;color:#314b5c}.exec{background:#fff;border:1px solid #d8e2e8;border-radius:12px;padding:17px 19px;margin-top:12px}.exec h3{margin:0 0 8px;color:#16364b}.focus{border-left:4px solid #1679c4;background:#f4f9fc;padding:10px 12px;margin-top:10px}
</style>
""", unsafe_allow_html=True)

SITE_GROUPS = {
    "Site 1": (1,1), "Site 2": (1,1), "Site 3": (1,1),
    "Site 4": (2,1), "Site 5": (1,1), "Site 6": (1,1),
    "Site 7": (2,1)
}
ASSET_GROUPS = ["Site 1","Site 2","Site 3","Site 4","Site 5","Site 6","Site 7","Site 8","Site 9"]
SITE_OPTIONS = sorted(set(ASSET_GROUPS + list(SITE_GROUPS)))


def db():
    c=DatabaseConnection()
    c.execute("CREATE TABLE IF NOT EXISTS audits(audit_id TEXT PRIMARY KEY,submitted_at TEXT,form_name TEXT,audit_date TEXT,site TEXT,auditor TEXT,reference TEXT,metadata TEXT,responses TEXT,summary TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS roles(mapping_type TEXT,person_name TEXT,role_name TEXT,PRIMARY KEY(mapping_type,person_name))")
    c.execute("CREATE TABLE IF NOT EXISTS kpi5(record_id TEXT PRIMARY KEY,submitted_at TEXT,reporting_month TEXT,site TEXT,current_count INTEGER,previous_count INTEGER,hipo INTEGER,injury INTEGER,loc INTEGER,major_loc INTEGER,repeat_theme TEXT,recurring_failure TEXT,significant_increase TEXT,comments TEXT,demo INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS governance(period TEXT,site TEXT,kpi2_alignment TEXT,kpi2_ind_conf INTEGER,kpi2_ind_find INTEGER,kpi2_self_find INTEGER,kpi3_coverage TEXT,kpi4_justification TEXT,kpi4_oim_coverage TEXT,kpi4_findings TEXT,kpi4_oim_consecutive INTEGER,kpi4_oim_12m INTEGER,PRIMARY KEY(period,site))")
    c.commit(); return c

def save_audit(form,meta,responses,summary=""):
    aid="OA-"+datetime.now().strftime("%Y%m%d")+"-"+uuid.uuid4().hex[:6].upper()
    c=db(); c.execute("INSERT INTO audits VALUES(?,?,?,?,?,?,?,?,?,?)",(aid,datetime.now().isoformat(timespec="seconds"),form,meta.get("audit_date",""),meta.get("site",""),meta.get("auditor",""),meta.get("reference",""),json.dumps(meta),json.dumps(responses),summary)); c.commit(); c.close(); return aid

def audits():
    c=db(); rows=c.execute("SELECT * FROM audits ORDER BY submitted_at").fetchall(); c.close(); out=[]
    for r in rows:
        out.append(dict(zip(["audit_id","submitted_at","form_name","audit_date","site","auditor","reference","metadata","responses","summary"],r)))
    for a in out:
        try:a["metadata"]=json.loads(a["metadata"] or "{}")
        except:a["metadata"]={}
        try:a["responses"]=json.loads(a["responses"] or "[]")
        except:a["responses"]=[]
    return out

def reportable(a):
    """Keep live records only; synthetic/demo and obvious test submissions are excluded."""
    aid=str(a.get("audit_id","")).upper(); auditor=str(a.get("auditor","")).strip().lower()
    ref=str(a.get("reference","")).strip().lower(); meta=a.get("metadata") or {}
    return not (aid.startswith("DEMO-") or bool(meta.get("demo")) or auditor.startswith("test") or ref.startswith("demo-"))

def role_map(kind):
    c=db(); r=dict(c.execute("SELECT person_name,role_name FROM roles WHERE mapping_type=?",(kind,)).fetchall()); c.close(); return r

def set_role(kind,name,role):
    c=db(); c.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?)",(kind,name,role)); c.commit(); c.close()

def banner(title,sub=""):
    s=f'<div class="oa-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="oa-banner"><div class="oa-title">{title}{s}</div></div>',unsafe_allow_html=True)

def purpose(text): st.markdown(f'<div class="purpose"><b>PURPOSE:</b> {text}</div>',unsafe_allow_html=True)

def questions(prefix,sections):
    out=[]
    for si,(section,qs) in enumerate(sections):
        st.markdown(f'<div class="section-title">{section}</div>',unsafe_allow_html=True)
        for qi,(letter,q) in enumerate(qs):
            st.markdown(f'<div class="qrow"><b>{letter})</b> {q}</div>',unsafe_allow_html=True)
            c1,c2=st.columns([1,2]); ans=c1.selectbox("Response",["Select","Yes","No","N/A"],key=f"{prefix}-{si}-{qi}",label_visibility="collapsed"); act=c2.text_input("SMART ACTION",placeholder="Add SMART action where required",key=f"act-{prefix}-{si}-{qi}",label_visibility="collapsed")
            out.append({"section":section,"item":letter,"question":q,"response":None if ans=="Select" else ans,"smart_action":act})
    return out

def result(a):
    v=[str(x.get("response","")).lower() for x in a["responses"] if str(x.get("response","")).lower() in ("yes","no")]
    if not v:return None
    return "Non-Compliant" if "no" in v else "Compliant"

def audit_conf(rows):
    r=[result(a) for a in rows]; r=[x for x in r if x]
    return None if not r else round(100*sum(x=="Compliant" for x in r)/len(r))

def q_conf(rows):
    v=[]
    for a in rows:
        v += [str(x.get("response","")).lower() for x in a["responses"] if str(x.get("response","")).lower() in ("yes","no")]
    return None if not v else round(100*sum(x=="yes" for x in v)/len(v))

def permit_type(a):
    m=a["metadata"]
    if m.get("routine") and not m.get("new_wcc"):return "Routine"
    if m.get("new_wcc") and not m.get("routine"):return "Non-Routine"
    return "Unclassified"

def weeks(y,m): return sum(1 for w in calendar.monthcalendar(y,m) if w[calendar.MONDAY])
def rag(plan,conf):
    if plan is None or conf is None:return "Not enough data"
    if plan<70 or conf<70:return "Red"
    if plan>=100 and conf>=90:return "Green"
    return "Amber"
def css(s): return {"Green":"green","Amber":"amber","Red":"red","Needs review":"amber"}.get(s,"")

def card(name,title,value,status,detail):
    st.markdown(f'<div class="kpi {css(status)}"><div class="kt">{name}</div><div class="ks">{title}</div><div class="kv">{value}</div><div class="kd">{detail}<br><b>{status}</b></div></div>',unsafe_allow_html=True)

def safe_date(x):
    try:return datetime.strptime(str(x),"%Y-%m-%d").date()
    except:return None

def governance(period,site):
    c=db(); r=c.execute("SELECT * FROM governance WHERE period=? AND site=?",(period,site)).fetchone(); c.close()
    keys=["period","site","kpi2_alignment","kpi2_ind_conf","kpi2_ind_find","kpi2_self_find","kpi3_coverage","kpi4_justification","kpi4_oim_coverage","kpi4_findings","kpi4_oim_consecutive","kpi4_oim_12m"]
    return dict(zip(keys,r)) if r else {"period":period,"site":site,"kpi2_alignment":"Not assessed","kpi2_ind_conf":None,"kpi2_ind_find":0,"kpi2_self_find":0,"kpi3_coverage":"Not assessed","kpi4_justification":"Not required","kpi4_oim_coverage":"Not assessed","kpi4_findings":"None","kpi4_oim_consecutive":0,"kpi4_oim_12m":0}

def seed_demo():
    c=db(); c.execute("DELETE FROM audits WHERE audit_id LIKE 'DEMO-%'"); c.execute("DELETE FROM roles WHERE person_name LIKE 'Demo %'"); c.execute("DELETE FROM kpi5 WHERE demo=1")
    d=str(date.today()); now=datetime.now().isoformat(timespec="seconds")
    def add(aid,form,site,aud,meta,resp,summary=""):
        m={"site":site,"audit_date":d,"auditor":aud,"reference":aid,"demo":True,**meta}; c.execute("INSERT INTO audits VALUES(?,?,?,?,?,?,?,?,?,?)",(aid,now,form,d,site,aud,aid,json.dumps(m),json.dumps(resp),summary))
    yes=[{"question":"Control verified","response":"Yes","smart_action":""}]; no=[{"question":"Control not fully evidenced","response":"No","smart_action":"Review and close identified assurance gap."}]
    add("DEMO-PQ1","Control of Work: Permit Quality","Asset A","Demo Site Controller",{"routine":True,"new_wcc":False},yes)
    add("DEMO-PQ2","Control of Work: Permit Quality","Asset A","Demo Site Controller",{"routine":False,"new_wcc":True},no)
    add("DEMO-PQ3","Control of Work: Permit Quality","Asset C","Demo Asset Superintendent",{"routine":True,"new_wcc":False},yes)
    add("DEMO-TBT1","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","North W2W","Demo W2W OOE",{"activity_type":"Routine"},no)
    add("DEMO-TBT2","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","South W2W","Demo Medic HSEA",{"activity_type":"Routine"},yes)
    add("DEMO-TBT3","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Offshore Hub","Demo Field Hub OIM",{"activity_type":"Routine"},yes)
    add("DEMO-LEAD1","Control of Work Leadership Engagement Checklist","North W2W","Demo Operations Director",{},yes,"Meets CoW Standard")
    add("DEMO-LEAD2","Control of Work Leadership Engagement Checklist","South W2W","Demo Operations Director",{},yes,"Meets CoW Standard")
    for x in [("permit","Demo Site Controller","Site Controller"),("permit","Demo Asset Superintendent","Asset Superintendent"),("tbt","Demo W2W OOE","W2W OOE"),("tbt","Demo Medic HSEA","Medic HSEA"),("tbt","Demo Field Hub OIM","Field Hub OIM"),("lead","Demo Operations Director","Operations Director")]:c.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?)",x)
    c.execute("INSERT OR REPLACE INTO kpi5 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("DEMO-KPI5",now,d[:7],"All",1,0,0,0,1,0,"Yes","No","No","Synthetic trial value",1)); c.commit(); c.close()

def dashboard():
    st.markdown('<div class="dash"><h1>Control of Work KPI Dashboard</h1><p>Operational assurance · performance, coverage and leadership oversight</p></div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,2]); md=c1.date_input("Reporting month",date.today().replace(day=1)); demo=c2.toggle("Demo mode")
    if c3.button("Load / refresh demonstration data",disabled=not demo,use_container_width=True):seed_demo(); st.rerun()
    y,m=md.year,md.month; period=md.strftime("%Y-%m"); all_a=[a for a in audits() if reportable(a)]; month=[a for a in all_a if safe_date(a["audit_date"]) and safe_date(a["audit_date"]).year==y and safe_date(a["audit_date"]).month==m]
    sites=sorted({a["site"] for a in month if a["site"]}); site=st.selectbox("Site / Team",["All"]+sites)
    view=month if site=="All" else [a for a in month if a["site"]==site]
    permit=[a for a in view if a["form_name"]=="Control of Work: Permit Quality"]; tbt=[a for a in view if "Toolbox Talk" in a["form_name"]]; lead=[a for a in view if "Leadership Engagement" in a["form_name"]]
    pmap,tmap,lmap=role_map("permit"),role_map("tbt"),role_map("lead")
    st.caption("KPI attribution uses the Auditor Role recorded on the form. The auditor name identifies the person; the role identifies which KPI receives the audit.")
    def assigned_role(a, mapping): return (a.get("metadata") or {}).get("auditor_role") or mapping.get(a.get("auditor"), "Other")
    with st.expander("KPI role configuration"):
        st.info("KPI attribution is based on this role mapping, not the auditor's name. Permit Quality audits mapped to Site Controller feed KPI 1; Permit Quality audits mapped to Asset Superintendent feed KPI 2; Leadership Engagement audits mapped to an operations leadership role feed KPI 3; Toolbox Talk / Permit / POP audits mapped to W2W OOE, Medic HSEA or Field Hub OIM feed KPI 4. Only auditors appearing in the selected month are listed here.")
        specs=[("permit",permit,["Site Controller","Asset Superintendent","Other"]),("tbt",tbt,["W2W OOE","Medic HSEA","Field Hub OIM","Other"]),("lead",lead,["Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager","Other"])]
        for kind,rows,opts in specs:
            for n in sorted({a["auditor"] for a in rows if a["auditor"]}):
                cur=role_map(kind).get(n,"Other"); val=st.selectbox(n,opts,index=opts.index(cur) if cur in opts else len(opts)-1,key=f"r-{kind}-{n}")
                if val!=cur:set_role(kind,n,val)
    gov=governance(period,site); w=weeks(y,m)
    sc=[a for a in permit if assigned_role(a,pmap)=="Site Controller"]; asc=[a for a in permit if assigned_role(a,pmap)=="Asset Superintendent"]
    k1plan=(sum(a+b for a,b in SITE_GROUPS.values())*w) if site=="All" else ((sum(SITE_GROUPS.get(site,(0,0)))*w) or None); k1done=len([a for a in sc if permit_type(a)!="Unclassified"]); k1routine=sum(1 for a in sc if permit_type(a)=="Routine"); k1nonroutine=sum(1 for a in sc if permit_type(a)=="Non-Routine"); k1p=round(100*k1done/k1plan) if k1plan else None; k1c=audit_conf(sc); k1s=rag(k1p,k1c) if sc else "Not enough data"
    k2plan=w; k2done=len([a for a in asc if permit_type(a)!="Unclassified"]); k2p=round(100*k2done/k2plan) if k2plan else None; k2c=audit_conf(asc); k2s=rag(k2p,k2c) if asc else "Not enough data"; k2cov=len({a["site"] for a in asc if a["site"] in ASSET_GROUPS})
    q=(m-1)//3+1; qstart=date(y,(q-1)*3+1,1); qe=(q-1)*3+3; qend=date(y,qe,calendar.monthrange(y,qe)[1]); k3_roles={"Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager","Onshore Operations Leadership"}; qlead=[a for a in all_a if "Leadership Engagement" in a["form_name"] and safe_date(a["audit_date"]) and qstart<=safe_date(a["audit_date"])<=qend and (site=="All" or a["site"]==site) and assigned_role(a,lmap) in k3_roles]; k3n=len(qlead); k3c=audit_conf(qlead); complete=date.today()>qend
    if not qlead:k3s="Not enough data"
    elif k3c is not None and k3c<70:k3s="Red"
    elif k3c is not None and k3c<70:k3s="Red"
    elif k3n<=1:k3s="Red"
    elif k3n==2 or (k3c is not None and k3c<90):k3s="Amber"
    elif k3n>=3 and k3c>=90 and gov["kpi3_coverage"]=="Reasonable":k3s="Green"
    else:k3s="Amber"
    mapped=[a for a in tbt if (a.get("metadata") or {}).get("nui_visit",True) and assigned_role(a,tmap) in {"W2W OOE","Medic HSEA","Field Hub OIM"}]; counts={r:sum(assigned_role(a,tmap)==r for a in mapped) for r in ["W2W OOE","Medic HSEA","Field Hub OIM"]}; oo=round(100*counts["W2W OOE"]/w) if w else 0; med=round(100*counts["Medic HSEA"]/w) if w else 0; k4c=audit_conf(mapped)
    k4_target_missed=oo<100 or med<100 or counts["Field Hub OIM"]<1
    if not mapped:k4s="Not enough data"
    elif oo<50 or med<50 or (k4c is not None and k4c<70) or gov["kpi4_findings"]=="Significant / repeat" or gov["kpi4_oim_consecutive"]>=2 or gov["kpi4_oim_12m"]>2:k4s="Red"
    elif med<100:k4s="Amber"
    elif oo<100 or med<100 or (k4c is not None and k4c<90):k4s="Amber"
    else:k4s="Green"
    c=db(); k5rows=c.execute("SELECT * FROM kpi5 WHERE reporting_month=? ORDER BY submitted_at",(period,)).fetchall(); c.close(); k5=k5rows[-1] if k5rows else None
    if not k5:k5s="Not enough data"; k5v="—"; k5detail="Enter monthly incident summary"
    else:
        current,prev,hipo,inj,loc,major,repeat,recurring,sig=k5[4],k5[5],k5[6],k5[7],k5[8],k5[9],k5[10],k5[11],k5[12]
        k5s="Red" if sig=="Yes" or hipo>=2 or inj>=2 or major>=1 or recurring=="Yes" else ("Amber" if current>prev or hipo==1 or inj==1 or loc>=1 or repeat=="Yes" else "Green"); k5v=str(current); k5detail=f"Previous {prev} · HiPO {hipo} · MTC+ {inj} · LOC {loc}"
    statuses=[k1s,k2s,k3s,k4s,k5s]; assessed=[x for x in statuses if x in ("Green","Amber","Red")]; overall="Red" if "Red" in assessed else ("Amber" if "Amber" in assessed else ("Green" if len(assessed)==5 else "Not enough data"))

    # Three management tiers containing five individual KPIs. Each KPI retains
    # its own target, denominator and intervention threshold.
    st.markdown("### Tier 1 - Strategic / Leadership")
    st.caption("Senior leadership oversight of Control of Work trends, systemic weaknesses and permit-controlled incident risk.")
    with st.container():
        card("KPI 5 · Tier 1","Permit-Controlled Activity Incident Performance (Rolling 12 Months)",k5v,k5s,k5detail)

    st.markdown("### Tier 2 - Functional")
    st.caption("Asset and functional leadership oversight of assurance performance, asset coverage and leadership engagement.")
    t2a,t2b=st.columns(2)
    with t2a:
        card("KPI 2 · Tier 2","Asset Superintendent Permit Assurance / Non-Compliance",f"{k2done}/{k2plan}" if k2plan else "—",k2s,f"Completion {k2p if k2p is not None else '—'}% · Whole-permit conformance {k2c if k2c is not None else '—'}% · coverage {k2cov}/9 asset groups · target 1 per week")
    with t2b:
        card("KPI 3 · Tier 2","Onshore Operations Leadership NUI Engagement",f"{k3n} engagements" if qlead else "—",k3s,f"Q{q} · {k3c if k3c is not None else '—'}% checklist conformance · minimum target 3 per quarter")

    st.markdown("### Tier 3 - Operational")
    st.caption("Site-level visibility of permit quality, supervision, compliance monitoring and worksite controls.")
    t3a,t3b=st.columns(2)
    with t3a:
        card("KPI 1 · Tier 3","Site Controller Permit Assurance / Non-Compliance",f"{k1done}/{k1plan}" if k1plan else "—",k1s,f"Completion {k1p if k1p is not None else '—'}% · Whole-permit conformance {k1c if k1c is not None else '—'}% · Routine {k1routine} · Non-routine {k1nonroutine} · target 16 per week / 64 per 4 weeks")
    with t3b:
        card("KPI 4 · Tier 3","Site Leadership NUI Visits / Engagement",f"OOE {counts['W2W OOE']}/{w} · Medic/HSEA {counts['Medic HSEA']}/{w} · Field Hub OIM {counts['Field Hub OIM']}/1" if mapped else f"OOE 0/{w} · Medic/HSEA 0/{w} · Field Hub OIM 0/1",k4s,f"OOE 1 per week · Medic/HSEA 1 per week · Field Hub OIM 1 per quarter · conformance {k4c if k4c is not None else '—'}% · missed-target justification: {gov['kpi4_justification']}")
    st.markdown(f'<div class="exec"><h3>Overall assurance position: {overall}</h3><div>Three-tier framework containing five individual KPIs, covering assurance delivery, whole-permit conformance, leadership engagement and lagging incident performance.</div><div class="focus"><b>Leadership focus:</b> address Red/Amber exceptions, maintain planned assurance coverage and test repeat findings for systemic Control of Work weakness.</div></div>',unsafe_allow_html=True)
    tabs=st.tabs(["Company & Site Performance","Findings & Actions","Work as Imagined vs Work as Done","Auditor View","KPI 5 Data"])
    with tabs[0]:
        st.subheader("Site Controller assurance by group"); rows=[]
        month_permit=[a for a in month if a["form_name"]=="Control of Work: Permit Quality" and pmap.get(a["auditor"])=="Site Controller"]
        for g,(rw,nw) in SITE_GROUPS.items():
            aa=[a for a in month_permit if a["site"]==g]; done=len([a for a in aa if permit_type(a)!="Unclassified"]); plan=(rw+nw)*w; pc=round(100*done/plan) if plan else None; cf=audit_conf(aa); rows.append({"Site / Group":g,"Routine":sum(permit_type(a)=="Routine" for a in aa),"Non-routine":sum(permit_type(a)=="Non-Routine" for a in aa),"Planned":plan,"Completed":done,"Plan %":pc,"Whole-permit conformance %":cf,"RAG":rag(pc,cf) if done else "Not enough data"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); st.caption(f"Monthly demonstration basis: {w} reporting weeks. Routine and non-routine samples remain separate.")
    with tabs[1]:
        rows=[]
        for a in permit+tbt+lead:
            for r in a["responses"]:
                if str(r.get("response","")).lower()=="no":rows.append({"Site":a["site"],"Auditor":a["auditor"],"Form":a["form_name"],"Finding":r.get("question",""),"Action":r.get("smart_action") or r.get("comments_evidence","")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True) if rows else st.success("No negative assurance responses in this view.")
    with tabs[2]:
        st.markdown("**Work as Imagined** — the question sets represent the expected Control of Work standard and intended controls."); c1,c2,c3=st.columns(3); c1.metric("Question conformance",f"{q_conf(permit+tbt)}%" if q_conf(permit+tbt) is not None else "—"); c2.metric("Permit whole-audit conformance",f"{audit_conf(permit)}%" if audit_conf(permit) is not None else "—"); c3.metric("TBT/POP whole-audit conformance",f"{audit_conf(tbt)}%" if audit_conf(tbt) is not None else "—")
    with tabs[3]:
        rr=[]
        for n in sorted({a["auditor"] for a in permit+tbt+lead if a["auditor"]}):
            aa=[a for a in permit+tbt+lead if a["auditor"]==n]; rr.append({"Auditor / Leader":"Anonymous","Role(s)":", ".join(sorted({(a.get("metadata") or {}).get("auditor_role", "") for a in aa if (a.get("metadata") or {}).get("auditor_role")})),"Activities":len(aa),"Question conformance %":q_conf(aa),"Whole-audit conformance %":audit_conf(aa),"Sites / Teams":", ".join(sorted({a["site"] for a in aa if a["site"]}))})
        st.dataframe(pd.DataFrame(rr),use_container_width=True,hide_index=True) if rr else st.info("No auditor data.")
    with tabs[4]:
        st.subheader("KPI 5 Incident Entry"); st.caption("Permit-controlled activity incidents · rolling 12-month reporting"); incident_date=st.date_input("Incident date",date.today()); incident_site=st.selectbox("Site / Asset",["All"]+SITE_OPTIONS); moi_ref=st.text_input("MOI reference"); incident_title=st.text_input("Incident title / short description"); permitted=st.selectbox("Occurred during permitted activity?",["Yes","No"]); a,b,c=st.columns(3); current=a.number_input("Rolling 12-month permit-controlled incidents",0,999,0); prev=b.number_input("Previous rolling 12-month incidents",0,999,0); hipo=c.number_input("HiPO events",0,999,0); a,b,c=st.columns(3); injury=a.number_input("Significant injuries (MTC+)",0,999,0); loc=b.number_input("Loss of Containment",0,999,0); major=c.number_input("Major Loss of Containment",0,999,0); a,b,c=st.columns(3); repeat=a.selectbox("Repeat event theme?",["No","Yes"]); recurring=b.selectbox("Recurring permit-control failure?",["No","Yes"]); sig=c.selectbox("Significant increase?",["No","Yes"],help="No numerical threshold is assumed; use the agreed management assessment."); comments=st.text_area("Learning / management comments"); comments=f"Incident date: {incident_date}; Site/Asset: {incident_site}; MOI reference: {moi_ref}; Title: {incident_title}; Occurred during permitted activity: {permitted}; {comments}"
        if st.button("Save KPI 5 incident entry",type="primary"):
            rid="KPI5-"+uuid.uuid4().hex[:8].upper(); con=db(); con.execute("INSERT INTO kpi5 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,datetime.now().isoformat(timespec="seconds"),period,site,current,prev,hipo,injury,loc,major,repeat,recurring,sig,comments,0)); con.commit(); con.close(); st.success("KPI 5 incident entry saved.")

st.sidebar.markdown("### Operational Assurance")
page=st.sidebar.radio("Navigation",["Dashboard","KPI 5 Incidents","Permit Quality","Toolbox Talk / Permit / POP","Leadership Engagement","Submitted Audits","Dashboard Export"],label_visibility="collapsed")

if page=="Dashboard": dashboard()
elif page=="KPI 5 Incidents":
    st.header("KPI 5 Incident Entry")
    st.caption("Permit-controlled activity incidents · rolling 12-month reporting")
    a,b,c=st.columns(3); current=a.number_input("Rolling 12-month permit-controlled incidents",0,999,0,key="k5-nav-current"); prev=b.number_input("Previous rolling 12-month incidents",0,999,0,key="k5-nav-prev"); hipo=c.number_input("HiPO events",0,999,0,key="k5-nav-hipo")
    a,b,c=st.columns(3); injury=a.number_input("Significant injuries (MTC+)",0,999,0,key="k5-nav-injury"); loc=b.number_input("Loss of Containment",0,999,0,key="k5-nav-loc"); major=c.number_input("Major Loss of Containment",0,999,0,key="k5-nav-major")
    a,b,c=st.columns(3); repeat=a.selectbox("Repeat event theme?",["No","Yes"],key="k5-nav-repeat"); recurring=b.selectbox("Recurring permit-control failure?",["No","Yes"],key="k5-nav-recurring"); sig=c.selectbox("Significant increase?",["No","Yes"],help="No numerical threshold is assumed; use the agreed management assessment.",key="k5-nav-sig")
    comments=st.text_area("Learning / management comments",key="k5-nav-comments")
    if st.button("Save KPI 5 incident entry",type="primary",key="k5-nav-save"):
        rid="KPI5-"+uuid.uuid4().hex[:8].upper(); con=db(); con.execute("INSERT INTO kpi5 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,datetime.now().isoformat(timespec="seconds"),period,site,current,prev,hipo,injury,loc,major,repeat,recurring,sig,comments,0)); con.commit(); con.close(); st.success("KPI 5 incident entry saved. Return to Dashboard to view the result.")
elif page=="Permit Quality":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work: Permit Quality")
    c1,c2,c3=st.columns([1.5,1.2,1.2]); site=c1.selectbox("SITE / INSTALLATION:",["Select"]+SITE_OPTIONS); team=c2.text_input("TEAM:"); ad=c3.date_input("DATE OF AUDIT:",date.today())
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1]); auditor=c1.text_input("AUDITOR:",value="Anonymous",disabled=True); auditor_role=c2.selectbox("AUDITOR ROLE:",["Site Controller","Asset Superintendent","Other"],index=None); sc=c3.text_input("SITE CONTROLLER:",value="Not captured",disabled=True); classification=c4.radio("WCC CLASSIFICATION:",["New WCC","Routine"],index=None); nw=classification=="New WCC"; routine=classification=="Routine"
    ref=""; desc=st.text_input("WCC DESCRIPTION:")
    meta={"site":site,"team":team,"audit_date":str(ad),"auditor":auditor,"auditor_role":auditor_role,"site_controller":sc,"reference":ref,"wcc_description":desc,"new_wcc":nw,"routine":routine}
    purpose("Self-verify the quality of a planned or active Work Control Certificate (WCC), including permit preparation, hazard identification, risk assessment, control selection, authorisation and worksite readiness."); st.markdown('<div class="blackbar">QUESTION</div>',unsafe_allow_html=True); rs=questions("ptw",DATA["ptw"]); st.markdown('<div class="blackbar">ENSURE EACH NON-COMPLIANCE GENERATES A RECORDED SMART ACTION</div>',unsafe_allow_html=True)
    if st.button("Submit Permit Quality Audit",type="primary",use_container_width=True):
        if site=="Select" or not auditor_role:st.error("Complete SITE / INSTALLATION and AUDITOR ROLE.")
        elif classification is None:st.error("Select exactly one classification: New WCC or Routine.")
        elif any(r["response"] is None for r in rs):st.error("Every question requires a response.")
        else:st.success("Submitted: "+save_audit("Control of Work: Permit Quality",meta,rs))
elif page=="Toolbox Talk / Permit / POP":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures")
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1]); site=c1.selectbox("SITE / INSTALLATION:",["Select"]+SITE_OPTIONS); team=c2.text_input("TEAM:"); ad=c3.date_input("DATE OF AUDIT:",date.today()); activity=c4.radio("TYPE",["New WCC","Routine","POP"],index=None)
    c1,c2,c3=st.columns(3); auditor=c1.text_input("AUDITOR:",value="Anonymous",disabled=True); auditor_role=c2.selectbox("AUDITOR ROLE:",["W2W OOE","Medic HSEA","Field Hub OIM","Other"],index=None); sc=c3.text_input("SITE CONTROLLER:",value="Not captured",disabled=True)
    nui_visit=st.checkbox("NUI VISIT COMPLETED – this audit will contribute to KPI 4",value=True)
    ref=st.text_input("WCC / POP No:"); desc=st.text_input("DESCRIPTION:"); meta={"site":site,"team":team,"audit_date":str(ad),"auditor":auditor,"auditor_role":auditor_role,"site_controller":sc,"reference":ref,"description":desc,"activity_type":activity,"nui_visit":nui_visit}
    purpose("Self-verify day-to-day Toolbox Talk, permit and operating-procedure compliance, workforce understanding and implementation of Control of Work requirements."); st.markdown('<div class="blackbar">QUESTION · SITE VISIT REQUIRED · SEQUENTIAL REVIEW</div>',unsafe_allow_html=True); rs=questions("tbt12",DATA["tbt"][:2]); st.markdown('<div class="blackbar">AUDITING A POP? MOVE TO QUESTION 8</div>',unsafe_allow_html=True); rs += questions("pop",[DATA["pop"]]) if activity=="POP" else questions("tbt37",DATA["tbt"][2:])+questions("tbt8",[DATA["pop"]])
    if st.button("Submit TBT / Permit / POP Audit",type="primary",use_container_width=True):
        if site=="Select" or not auditor_role or not activity:st.error("Complete SITE / INSTALLATION, AUDITOR ROLE and TYPE.")
        elif any(r["response"] is None for r in rs):st.error("Every displayed question requires a response.")
        else:st.success("Submitted: "+save_audit("Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures",meta,rs))
elif page=="Leadership Engagement":
    banner("Control of Work Leadership Engagement Checklist"); c1,c2,c3,c4=st.columns([1,2,1.4,1.7]); ad=c1.date_input("Date",date.today()); site=c2.selectbox("Location / Team",["Select"]+SITE_OPTIONS); sc=c3.text_input("Site Controller",value="Not captured",disabled=True); leader=c4.text_input("Leadership Representative",value="Anonymous",disabled=True); auditor_role=st.selectbox("AUDITOR ROLE:",["Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager","Other"],index=None); purpose("Provide a predefined set of Control of Work questions for leadership engagement visits, supporting visible leadership, workforce engagement and assurance discussions."); rs=[]
    for si,(section,qs) in enumerate(DATA["lead"]):
        st.markdown(f'<div class="section-title">{section}</div>',unsafe_allow_html=True)
        for qi,q in enumerate(qs):
            st.markdown(f'<div class="qrow">{q}</div>',unsafe_allow_html=True)
            if section=="Learning & Continuous Improvement" and q.startswith("Can personnel suggest"):
                comment=st.text_area("Comments / Evidence",key=f"lc-{si}-{qi}"); ans="Comment"
            else:
                ans=st.radio("Response",["Yes","No"],index=None,horizontal=True,key=f"lr-{si}-{qi}",label_visibility="collapsed"); comment=st.text_input("COMMENTS / EVIDENCE",key=f"le-{si}-{qi}",placeholder="Enter comments / evidence",label_visibility="collapsed")
            rs.append({"section":section,"question":q,"response":ans,"comments_evidence":comment})
    positive=st.text_area("Positive Observations"); improvement=st.text_area("Opportunities for Improvement"); actions=st.text_area("Actions Agreed"); indicator=st.radio("Overall Control of Work Indicator",["Meets CoW Standard","Does not meet CoW Standard"],index=None); notes=st.text_area("Auditor Notes"); st.info("If one question is No / non-conforming, mark the overall indicator as Does not meet CoW Standard.")
    if st.button("Submit Leadership Engagement",type="primary",use_container_width=True):
        required=[r for r in rs if r["response"]!="Comment"]
        if site=="Select" or not auditor_role:st.error("Complete Location / Team and Auditor Role.")
        elif any(r["response"] is None for r in required):st.error("Every Yes/No question requires a response.")
        elif indicator is None:st.error("Select the Overall Control of Work Indicator.")
        else:
            meta={"site":site,"audit_date":str(ad),"auditor":"Anonymous","auditor_role":auditor_role,"site_controller":"Not captured","reference":"","positive_observations":positive,"opportunities_for_improvement":improvement,"actions_agreed":actions,"auditor_notes":notes,"overall_indicator":indicator}; st.success("Submitted: "+save_audit("Control of Work Leadership Engagement Checklist",meta,rs,indicator))
elif page=="Submitted Audits":
    st.header("Submitted Audits"); aa=audits(); df=pd.DataFrame([{**{k:a[k] for k in ["audit_id","submitted_at","form_name","audit_date","site","summary"]},"Auditor":"Anonymous","Reference":""} for a in aa]); st.dataframe(df,use_container_width=True,hide_index=True) if len(df) else st.info("No submissions yet.")
else:
    st.header("Dashboard Export"); flat=[]
    for a in audits():
        for r in a["responses"]:flat.append({"Audit ID":a["audit_id"],"Submitted At":a["submitted_at"],"Form":a["form_name"],"Audit Date":a["audit_date"],"Site / Installation":a["site"],"Auditor":"Anonymous","Reference":"","Section":r.get("section",""),"Question":r.get("question",""),"Response":r.get("response",""),"Comments / Evidence":r.get("comments_evidence",""),"SMART Action":r.get("smart_action",""),"Overall Indicator":a["summary"]})
    if flat:
        df=pd.DataFrame(flat); st.dataframe(df.head(100),use_container_width=True,hide_index=True); st.download_button("Download dashboard-ready CSV",df.to_csv(index=False).encode("utf-8-sig"),"Operational_Assurance_Export.csv","text/csv",use_container_width=True)
    else:st.info("Submit a test audit first.")
