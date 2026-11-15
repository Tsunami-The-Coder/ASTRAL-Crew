# Optional UI design QA

final result: passed

Date: 2026-11-15. Scope: the five selected visual directions, adapted to the requested persistent left navigation and existing working application. Passed means the reviewed flows and responsive layouts have no outstanding actionable P0/P1/P2 findings; it does not mean pixel identity with generated concept images.

## Reference and capture comparison

The source images and corresponding implementation captures were viewed side by side. Evidence is delivered separately in the local `outputs/optional-ui-preview/` folder; comparison boards are in `work/visual-qa/` in the task workspace.

| Reference | Implementation capture | Reviewed |
| --- | --- | --- |
| method-workbench.png | method.jpg | Four-stage rail, feature workbench, description hierarchy, typography, spacing and colors |
| hazards-inspector.png | mission-hazards.jpg | Five-item hazard list, detail inspector, supporting content and destination action |
| mission-operations.png | mission-control.jpg | Left wireframe body, Biology above entry controls, astronaut selection and evidence modules |
| findings-inspector.png | flagged-findings.jpg | Selectable findings, detail/evidence hierarchy, filter, human review form and log |
| sources-register.png | sources.jpg | Provenance register, source hierarchy, typography and complete bibliography access |

Desktop captures use 1440 × 1024 CSS pixels; Mission Control uses 1440 × 1280 to show the evidence boundary. Mobile was checked at 390 × 844. Device pixel ratio was approximately 1.84, with screenshots normalized by the browser capture. Source aspect ratios were preserved when assembling comparison boards.

## Findings and corrections

| Priority | Finding | Resolution |
| --- | --- | --- |
| P0 | A transformed textarea initially swallowed following markup | Restored the explicit closing tag; checked unique control IDs, bootstrap JSON and all script assets |
| P1 | An early demonstration model had unsuitable helmet proportions | Replaced it with the licensed MakeHuman body mesh; inspected the rendered body and original quad wireframe |
| P2 | Legacy form/grid margins left excessive gaps in Mission Control | Compacted the entry form, empty feedback slots, research footer and evidence/module boundary; compared the revised capture again |
| P2 | Closed mobile navigation could remain keyboard reachable | Added inert/aria-hidden handling, focus containment while open and Escape dismissal |
| P2 | Mobile astronaut selection appeared below the model | Moved selection and previous/next controls above the model; verified DOM positions and screenshot |
| P2 | Offline actions and empty audio could imply live processing | Disabled unavailable backend actions and removed offline audio sources; retained labeled historical replay values |

## Functional and accessibility evidence

- Five main navigation destinations and all five astronauts were exercised. Identity, entry history and evidence updated together.
- Generated readings were submitted through the real local backend and matched stored values. Processing stages were observed in the accessibility tree; the saved pipeline screenshot shows completion, not a frozen in-progress animation.
- Silence/missing wearable samples retained explicit unavailable results and missing EDA, without substituted normal values.
- Findings selection/filtering and links to affected crew worked. A review was saved and verified after reload against its analysis.
- Research expansion/collapse and the original CSV/asset routes worked. The complete original source bibliography remains accessible.
- The 3D viewer loaded locally; pause/resume, horizontal drag and keyboard rotation were checked. Reduced-motion behavior was inspected in code; the operating system preference was not changed for this test.
- Mobile width equaled document width (390 pixels), with no page-level horizontal overflow. The drawer opens on the left and closes after destination selection. The source table provides a labeled keyboard-scrollable region.
- Visible headings, buttons, fields and selects use the same Inter font family. Native selects retain browser keyboard behavior. No JavaScript console errors were recorded in the final online session.

## Intentional adaptations and limits

Left navigation replaces the top navigation appearing in some concepts, as explicitly requested. Live model outputs, timestamps and missing states replace illustrative concept values. The real interactive mesh differs from the raster pose. Source details use an expandable complete bibliography, and health evidence continues below the main astronaut workspace. These are accepted functional adaptations rather than unresolved defects.

The visual reference contains smaller decorative details and generated copy that were not copied literally. No remaining P0/P1/P2 issues were identified in the reviewed scope. Future refinements can adjust microcopy, exact model pose or minor spacing after user feedback. Automated tests and their dependency/fixture limits are recorded in `OPTIONAL_UI.md`.
