# Operational Assurance – Control of Work

Anonymous Streamlit demonstrator for a Control of Work operational assurance system.

The application combines Level 4 assurance forms, structured evidence capture, SMART actions, KPI calculations and leadership reporting in a single demonstrator. It is deliberately client-neutral and uses generic asset and team names.

## Included

- Permit Quality assurance form
- Toolbox Talk / Permit / POP assurance form with activity branching
- Leadership Engagement checklist
- Persistent PostgreSQL demo data store (SQLite fallback for local development)
- Persistent KPI role mapping
- Five Control of Work KPI cards and RAG logic
- Company and site/group performance comparison
- Findings and SMART actions view
- Work as Imagined vs Work as Done view
- Auditor / leadership view
- KPI 5 manual incident summary
- Submitted audits register
- Dashboard-ready CSV export
- Synthetic demonstration data

## Run

Install the requirements and start Streamlit with:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The deployed demo reads `DATABASE_URL` from Streamlit Secrets and stores every submitted audit, KPI 5 result and role mapping in PostgreSQL. If `DATABASE_URL` is not configured, the local `assurance.db` file is created automatically for local development.

## Important

This repository is a development and demonstration application. The PostgreSQL connection provides persistent storage for demonstration and UAT. It is not a substitute for the organisation's production authentication, security architecture, backup policy or enterprise integrations. Production hosting, authentication, security, database architecture, backup and enterprise integrations should be defined by the organisation deploying the application.

The KPI logic intentionally avoids inventing thresholds where the underlying assurance criteria require management judgement. Synthetic demonstration records are identifiable by the `DEMO-` prefix.
