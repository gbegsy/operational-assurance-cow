import streamlit as st
import pandas as pd
import json, uuid, calendar
from pathlib import Path
from datetime import date, datetime

BASE = Path(__file__).parent
DATA = json.loads((BASE / "questions.json").read_text(encoding="utf-8"))
# Streamlit in Snowflake supplies an authenticated Snowpark session.
session = st.connection("snowflake").session()
session.sql("USE DATABASE OPERATIONAL_ASSURANCE").collect()
session.sql("USE SCHEMA DEMO").collect()


class SnowflakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return [tuple(row) for row in self.rows]

    def fetchone(self):
        return tuple(self.rows[0]) if self.rows else None


class DatabaseConnection:
    """Compatibility layer used by the assurance application."""

    def execute(self, query, params=()):
        if query == "INSERT OR REPLACE INTO roles VALUES(?,?,?)":
            query = """
                MERGE INTO roles target
                USING (SELECT ? AS mapping_type, ? AS person_name, ? AS role_name) source
                ON target.mapping_type=source.mapping_type
                   AND target.person_name=source.person_name
                WHEN MATCHED THEN UPDATE SET role_name=source.role_name
                WHEN NOT MATCHED THEN INSERT(mapping_type,person_name,role_name)
                VALUES(source.mapping_type,source.person_name,source.role_name)
            """
        elif query.startswith("INSERT OR REPLACE INTO kpi5 VALUES("):
            record_id = params[0]
            session.sql("DELETE FROM kpi5 WHERE record_id=?", params=[record_id]).collect()
            query = query.replace("INSERT OR REPLACE INTO", "INSERT INTO")
        rows = session.sql(query, params=list(params)).collect()
        return SnowflakeResult(rows)

    def commit(self):
        pass

    def close(self):
        pass

st.set_page_config(page_title="Perenco UK - Control of Work Assurance", page_icon="🔒", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:1.5rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#f7f9fb,#edf2f6);border-right:1px solid #d8e1e7}
[data-testid="stSidebar"] div[role="radiogroup"] label{background:#fff;border:1px solid #d7e1e8;border-radius:9px;padding:8px 10px;margin:2px 0}
.oa-banner{background:#000;color:#fff;min-height:118px;display:flex;align-items:center;justify-content:center;text-align:center;margin-bottom:8px}
.oa-title{font-size:23px;font-weight:800;line-height:1.35;padding:20px}.oa-sub{font-size:20px;margin-top:8px}
.purpose{border:1px solid #222;padding:9px 11px;font-size:13px;line-height:1.4;margin-bottom:8px;background:#fff}
.blackbar{background:#000;color:#fff;font-weight:800;padding:7px 10px;margin-top:8px}.section-title{font-size:18px;font-weight:800;margin:16px 0 6px}.qrow{padding:8px 0 2px;font-size:15px}.bar{display:inline-block;border-radius:4px;padding:2px 7px;margin-left:7px;font-size:10px;font-weight:800;color:#fff}.bar1{background:#c62828}.bar2{background:#e67e22}.bar3{background:#62a744}
.dash{background:#1d3d5c;color:#fff;margin:-1.5rem -3rem 22px;padding:24px 3rem 27px}.dash .eyebrow{font-size:11px;font-weight:800;letter-spacing:1.5px;color:#a9d8ff}.dash h1{font-size:31px;margin:18px 0 12px}.dash p{margin:0;color:#fff}.selection{border-left:4px solid #347ec8;background:#eaf5fc;padding:11px 14px;margin:12px 0 16px;color:#16364b}.section-head{font-size:22px;font-weight:800;color:#102b40;margin:18px 0 12px}
.kpi{background:#fff;border:1px solid #d8e2e8;border-left:5px solid #a8b7c2;border-radius:12px;padding:15px 15px 14px;min-height:188px;box-shadow:0 3px 12px rgba(20,50,70,.06)}.kpi.green{border-left-color:#2f9e62}.kpi.amber{border-left-color:#c88718}.kpi.red{border-left-color:#cf4c45}.kt{font-size:11px;font-weight:800;color:#55718a}.kv{font-size:29px;font-weight:800;color:#102b40;margin:13px 0 8px}.kd{font-size:11px;color:#657a88;line-height:1.4;margin-top:7px}.ks{font-size:15px;font-weight:600;color:#102b40;margin-top:6px}.badge{display:inline-block;border-radius:999px;padding:3px 10px;font-size:10px;font-weight:800;background:#edf1f4;color:#526775}.badge.green{background:#e3f4e9;color:#16733d}.badge.amber{background:#fff0cf;color:#9b6100}.badge.red{background:#fde7e5;color:#a62d26}.exec{background:#fff;border:1px solid #d8e2e8;border-radius:12px;padding:17px 19px;margin:14px 0}.exec h3{margin:0 0 5px;color:#16364b}.focus{border-left:4px solid #1679c4;background:#f4f9fc;padding:10px 12px;margin-top:10px}
</style>
""", unsafe_allow_html=True)

SITE_GROUPS = {
    "Dimlington": (1,1),
    "Cleeton": (1,1),
    "Ravenspurn North": (1,1),
    "Northern NUIs": (2,1),
    "Bacton": (1,1),
    "Leman 27BC": (1,1),
    "Southern NUIs": (2,1),
}
ASSET_GROUPS = list(SITE_GROUPS)


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

def role_map(kind):
    c=db(); r=dict(c.execute("SELECT person_name,role_name FROM roles WHERE mapping_type=?",(kind,)).fetchall()); c.close(); return r

def set_role(kind,name,role):
    c=db(); c.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?)",(kind,name,role)); c.commit(); c.close()

def banner(title,sub=""):
    s=f'<div class="oa-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="oa-banner"><div class="oa-title">{title}{s}</div></div>',unsafe_allow_html=True)

def purpose(text): st.markdown(f'<div class="purpose"><b>PURPOSE:</b> {text}</div>',unsafe_allow_html=True)

def bar_review():
    with st.expander("BAR review criteria"):
        st.markdown("**BAR 1 — Critical controls:** MAH, loss of containment, isolations, gas testing, authorisation, emergency response and stop-work decisions.")
        st.markdown("**BAR 2 — Key operational controls:** permit quality, hazard identification, task planning, control implementation, Toolbox Talks, supervision and procedural compliance.")
        st.markdown("**BAR 3 — Supporting assurance:** planning evidence, records, document administration, workforce perception and continuous improvement.")

def questions(prefix,sections):
    out=[]
    for si,(section,qs) in enumerate(sections):
        st.markdown(f'<div class="section-title">{section}</div>',unsafe_allow_html=True)
        for qi,item in enumerate(qs):
            letter,q,bar=item
            bar_class=bar.lower().replace(" ","")
            st.markdown(f'<div class="qrow"><b>{letter}</b> {q}<span class="bar {bar_class}">{bar}</span></div>',unsafe_allow_html=True)
            c1,c2=st.columns([1,2]); ans=c1.selectbox("Response",["Select","Yes","No","N/A"],key=f"{prefix}-{si}-{qi}",label_visibility="collapsed"); placeholder="If No selected, add SMART action" if ans=="No" else "Add SMART action where required"; act=c2.text_input("SMART ACTION",placeholder=placeholder,key=f"act-{prefix}-{si}-{qi}",label_visibility="collapsed")
            out.append({"section":section,"item":letter,"bar_rating":bar,"question":q,"response":None if ans=="Select" else ans,"smart_action":act})
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
    if m.get("new_wcc") and not m.get("routine"):return "New WCC"
    return "Unclassified"

def weeks(y,m): return sum(1 for w in calendar.monthcalendar(y,m) if w[calendar.MONDAY])
def rag(plan,conf):
    if (plan is not None and plan<70) or (conf is not None and conf<70):return "Red"
    if plan is None or conf is None:return "Not enough data"
    if plan>=100 and conf>=90:return "Green"
    return "Amber"
def css(s): return {"Green":"green","Amber":"amber","Red":"red","Needs review":"amber"}.get(s,"")

def card(name,title,value,status,detail):
    badge=status.upper() if status!="Not enough data" else "NOT ASSESSED"
    st.markdown(f'<div class="kpi {css(status)}"><div class="kt">{name}</div><div class="ks">{title}</div><div class="kv">{value}</div><span class="badge {css(status)}">{badge}</span><div class="kd">{detail}</div></div>',unsafe_allow_html=True)

def dual_card(name,title,completion,compliance,status,detail):
    badge=status.upper() if status!="Not enough data" else "NOT ASSESSED"
    st.markdown(f'<div class="kpi {css(status)}"><div class="kt">{name}</div><div class="ks">{title}</div><div class="kv">{completion}</div><span class="badge {css(status)}">{badge}</span><div class="kd">Audit completion<br>Question compliance {compliance}</div></div>',unsafe_allow_html=True)

def intervention(status):
    return {
        "Green": "No intervention required.",
        "Amber": "Site Leadership intervention required to identify improvements and address emerging trends.",
        "Red": "Immediate management intervention required; improvement actions to be implemented within one month.",
    }.get(status, "")

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
    add("DEMO-PQ1","Control of Work: Permit Quality","Dimlington","Demo Site Controller",{"routine":True,"new_wcc":False},yes)
    add("DEMO-PQ2","Control of Work: Permit Quality","Dimlington","Demo Site Controller",{"routine":False,"new_wcc":True},no)
    add("DEMO-PQ3","Control of Work: Permit Quality","Ravenspurn North","Demo Asset Superintendent",{"routine":True,"new_wcc":False},yes)
    add("DEMO-TBT1","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Northern NUIs","Demo W2W OOE",{"activity_type":"Routine"},no)
    add("DEMO-TBT2","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Southern NUIs","Demo Medic HSEA",{"activity_type":"Routine"},yes)
    add("DEMO-TBT3","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Leman 27BC","Demo Field Hub OIM",{"activity_type":"Routine"},yes)
    add("DEMO-LEAD1","Control of Work Leadership Engagement Checklist","Northern NUIs","Demo Operations Director",{},yes,"Meets CoW Standard")
    add("DEMO-LEAD2","Control of Work Leadership Engagement Checklist","Southern NUIs","Demo Operations Director",{},yes,"Meets CoW Standard")
    for x in [("permit","Demo Site Controller","Site Controller"),("permit","Demo Asset Superintendent","Asset Superintendent"),("tbt","Demo W2W OOE","W2W OOE"),("tbt","Demo Medic HSEA","Medic HSEA"),("tbt","Demo Field Hub OIM","Field Hub OIM"),("lead","Demo Operations Director","Operations Director")]:c.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?)",x)
    c.execute("INSERT OR REPLACE INTO kpi5 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("DEMO-KPI5",now,d[:7],"All",1,0,0,0,1,0,"Yes","No","No","Synthetic trial value",1)); c.commit(); c.close()

def dashboard():
    st.markdown('<div class="dash"><div class="eyebrow">PERENCO UK | OPERATIONAL ASSURANCE</div><h1>Control of Work KPI Dashboard</h1><p>Monthly performance, cumulative visibility and leadership oversight</p></div>',unsafe_allow_html=True)
    all_a=audits()
    with st.container(border=True):
        c1,c2,c3=st.columns(3); md=c1.date_input("PERIOD VIEW",date.today().replace(day=1)); c2.selectbox("REPORTING BASIS",["Monthly KPI review"])
        y,m=md.year,md.month; period=md.strftime("%Y-%m"); month=[a for a in all_a if safe_date(a["audit_date"]) and safe_date(a["audit_date"]).year==y and safe_date(a["audit_date"]).month==m]
        sites=sorted({a["site"] for a in month if a["site"]}); site=c3.selectbox("ASSET / REGION",["All assets and teams"]+sites)
    site="All" if site=="All assets and teams" else site
    st.markdown(f'<div class="selection">Showing: {md.strftime("%B %Y")} only &nbsp;|&nbsp; Monthly KPI review &nbsp;|&nbsp; {"All assets and teams" if site=="All" else site}</div>',unsafe_allow_html=True)
    view=month if site=="All" else [a for a in month if a["site"]==site]
    permit=[a for a in view if a["form_name"]=="Control of Work: Permit Quality"]; tbt=[a for a in view if "Toolbox Talk" in a["form_name"]]; lead=[a for a in view if "Leadership Engagement" in a["form_name"]]
    pmap,tmap,lmap=role_map("permit"),role_map("tbt"),role_map("lead")
    # Default unmapped auditors by audit family so existing records feed the
    # dashboard immediately. An explicit saved role always takes precedence.
    for a in permit:
        if a["auditor"] and a["auditor"] not in pmap:pmap[a["auditor"]]="Site Controller"
    for a in tbt:
        if a["auditor"] and a["auditor"] not in tmap:tmap[a["auditor"]]="W2W OOE"
    for a in lead:
        if a["auditor"] and a["auditor"] not in lmap:lmap[a["auditor"]]="Operations Director"
    with st.expander("KPI role configuration"):
        specs=[("permit",permit,["Site Controller","Asset Superintendent","Other"],pmap),("tbt",tbt,["W2W OOE","Medic HSEA","Field Hub OIM","Other"],tmap),("lead",lead,["Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager","Other"],lmap)]
        for kind,rows,opts,current_map in specs:
            for n in sorted({a["auditor"] for a in rows if a["auditor"]}):
                cur=current_map.get(n,"Other"); val=st.selectbox(n,opts,index=opts.index(cur) if cur in opts else len(opts)-1,key=f"r-{kind}-{n}")
                if val!=cur:set_role(kind,n,val)
    gov=governance(period,site); w=weeks(y,m)
    sc=[a for a in permit if pmap.get(a["auditor"])=="Site Controller"]; asc=[a for a in permit if pmap.get(a["auditor"])=="Asset Superintendent"]
    k1plan=(sum(a+b for a,b in SITE_GROUPS.values())*w) if site=="All" else ((sum(SITE_GROUPS.get(site,(0,0)))*w) or None); k1done=len([a for a in sc if permit_type(a)!="Unclassified"]); k1p=round(100*k1done/k1plan) if k1plan else None; k1c=q_conf(sc); k1s=rag(k1p,k1c)
    k2plan=w; k2done=len([a for a in asc if permit_type(a)!="Unclassified"]); k2p=round(100*k2done/k2plan) if k2plan else None; k2c=audit_conf(asc); k2s=rag(k2p,k2c) if asc else "Not enough data"; k2cov=len({a["site"] for a in asc if a["site"]})
    q=(m-1)//3+1; qstart=date(y,(q-1)*3+1,1); qe=(q-1)*3+3; qend=date(y,qe,calendar.monthrange(y,qe)[1]); qlead=[a for a in all_a if "Leadership Engagement" in a["form_name"] and safe_date(a["audit_date"]) and qstart<=safe_date(a["audit_date"])<=qend and (site=="All" or a["site"]==site) and lmap.get(a["auditor"]) in {"Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager"}]; k3n=len(qlead); k3c=audit_conf(qlead); complete=date.today()>qend
    if not qlead:k3s="Not enough data"
    elif k3c is not None and k3c<70:k3s="Red"
    elif k3n>=3 and k3c>=90 and gov["kpi3_coverage"]=="Reasonable":k3s="Green"
    elif complete:k3s="Red" if k3n<=1 else "Amber"
    else:k3s="In progress" if k3c and k3c>=90 else "Amber"
    mapped=[a for a in tbt if tmap.get(a["auditor"]) in {"W2W OOE","Medic HSEA","Field Hub OIM"}]; counts={r:sum(tmap.get(a["auditor"])==r for a in mapped) for r in ["W2W OOE","Medic HSEA","Field Hub OIM"]}; oo=round(100*counts["W2W OOE"]/w) if w else 0; med=round(100*counts["Medic HSEA"]/w) if w else 0; k4c=audit_conf(mapped)
    if not mapped:k4s="Not enough data"
    elif oo<50 or med<50 or (k4c is not None and k4c<70) or gov["kpi4_findings"]=="Significant / repeat":k4s="Red"
    elif 50<=med<75:k4s="Needs review"
    elif oo<100 or med<100 or (k4c is not None and k4c<90):k4s="Amber"
    else:k4s="Green"
    c=db(); k5rows=c.execute("SELECT * FROM kpi5 WHERE reporting_month=? ORDER BY submitted_at",(period,)).fetchall(); c.close(); k5=k5rows[-1] if k5rows else None
    if not k5:k5s="Not enough data"; k5v="—"; k5detail="Enter monthly incident summary"
    else:
        current,prev,hipo,inj,loc,major,repeat,recurring,sig=k5[4],k5[5],k5[6],k5[7],k5[8],k5[9],k5[10],k5[11],k5[12]
        k5s="Red" if sig=="Yes" or hipo>=2 or inj>=2 or major>=1 or recurring=="Yes" else ("Amber" if current>prev or hipo==1 or inj==1 or loc>=1 or repeat=="Yes" else "Green"); k5v=str(current); k5detail=f"Previous {prev} · HiPO {hipo} · MTC+ {inj} · LOC {loc}"
    statuses=[k1s,k2s,k3s,k4s,k5s]; assessed=[x for x in statuses if x in ("Green","Amber","Red")]; overall="Red" if "Red" in assessed else ("Amber" if "Amber" in assessed else ("Green" if len(assessed)==5 else "Not enough data"))
    st.markdown(f'<div class="exec"><h3>Overall Control of Work position: {overall.upper()}</h3><div>Results reflect the selected reporting month and asset or team view.</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-head">Five KPI results</div>',unsafe_allow_html=True)
    cols=st.columns(5)
    k1new=sum(permit_type(a)=="New WCC" for a in sc); k1routine=sum(permit_type(a)=="Routine" for a in sc)
    k1detail=(f"**Completed:** {k1done}/{k1plan or '—'}  <br>"
              f"**WCC classification:** New WCC {k1new} · Routine WCC {k1routine}  <br>"
              f"**Target:** 16 per week / 64 per 4 weeks  <br>"
              f"**Required response:** {intervention(k1s)}")
    with cols[0]:dual_card("KPI 1","Site Controller Permit Assurance",f"{k1p}%" if k1p is not None else "—",f"{k1c}%" if k1c is not None else "—",k1s,k1detail)
    with cols[1]:card("KPI 2","Asset Superintendent Permit Non-Compliance",f"{k2c}%" if k2c is not None else "—",k2s,f"Plan {k2done}/{k2plan} · coverage {k2cov}/9")
    with cols[2]:card("KPI 3","Leadership Engagement",f"{k3n}/3" if qlead else "—",k3s,f"Q{q} · {k3c if k3c is not None else '—'}% conformance")
    with cols[3]:card("KPI 4","Site Leadership Visits",f"{k4c}%" if k4c is not None else "—",k4s,f"OOE {counts['W2W OOE']}/{w} · HSEA {counts['Medic HSEA']}/{w}")
    with cols[4]:card("KPI 5","Permit-Controlled Incidents",k5v,k5s,k5detail)
    with st.expander("KPI 1 · Site Controller details"):
        st.markdown(k1detail,unsafe_allow_html=True)
    with st.expander("KPI definitions, tolerances and role configuration"):
        st.markdown("The overall position follows the most adverse assessed KPI. KPI 1 combines completion against plan with compliance across applicable audit questions.")
        st.markdown(f"**Leadership focus:** {intervention(overall)}")
    tabs=st.tabs(["Company & Site Performance","Findings & Actions","Work as Imagined vs Work as Done","Auditor View","KPI 5 Data"])
    with tabs[0]:
        st.subheader("Monthly performance by asset / group"); rows=[]
        month_permit=[a for a in month if a["form_name"]=="Control of Work: Permit Quality" and pmap.get(a["auditor"])=="Site Controller"]
        for g,(rw,nw) in SITE_GROUPS.items():
            aa=[a for a in month_permit if a["site"]==g]; done=len([a for a in aa if permit_type(a)!="Unclassified"]); plan=(rw+nw)*w; pc=round(100*done/plan) if plan else None; cf=q_conf(aa); rows.append({"Site / Group":g,"Routine WCC":sum(permit_type(a)=="Routine" for a in aa),"New WCC":sum(permit_type(a)=="New WCC" for a in aa),"Planned":plan,"Completed":done,"Completion %":pc,"Audit-question compliance %":cf,"RAG":rag(pc,cf)})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); st.caption(f"Monthly demonstration basis: {w} reporting weeks. New WCC and Routine WCC samples remain separate.")
    with tabs[1]:
        rows=[]
        for a in permit+tbt+lead:
            for r in a["responses"]:
                if str(r.get("response","")).lower()=="no":rows.append({"Site":a["site"],"Auditor":a["auditor"],"Form":a["form_name"],"BAR":r.get("bar_rating",""),"Finding":r.get("question",""),"Action":r.get("smart_action") or r.get("comments_evidence","")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True) if rows else st.success("No negative assurance responses in this view.")
    with tabs[2]:
        st.markdown("**Work as Imagined** — the question sets represent the expected Control of Work standard and intended controls."); c1,c2,c3=st.columns(3); c1.metric("Question conformance",f"{q_conf(permit+tbt)}%" if q_conf(permit+tbt) is not None else "—"); c2.metric("Permit whole-audit conformance",f"{audit_conf(permit)}%" if audit_conf(permit) is not None else "—"); c3.metric("TBT/POP whole-audit conformance",f"{audit_conf(tbt)}%" if audit_conf(tbt) is not None else "—")
    with tabs[3]:
        rr=[]
        for n in sorted({a["auditor"] for a in permit+tbt+lead if a["auditor"]}):
            aa=[a for a in permit+tbt+lead if a["auditor"]==n]; rr.append({"Auditor / Leader":n,"Activities":len(aa),"Question conformance %":q_conf(aa),"Whole-audit conformance %":audit_conf(aa),"Sites / Teams":", ".join(sorted({a["site"] for a in aa if a["site"]}))})
        st.dataframe(pd.DataFrame(rr),use_container_width=True,hide_index=True) if rr else st.info("No auditor data.")
    with tabs[4]:
        st.subheader("KPI 5 · Monthly incident summary"); a,b,c=st.columns(3); current=a.number_input("Rolling 12-month permit-controlled incidents",0,999,0); prev=b.number_input("Previous rolling 12-month incidents",0,999,0); hipo=c.number_input("HiPO events",0,999,0); a,b,c=st.columns(3); injury=a.number_input("Significant injuries (MTC+)",0,999,0); loc=b.number_input("Loss of Containment",0,999,0); major=c.number_input("Major Loss of Containment",0,999,0); a,b,c=st.columns(3); repeat=a.selectbox("Repeat event theme?",["No","Yes"]); recurring=b.selectbox("Recurring permit-control failure?",["No","Yes"]); sig=c.selectbox("Significant increase?",["No","Yes"],help="No numerical threshold is assumed; use the agreed management assessment."); comments=st.text_area("Comment / source note")
        if st.button("Save KPI 5 result",type="primary"):
            rid="KPI5-"+uuid.uuid4().hex[:8].upper(); con=db(); con.execute("INSERT INTO kpi5 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,datetime.now().isoformat(timespec="seconds"),period,site,current,prev,hipo,injury,loc,major,repeat,recurring,sig,comments,0)); con.commit(); con.close(); st.success("KPI 5 result saved.")

st.sidebar.markdown("### Operational Assurance")
page=st.sidebar.radio("Navigation",["Dashboard","Permit Quality","Toolbox Talk / Permit / POP","Leadership Engagement","Submitted Audits","Dashboard Export"],label_visibility="collapsed")

if page=="Dashboard": dashboard()
elif page=="Permit Quality":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work: Permit Quality")
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1]); site=c1.text_input("SITE / INSTALLATION:"); team=c2.text_input("TEAM:"); ad=c3.date_input("DATE OF AUDIT:",date.today()); nw=c4.checkbox("New WCC")
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1]); auditor=c1.text_input("AUDITOR:"); sc=c2.text_input("SITE CONTROLLER:"); ref=c3.text_input("WCC NUMBER:"); routine=c4.checkbox("Routine"); desc=st.text_input("WCC DESCRIPTION:")
    meta={"site":site,"team":team,"audit_date":str(ad),"auditor":auditor,"site_controller":sc,"reference":ref,"wcc_description":desc,"new_wcc":nw,"routine":routine}
    purpose("Self-verify the quality of a planned or active Work Control Certificate (WCC), including permit preparation, hazard identification, risk assessment, control selection, authorisation and worksite readiness."); bar_review(); st.markdown('<div class="blackbar">QUESTION</div>',unsafe_allow_html=True); rs=questions("ptw",DATA["ptw"]); st.markdown('<div class="blackbar">ENSURE EACH NON-COMPLIANCE GENERATES A RECORDED SMART ACTION</div>',unsafe_allow_html=True)
    if st.button("Submit Permit Quality Audit",type="primary",use_container_width=True):
        if not site or not auditor:st.error("Complete SITE / INSTALLATION and AUDITOR.")
        elif nw==routine:st.error("Select exactly one classification: New WCC or Routine.")
        elif any(r["response"] is None for r in rs):st.error("Every question requires a response.")
        else:st.success("Submitted: "+save_audit("Control of Work: Permit Quality",meta,rs))
elif page=="Toolbox Talk / Permit / POP":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures")
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1]); site=c1.text_input("SITE / INSTALLATION:"); team=c2.text_input("TEAM:"); ad=c3.date_input("DATE OF AUDIT:",date.today()); activity=c4.radio("TYPE",["New WCC","Routine","POP"],index=None)
    c1,c2,c3=st.columns(3); auditor=c1.text_input("AUDITOR:"); sc=c2.text_input("SITE CONTROLLER:"); ref=c3.text_input("WCC / POP No:"); desc=st.text_input("DESCRIPTION:"); meta={"site":site,"team":team,"audit_date":str(ad),"auditor":auditor,"site_controller":sc,"reference":ref,"description":desc,"activity_type":activity}
    purpose("Self-verify day-to-day Toolbox Talk, permit and operating-procedure compliance, workforce understanding and implementation of Control of Work requirements."); bar_review(); st.markdown('<div class="blackbar">QUESTION · SITE VISIT REQUIRED · SEQUENTIAL REVIEW</div>',unsafe_allow_html=True); rs=questions("tbt12",DATA["tbt"][:2]); st.markdown('<div class="blackbar">AUDITING A POP? MOVE TO QUESTION 8</div>',unsafe_allow_html=True); rs += questions("pop",[DATA["pop"]]) if activity=="POP" else questions("tbt37",DATA["tbt"][2:])+questions("tbt8",[DATA["pop"]])
    if st.button("Submit TBT / Permit / POP Audit",type="primary",use_container_width=True):
        if not site or not auditor or not activity:st.error("Complete SITE / INSTALLATION, AUDITOR and TYPE.")
        elif any(r["response"] is None for r in rs):st.error("Every displayed question requires a response.")
        else:st.success("Submitted: "+save_audit("Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures",meta,rs))
elif page=="Leadership Engagement":
    banner("Control of Work Leadership Engagement Checklist"); c1,c2,c3,c4=st.columns([1,2,1.4,1.7]); ad=c1.date_input("Date",date.today()); site=c2.text_input("Location / Team"); sc=c3.text_input("Site Controller"); leader=c4.text_input("Leadership Representative"); purpose("Provide a predefined set of Control of Work questions for leadership engagement visits, supporting visible leadership, workforce engagement and assurance discussions."); rs=[]
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
        if not site or not leader:st.error("Complete Location / Team and Leadership Representative.")
        elif any(r["response"] is None for r in required):st.error("Every Yes/No question requires a response.")
        elif indicator is None:st.error("Select the Overall Control of Work Indicator.")
        else:
            meta={"site":site,"audit_date":str(ad),"auditor":leader,"site_controller":sc,"reference":"","positive_observations":positive,"opportunities_for_improvement":improvement,"actions_agreed":actions,"auditor_notes":notes,"overall_indicator":indicator}; st.success("Submitted: "+save_audit("Control of Work Leadership Engagement Checklist",meta,rs,indicator))
elif page=="Submitted Audits":
    st.header("Submitted Audits"); aa=audits(); df=pd.DataFrame([{k:a[k] for k in ["audit_id","submitted_at","form_name","audit_date","site","auditor","reference","summary"]} for a in aa]); st.dataframe(df,use_container_width=True,hide_index=True) if len(df) else st.info("No submissions yet.")
else:
    st.header("Dashboard Export"); flat=[]
    for a in audits():
        for r in a["responses"]:flat.append({"Audit ID":a["audit_id"],"Submitted At":a["submitted_at"],"Form":a["form_name"],"Audit Date":a["audit_date"],"Site / Installation":a["site"],"Auditor":a["auditor"],"Reference":a["reference"],"Section":r.get("section",""),"Question Ref":r.get("item",""),"BAR Rating":r.get("bar_rating",""),"Question":r.get("question",""),"Response":r.get("response",""),"Comments / Evidence":r.get("comments_evidence",""),"SMART Action":r.get("smart_action",""),"Overall Indicator":a["summary"]})
    if flat:
        df=pd.DataFrame(flat); st.dataframe(df.head(100),use_container_width=True,hide_index=True); st.download_button("Download dashboard-ready CSV",df.to_csv(index=False).encode("utf-8-sig"),"Operational_Assurance_Export.csv","text/csv",use_container_width=True)
    else:st.info("Submit a test audit first.")
