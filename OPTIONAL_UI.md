# Optional UI

This branch implements the selected Method Workbench, Hazards Inspector, Mission Operations, Findings Inspector and Sources Register directions. All five screens use local Inter typography, a shared navy/teal palette and left navigation. On narrow screens the navigation opens from the left.

## Run

Use the repository's existing Python environment and dependencies, then run from the repository root:

```sh
python -m backend.demo_server --port 8766
```

Open http://127.0.0.1:8766/astral-prototype/. Method opens first; Mission Control is also directly available at `#mission-control`. A static-only server supports replay, but generating and saving entries requires the local backend.

## Behavior

- Mission Control combines the selected astronaut, an interactive Three.js human wireframe, NASA research context, entry generation/submission and saved evidence. All five astronauts remain available. Crew/cabin analysis, scenario playback, imports, exports and the engineering lab remain under the crew/cabin overview.
- The body rotates horizontally, supports dragging and left/right arrow keys, and has a pause control. Reduced-motion preferences start it paused. A WebGL failure does not disable data entry.
- Hazards use a selectable inspector with links into the corresponding health module. Findings use actual analysis results, evidence and next-check guidance, with the existing review persistence.
- Sources presents a provenance register while retaining the original complete bibliography. Research samples remain separate from synthetic astronaut readings.
- Missing inputs remain missing. Disconnected replay disables backend actions and explains that the local backend is required. Changing an input invalidates the draft before submission.

## Integration and assets

Server routes, request/response contracts, database behavior, AI model code, model artifacts and research/audio data are unchanged. The baseline server's `/submission-assets/` and `/data/` bridges remain intact. Audio and manifests stay in `submission/astral-prototype/`; the original serum CSV stays in `submission/data/`.

The new rendering assets are local: Three.js 0.180.0, Inter, Phosphor and an extracted MakeHuman hm08 body mesh. Source and license notices are in `ui/astral-prototype/vendor/`. The body mesh is illustrative; it does not represent measurements or an anatomical assessment.

## Validation

Validated with Python 3.12, NumPy 2.5.3 and isolated test dependencies; this was not an exact recreation of every pinned dependency version.

```sh
python -m unittest discover -s backend -p 'test_*.py' -q
python -m pytest models/voice -q
python -m unittest models.wearable.test_wearable models.wearable.test_space -q
```

Results: 104 backend tests passed; 26 voice tests passed and 3 skipped; 33 wearable/space tests passed and 8 skipped because optional fixtures were unavailable. The final HTML structure checks passed again after layout refinements. JavaScript syntax checks passed.

Browser verification covered all five screens, all five astronauts, generation → submission → stored history, missing-input handling, findings inspection/filtering, saved review persistence, research expansion, offline replay, model controls and mobile navigation. See `design-qa.md` for visual QA details.
