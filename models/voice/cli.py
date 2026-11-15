"""Command-line entry point (kept separate from inference.py so `python -m` runs cleanly).

    python -m models.voice.cli enroll      AST-01 calm1.wav calm2.wav calm3.wav calm4.wav calm5.wav
    python -m models.voice.cli analyze     AST-01 clip.wav --timestamp 2026-11-14T09:15:00Z
    python -m models.voice.cli analyze-dir AST-01 folder/ --out data/processed/voice_outputs.jsonl
"""
from .inference import _cli

if __name__ == "__main__":
    _cli()
