# ASTRAL Crew 🚀

**Adaptive Spaceflight Telemetry, Resilience & Astronaut Life-support Intelligence**  
NASA Space Apps Challenge 2026 · *Create Health Monitoring Software for Astronauts on Space Missions*

ASTRAL Crew is a local, interactive prototype showing how a crew on a long-duration space mission could **review changes in health and habitat signals, investigate possible patterns, and document human decisions**. It combines a five-member synthetic crew simulation, working voice/wearable research pipelines, mission logs, and a separately labeled NASA research-data view.

> **Important:** This is an educational, offline-first software demonstration. The crew readings, habitat scenarios, and stress-related examples are simulated. It is **not** a medical device, a clinical stress detector, or flight-certified spacecraft software. It neither receives live spacecraft/sensor data nor controls spacecraft systems.

## Quick start

You need **Python 3.11+**, a modern web browser, and an internet connection **for the first dependency installation only**. After setup, the local demo does not need an account, API key, or internet connection.

1. Download the **entire repository** (not only `ui/`). If you already have it, open a terminal at the repository root. To get this final branch from GitHub:

   ```bash
   git clone https://github.com/Tsunami-The-Coder/ASTRAL-Crew.git
   cd ASTRAL-Crew
   git switch final-end
   ```

2. **macOS (easiest):** launch the included setup/server script from the repository root:

   ```bash
   bash demo/run_demo.command
   ```

   It creates `.venv/` if needed, installs the two demo runtime packages, starts the Python server, and attempts to open the browser.

3. Open **http://127.0.0.1:8765/astral-prototype/** in your browser. Keep the server terminal running while using the app. Press **Ctrl+C** in that terminal to stop it.

### Run manually (macOS / Linux / Codespaces terminal)

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r demo/requirements-demo.txt
.venv/bin/python -m backend.demo_server --open-browser
```

If the browser does not open automatically, visit **http://127.0.0.1:8765/astral-prototype/** yourself. The app intentionally accepts only local-host requests; **a remotely forwarded Codespaces URL may receive HTTP 403**. A local machine/browser is the supported demo setup.

### Windows (PowerShell)

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r demo/requirements-demo.txt
.\.venv\Scripts\python.exe -m backend.demo_server
```

Then open **http://127.0.0.1:8765/astral-prototype/** in your browser. Use **Ctrl+C** to stop the server.

**Why a server?** The website lives in `ui/`, but it requests Python analysis routes and files stored under `submission/`. Opening the HTML file directly does not provide those connections.

## What to show in the demo

1. **Mission Control:** see the five simulated crew members and current synthetic cabin measurements.
2. **Crew:** select a member (`AST-01` through `AST-05`), review their history, and choose **Add entry**.
3. Select a voice sample and wearable window. Generate draft readings, inspect them, and **Submit & analyze** to run the local processing pipeline and save the check-in.
4. **Mission Control:** select a scenario such as **rising CO₂**, **voice/wearable disagreement**, **missing sensor**, **radiation rise**, or **oxygen drop**. Run the analysis and inspect what was flagged and why.
5. Inspect the **Cognitive**, **Habitat**, **Radiation**, **Gravity**, **Medical**, and **Mission Logs** views. Record a human review or export a report where offered.
6. Visit **Biology**, **Sources**, and **Method** to distinguish public NASA measurements from generated demonstration data and to review limitations.

All alerts are **review prompts**, not diagnoses or automatic emergency actions. A missing or invalid signal must remain *unavailable*; it must not be interpreted as a normal result.

## What the AI / analysis actually does

| Component | What runs locally | What it does **not** prove |
| --- | --- | --- |
| **Voice** | Processes audio with filtering and voice features (including pitch, MFCCs, and energy features), then compares supported examples with a speaker-specific synthetic calm baseline. | There is no astronaut-trained or medically validated stress classifier. |
| **Wearable** | Extracts features from generated wrist-style waveforms and applies the included WESAD-trained logistic research model. | The output is not a clinical probability and is not validated for astronauts. |
| **Multimodal analysis** | Combines available voice/wearable indicators with transparent backend rules. It can surface shared changes, disagreement, gaps, and possible associations with cabin scenarios. | Correlation does not establish cause; it does not independently diagnose a health problem. |
| **Mission record** | Saves synthetic check-ins, analysis results, review notes, and scenario history in a local SQLite database. | It is not a live, authenticated mission medical record or spacecraft control system. |

The demo also offers attributed NASA Artemis audio excerpts and RAVDESS acted speech examples for **audio feature exploration**. Those recordings are not automatically treated as synchronized wearable observations or verified astronaut stress labels.

## Where everything lives

| Folder | Purpose |
| --- | --- |
| `ui/astral-prototype/` | Website: HTML, CSS, JavaScript, crew dashboard, playback, and browser-to-server connection. |
| `submission/astral-prototype/audio/` | Bundled local audio and source/provenance manifests. |
| `submission/astral-prototype/data/` | Browser-facing research model data and source notes. |
| `submission/data/` | Public NASA OSDR serum chemistry CSV used in the separate Biology view. |
| `backend/` | Local HTTP API, simulation, analysis, storage, mission log, and tests. |
| `models/voice/`, `models/wearable/` | Voice and wearable research inference, synthetic samples, tests, and model evidence. |
| `integration/` | Adapters and rules joining the different analysis outputs. |
| `demo/` | Launch script and minimal runtime dependencies. |
| `runtime/demo.sqlite3` | Local SQLite file created on first run; keeps demo history between sessions. |

The server supplies assets under **`/submission-assets/`**, while the browser UI is served at **`/astral-prototype/`**. Keep both the `ui/` and `submission/` folders in place. The audio manifests are at `submission/astral-prototype/audio/manifest.json` and `submission/astral-prototype/audio/ravdess/manifest.json`.

## Data sources and responsible interpretation

- **Synthetic:** crew profiles, wrist waveforms, generated voice enrollment, habitat scenarios, and most displayed health history. Synthetic sources are designed to demonstrate the interface and pipeline, not reproduce actual astronaut physiology.
- **NASA biology:** `submission/data/OSD-575_CMP_TRANSFORMED.csv` contains **28 measured serum samples from four coded Inspiration4 research participants**, with seven pre-/post-flight collections each. These samples are **not** a continuous live sensor stream and are not used to train or validate the daily stress indicators. Source: [NASA OSDR OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) · [DOI](https://doi.org/10.26030/mc5d-p710). The data file was documented as CC0-1.0; its SHA-256 is `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9`.
- **Research audio:** the accompanying audio manifests record file provenance and transformations. RAVDESS acted recordings have distinct non-commercial/share-alike licensing restrictions; the samples are not medical ground truth.
- **Further evidence:** see [research sources](docs/DATA_SOURCES.md), [submission references](submission/REFERENCES.md), the [voice model card](models/voice/MODEL_CARD.md), the [wearable model card](models/wearable/MODEL_CARD.md), and their source/validation notes.

## Check that it is running

With the server started, visit **http://127.0.0.1:8765/api/health**. A healthy local server returns JSON showing that the demo is ready. For backend verification, from the repository root run:

```bash
.venv/bin/python -m unittest discover -s backend -p 'test_*.py' -v
```

These are **commands to run**, not a claim that tests passed on your machine. Additional research-model checks are available in `models/voice/test_voice.py`, `models/wearable/test_wearable.py`, and `models/wearable/test_space.py`.

## Troubleshooting

- **ModuleNotFoundError for NumPy/SciPy:** rerun `.venv/bin/python -m pip install -r demo/requirements-demo.txt` from the repository root.
- **Port 8765 already in use:** check whether the demo is already running at the URL above. To use a different port, run `.venv/bin/python -m backend.demo_server --port 8766` and open `http://127.0.0.1:8766/astral-prototype/`.
- **HTTP 403 / “Local host required”:** use `127.0.0.1` on the computer running the demo. The bundled server intentionally rejects public-host requests; a Codespaces forwarding link is not equivalent to localhost.
- **Missing audio or manifest / 404:** make sure you downloaded the **whole repository** and start from its root; audio is intentionally stored under `submission/`, not `ui/`.
- **Old saved results appearing:** the database at `runtime/demo.sqlite3` intentionally keeps previous entries. Demo scenario changes do not automatically erase the history.

## Project status

This repository demonstrates a complete **local software flow**: input selection → simulated data and actual research feature processing → rule-based analysis → human review and history. It does **not** offer validated clinical recommendations, synchronized real sensors, autonomous interventions, or astronaut-specific accuracy claims.

Additional deliverables, supporting studies, and presentation material are in `submission/`.
