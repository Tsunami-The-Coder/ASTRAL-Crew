# Team plan and handoffs

| Owner | Scope | Handoff |
| --- | --- | --- |
| Anuj | Streamlit UI/UX, cockpit, screens, SVG hazard selector | Reads backend JSON and presents evidence clearly |
| Aarika | SQLite, simulated telemetry, event logs, interface | Publishes stable JSON schema and storage layer |
| Eleni | NASA references, WESAD/SUSAS access, provenance, research | Data inventory, verified licenses, evidence citations |
| Khalid | EDA/HRV/motion processing and biometric stress inference | Structured inference result with uncertainty/limitations |
| Ben | Speech filtering, feature extraction, voice inference | Structured inference result with uncertainty/limitations |
| Colin | Fusion, crew correlation rules, sensor sanity checks, QA | Crew-level assessments, tests, demo event interpretation |

## Checkpoints
- Nov 13: agree on data contract, dataset availability, screen wireframes, responsibilities
- Nov 14: implement individual workstreams, integrate early, validate demo flow
- Nov 15: end-to-end testing, record demo, finalize documentation and submit

## Demo sequence
1. Nominal four-person crew.
2. Cabin CO2 rise and multiple crew changes.
3. Voice/biometric disagreement requiring verification.
4. Human-reviewed suggested actions, event log and export.

## Done means
A reviewer can run the app offline with bundled permitted or synthetic samples; every graph has units and data provenance; simulation labels are visible; team contributions and NASA sources are credited.
