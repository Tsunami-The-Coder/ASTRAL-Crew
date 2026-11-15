# ASTRAL-Crew — Instructions for AI Coding Agents

> Shared project instructions for ChatGPT, Codex, Claude Code, Cursor, Copilot, and other AI coding assistants. Read this file before proposing or modifying code. These instructions apply repository-wide.

## 1. Mission and boundaries

ASTRAL-Crew (Autonomous Spaceflight Health & Crew Resilience) is a **software-only, offline-first NASA Space Apps 2026 prototype** for a simulated four-person Mars mission. It explores health trends, environmental telemetry, research-based stress indicators, and **human-reviewed** decision support. It is not a medical device or a flight-certified autonomous controller.

The five hazard areas are radiation, gravity adaptation, habitat health, autonomous medical support, and cognitive/mental health. Planned screens: Mission Control, Crew Health Twins, Cognitive AI, Five Hazards, Crew Diagnostics, and Mission Logs.

**Build-window rule:** Before the officially permitted hackathon implementation window, limit work to planning, research, access checks, documentation, wireframes, and coordination. Do not generate or commit implementation code early. Confirm the event rules with the team rather than assuming a start time.

## 2. Read these files first, in order

1. `README.md` — scope, screens, roles, timeline.
2. `CONTRIBUTING.md` — branching, review, safety and data rules.
3. `docs/DATA_CONTRACT.md` — proposed shared telemetry and model handoffs.
4. `docs/TEAM_PLAN.md` and `docs/DATA_SOURCES.md` when relevant.
5. The actual files in the assigned workstream, plus its tests.

**Important:** `docs/DATA_CONTRACT.md` is currently a **proposal**. Do not treat its example as a fully implemented or team-approved API. Flag unspecified fields, units, nullability, timestamps, score semantics, and versioning. Obtain team agreement before changing shared interfaces.

## 3. Workstream ownership

| Owner | Primary paths | Responsibilities |
|---|---|---|
| UI lead | `ui/` | Streamlit/Plotly UI, body map, product integration |
| backend lead | `backend/` | Synthetic mission telemetry, SQLite, logs, orchestration |
| research lead | `research/`, `data/` | Dataset provenance, scientific sources, preprocessing |
| wearable lead | `models/wearable/` | Wearable stress features and model |
| voice lead | `models/voice/` | Voice features and model |
| integration lead | `fusion/`, `tests/` | Multimodal fusion, crew-wide anomaly rules, QA |

Paths indicate intended ownership; create subfolders only when implementation is permitted and needed. Coordinate before changing another owner's files. Shared files (root config, dependencies, contracts, app entry points) require explicit cross-team review.

## 4. Mandatory AI-agent workflow

**Before writing:**
1. Inspect repository state and relevant code; never assume a function or dependency exists.
2. State your assigned task, intended files, inputs/outputs, dependencies, and acceptance tests.
3. Compare intended interfaces with the current data contract. If ambiguous or conflicting, ask the owner; do not silently invent a new contract.
4. Make a small implementation plan and identify any cross-owner changes.

**While writing:**
1. Keep changes scoped and modular; prefer small pure functions and explicit adapters.
2. Preserve existing public interfaces unless a coordinated contract change is approved.
3. Use dependency injection or mock/stub inputs to work independently of unfinished components.
4. Do not regenerate, overwrite, or refactor unrelated teammates' code.
5. Keep dependencies minimal and compatible with the shared Python environment.
6. Handle missing inputs, sensor faults, malformed data, and unavailable models explicitly.
7. Label demo data and simulated inference; do not fabricate validation metrics.

**Before handing off:**
1. Run the relevant tests and describe the actual command and result; never claim unrun tests passed.
2. Check schema, types, units, timestamps, missing-data behavior, and offline operation.
3. Summarize changed files, dependencies, assumptions, limitations, and integration points.
4. Open a small pull request with test evidence; do not directly merge into `main`.

## 5. Shared interfaces and data provenance

Use `docs/DATA_CONTRACT.md` as the starting point for discussion. Its proposed telemetry fields include `timestamp` (ISO 8601 UTC), `mission_day`, `crew_id`, `data_origin`, `biometrics`, `voice`, `environment`, and `assessment`.

- Use consistent crew IDs (e.g. `AST-01` through `AST-04`) and explicit units.
- Never silently rename fields or change types, scales, or score meanings.
- Voice and wearable model handoffs must identify source, model version, timestamp, output score/label, and limitations once the contract is approved.
- Keep **missing**, **invalid**, and **normal** readings distinct; never replace missing signals with a fabricated normal reading.
- Do not assume independent voice and wearable datasets are synchronized or have shared labels.
- Clearly distinguish **measured/research**, **replayed**, **synthetic**, and **simulated inference**. Document transformations and licensing.
- Keep environmental correlation separate from causal conclusions. A cross-crew pattern should trigger investigation, not a diagnosis.
- Never execute or portray safety-critical spacecraft actions as autonomous real-world overrides. Recommendations and interventions are simulated and human-reviewed.

If the team revises a contract: update its documentation, mocks, producer/consumer tests, and affected teammates **together**.

## 6. Architecture and integration

Preferred stack: Python, Streamlit, Plotly, pandas, SciPy/librosa, XGBoost where justified, SQLite. Treat this as the planned stack, not proof that packages or pipelines are installed.

Design a clear flow:
`research/synthetic inputs → voice + wearable models → fusion → backend/orchestration → Streamlit UI + logs`

Environmental telemetry may feed backend and fusion/diagnostics. The backend should expose a stable, testable interface; the UI should not import model training internals. Use mocks implementing the **same approved interface** until producers are ready.

For integration, inspect both sides first, connect existing exported functions, add only minimal adapters, and test success, missing data, malformed data, and sensor disagreement. Do not ask an AI agent to rewrite the entire app just to connect two modules.

## 7. Git and parallel AI development

- Create a short-lived `feature/<task>` branch from updated `main`; do not develop directly on `main`.
- Work on scoped files and commit focused changes. Do not use destructive Git commands, force-push, or rewrite teammates' history.
- Keep PRs small. State which interfaces changed and which teammates are affected.
- Coordinate edits to shared files, particularly `requirements.txt`, `pyproject.toml`, `docs/DATA_CONTRACT.md`, and the application entry point.
- Prefer regular integration over a final-day mega-merge.
- If merging causes conflicts, inspect both versions and ask the affected owners; never let an agent automatically discard a teammate's changes.

## 8. Testing and definition of done

Each workstream should supply, when implementation is permitted:
- A minimal reproducible local test or command.
- Representative mock inputs/outputs that match the agreed contract.
- Unit tests for core behavior and edge cases.
- Integration tests for upstream/downstream handoffs where available.
- Clear notes on dependencies, datasets, and offline fallback behavior.

End-to-end demo should cover four crew members, baseline health telemetry, a rising-CO₂ scenario, cross-crew stress indicators, an alert with **human-reviewed** next steps, a logged event, and a missing/faulty sensor scenario. Synthetic scenarios must be labeled as such.

**Done means:** runs locally, satisfies the agreed interface, has test evidence, does not break known integration paths, and is reviewable in a PR.

## 9. Security, science, and claims

- Never commit API keys, secrets, personal medical records, licensed audio, or large raw datasets.
- Follow dataset terms and document sources, license/access constraints, and preprocessing.
- WESAD supports research on physiological stress; SUSAS may require licensing; NASA mission audio is not automatically labeled for stress. Verify access before promising model training.
- Do not invent model accuracy, scientific citations, astronaut validation, or clinical claims.
- Use cautious terms such as **stress indicator**, **anomaly**, **possible association**, and **recommended review**.
- Ensure the demo remains useful without network access.

## 10. Required agent handoff format

At the end of each coding task, report:

- **Task / owner:**
- **Branch / PR:**
- **Files changed:**
- **Interfaces consumed / produced:**
- **Dependencies added:**
- **Tests run and actual results:**
- **Mock vs. real data:**
- **Known limitations / unresolved questions:**
- **Next integration owner:**

## 11. Tool-specific notes

This file is the shared source of guidance. Some assistants automatically read `AGENTS.md`; others do not. **Claude Code users should explicitly load this file into context or point their project's `CLAUDE.md` to it.** ChatGPT, Cursor, Copilot, and other assistants should likewise be instructed to read it. Tool-specific instructions must not contradict this file or the team-approved contract.

**Priority:** working, scientifically honest, integrated prototype > ambitious but disconnected AI-generated features.

## 12. Browser-only GitHub workflow (team preference)

**Use GitHub's website for all Git operations. Do not instruct teammates to use a terminal, Git CLI, or local Git commands unless they explicitly request them.** Browser-based AI development can use GitHub's file editor and, where available, github.dev or browser-based coding agents. Check the actual environment's capabilities; github.dev is an editor, not a full execution environment.

1. Open the repository on github.com and use the branch selector to create a `feature/<task>` branch from `main`.
2. Open the target file and click the pencil icon to edit; use **Add file → Create new file** for new files. For multi-file edits, use github.dev (press `.` while viewing the repo) or a supported web-based coding agent.
3. Choose **Commit changes** and enter a focused message, e.g. `feat(ui): add crew health cards`. Ensure the destination branch is your feature branch, not `main`.
4. Open **Pull requests → New pull request**, set base to `main` and compare to the feature branch, review the diff, and request a teammate's review.
5. Merge through the GitHub web UI only after contract compatibility and available checks are reviewed.
6. To bring new `main` changes into a feature branch, use the PR page's **Update branch** control when GitHub offers it. If unavailable or conflicts appear, coordinate through the GitHub conflict editor when supported; otherwise ask for help rather than overwriting code.
7. Review commits from the repository's **Commits** history, or a PR's **Commits** and **Files changed** tabs. To correct a recent file edit, make a new commit; do not rewrite shared history.

**Browser limitation:** Editing and committing on github.com does not run Python tests. AI agents must not report tests as passed without a real execution environment. If browser-based execution/CI is configured, report its actual results; otherwise mark tests **not run** and request integration verification.
