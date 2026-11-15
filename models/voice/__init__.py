"""ASTRAL-Crew voice stress workstream (owner: voice lead).

Public interface (see INTEGRATION_HANDOFF.md):
    VoiceStressEstimator   enroll a calm baseline, then analyze utterances
    VoiceResult            .record (DATA_CONTRACT record or None) + .details
    make_record            build a contract-shaped voice record
    CONTRACT_KEYS          the six required keys
"""
from .inference import CONTRACT_KEYS, VoiceResult, VoiceStressEstimator, make_record, write_jsonl

__all__ = ["VoiceStressEstimator", "VoiceResult", "make_record", "write_jsonl", "CONTRACT_KEYS"]
