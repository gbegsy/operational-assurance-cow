# Operational Assurance – Control of Work

Anonymous Streamlit demonstrator for a Control of Work operational assurance system.

The application combines Level 4 assurance forms, structured evidence capture, SMART actions, KPI calculations and leadership reporting in a single demonstrator. It is deliberately client-neutral and uses generic asset and team names.

## Included

- Permit Quality assurance form
- Toolbox Talk / Permit / POP assurance form with activity branching
- Leadership Engagement checklist
- SQLite UAT data store
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

The local `assurance.db` file is created automatically when the application first runs.

## Important

This repository is a development and demonstration application. The included SQLite database is suitable for local/UAT demonstration rather than a production corporate deployment. Production hosting, authentication, security, database architecture, backup and enterprise integrations should be defined by the organisation deploying the application.

The KPI logic intentionally avoids inventing thresholds where the underlying assurance criteria require management judgement. Synthetic demonstration records are identifiable by the `DEMO-` prefix.
