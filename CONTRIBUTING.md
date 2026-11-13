# Contributing to ASTRAL-Crew

1. Accept your collaborator invitation to this private repository.
2. Read README.md and the issue assigned to your workstream.
3. On/after the official hackathon start, create a feature branch from main (e.g. `feature/voice-model`).
4. Make small, focused commits; never commit credentials, private health records, or large datasets.
5. Push your branch and open a pull request into main.
6. In the PR, explain what changed, how you tested it, and which issue it addresses.
7. Request a review from another teammate; merge only when compatible with the shared data contract.

**Before the event:** Keep work to permitted planning, coordination, research, access verification, and documentation. Do not implement project code early.

**Data:** Document license, URL, version, transformations, and whether samples are recorded or synthetic. Do not upload restricted or copyrighted recordings without permission.

**Integration:** Use shared keys and units defined in docs/DATA_CONTRACT.md. Never silently change an output schema.

**Safety:** Label simulated actions and clinical uncertainty; avoid diagnostic claims or autonomous safety-critical overrides.
