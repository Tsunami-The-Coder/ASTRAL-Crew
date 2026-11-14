# Research and data — Eleni

Track scientific references, NASA dataset accession IDs, licenses, provenance and limitations. See docs/DATA_SOURCES.md.
## Data & Science (Eleni)

All the data and science for ASTRAL-Crew live in `data/` and `research/`.

**Where our numbers come from (real NASA sources):**
- Radiation limits: 600 mSv career, 250 mSv per solar storm (NASA-STD-3001)
- CO₂ limit: 3 mmHg, 1-hour average (NASA-STD-3001)
- Deep-space radiation: 1.84 mSv/day, measured by NASA's Curiosity rover on its way to Mars
- Bone loss: 1–1.5% per month in space (NASA Human Research Program)
- Real solar storms: NASA DONKI space-weather database
- Real astronaut voices: NASA Artemis II audio library (demo only)

**Stress data:** WESAD, a public dataset of 15 people wearing smartwatches during calm and stressful tasks.

**Test scenarios:** 9 simulated 4-astronaut emergencies (CO₂ failure, solar storm, cabin leak, a broken sensor, stress spreading between crew members, exercise) with the correct answer for each. These are SIMULATED and labelled as such.

**Run it:**
pip install numpy pandas scipy scikit-learn pytest
python -m pytest tests/ -q
python -m data.scripts.generate_scenarios

**Honest limits:** WESAD is lab data, not astronauts. Stress scores are indicators, not medical diagnoses.
