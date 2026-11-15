"""Tests for the voice workstream. Run from the repo root:

    python -m pytest models/voice -q

All audio here is SYNTHETIC (models/voice/synth.py). Integration tests that
need Eleni's data layer (data/) are skipped automatically if it is missing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from models.voice import CONTRACT_KEYS, VoiceStressEstimator, make_record, write_jsonl
from models.voice import features as F
from models.voice import scoring, synth
from models.voice.baseline import BaselineStore
from models.voice.inference import normalise_timestamp

TS = "2026-11-14T15:30:00Z"
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ROOT = Path(__file__).resolve().parents[2]
HAS_DATA = (ROOT / "data" / "scripts" / "validate_data.py").exists()


@pytest.fixture(scope="module")
def enrolled() -> VoiceStressEstimator:
    est = VoiceStressEstimator(baseline_path=None, model_path=None)
    for i, (crew, prof) in enumerate(synth.SPEAKERS.items()):
        est.enroll(crew, [synth.utterance(prof, 3.0, seed=100 * i + s) for s in range(10)], data_type="synthetic")
    return est


# ---------------------------------------------------------------- signal level
def test_bandpass_removes_fan_hum_and_keeps_speech_band():
    t = np.arange(F.SR) / F.SR
    hum, tone = np.sin(2 * np.pi * 60 * t), np.sin(2 * np.pi * 1000 * t)
    att_hum = 10 * np.log10(np.mean(F.bandpass(hum) ** 2) / np.mean(hum ** 2))
    att_tone = 10 * np.log10(np.mean(F.bandpass(tone) ** 2) / np.mean(tone ** 2))
    assert att_hum < -30          # fan hum suppressed by > 30 dB
    assert att_tone > -1          # 1 kHz speech energy kept


@pytest.mark.parametrize("f0", [110.0, 200.0])
def test_pitch_tracker_accuracy(f0):
    prof = synth.VoiceProfile(f0_hz=f0, f0_var=0.0, jitter=0.0)
    v = F.extract(synth.utterance(prof, 3.0, seed=1)).values
    assert abs(v["f0_mean_hz"] - f0) / f0 < 0.03


def test_teager_energy_of_sinusoid_is_constant():
    w = 2 * np.pi * 500 / F.SR
    x = 0.5 * np.sin(w * np.arange(1000))
    psi = F.teager(x)[1:-1]
    assert np.allclose(psi, 0.25 * np.sin(w) ** 2, atol=1e-9)


def test_mfcc_and_feature_vector_shapes():
    frames = F.frame_signal(synth.utterance(synth.SPEAKERS["AST-01"], 1.0))
    assert F.mfcc(frames).shape == (len(frames), F.N_MFCC)
    feats = F.extract(synth.utterance(synth.SPEAKERS["AST-01"], 2.0))
    assert feats.vector().shape == (len(F.FEATURE_NAMES),)
    assert np.all(np.isfinite(feats.vector()))


def test_resampling_from_44k1():
    x = synth.utterance(synth.SPEAKERS["AST-03"], 2.0)
    up = F.resample(x, F.SR, 44100)
    v1, v2 = F.extract(x).values, F.extract(up, sr=44100).values
    assert abs(v1["f0_mean_hz"] - v2["f0_mean_hz"]) < 3


# ---------------------------------------------------------------- contract
def test_record_has_exactly_the_contract_keys(enrolled):
    res = enrolled.analyze(synth.utterance(synth.SPEAKERS["AST-01"], 3.0, seed=999), "AST-01", TS,
                           data_type="synthetic")
    r = res.record
    assert res.ok and tuple(r) == CONTRACT_KEYS
    assert r["source"] == "voice" and r["data_type"] == "synthetic" and r["crew_id"] == "AST-01"
    assert ISO_Z.match(r["timestamp"]) and r["timestamp"] == TS
    assert 0 <= r["stress_score"] <= 1 and 0 <= r["confidence"] <= 1
    json.dumps(r)  # serialisable


def test_make_record_clips_values():
    r = make_record("AST-02", TS, 1.7, -0.2, "real")
    assert r["stress_score"] == 1.0 and r["confidence"] == 0.0


@pytest.mark.skipif(not HAS_DATA, reason="Eleni's data layer not in repo")
def test_records_pass_elenis_validator(enrolled, tmp_path):
    from data.scripts.validate_data import CONTRACT_KEYS as ELENI_KEYS
    from data.scripts.validate_data import check_outputs
    assert set(CONTRACT_KEYS) == ELENI_KEYS
    recs = [enrolled.analyze(synth.utterance(p, 3.0, seed=50 + i), c, TS, data_type="synthetic").record
            for i, (c, p) in enumerate(synth.SPEAKERS.items())]
    path = tmp_path / "voice.jsonl"
    assert write_jsonl(recs, path) == 4
    assert check_outputs(path) == []


# ------------------------------------------------- missing / invalid inputs
def test_silence_gives_no_record(enrolled):
    res = enrolled.analyze(np.zeros(F.SR * 3, dtype=np.float32), "AST-01", TS)
    assert res.record is None and res.details["status"] == "no_speech"


def test_noise_only_gives_no_record(enrolled):
    noise = 0.05 * synth.cabin_noise(F.SR * 3, seed=3)
    res = enrolled.analyze(noise, "AST-02", TS)
    assert res.record is None and res.details["status"] == "no_speech"


@pytest.mark.parametrize("kwargs,reason", [
    ({"crew_id": "AST-09"}, "crew_id"),
    ({"timestamp": "yesterday"}, "timestamp"),
    ({"data_type": "made_up"}, "data_type"),
])
def test_invalid_inputs_do_not_raise(enrolled, kwargs, reason):
    args = {"audio": synth.utterance(synth.SPEAKERS["AST-01"], 2.0), "crew_id": "AST-01", "timestamp": TS, **kwargs}
    res = enrolled.analyze(**args)
    assert res.record is None and res.details["status"] == "invalid_input" and reason in res.details["reason"]


def test_nan_and_empty_audio(enrolled):
    bad = synth.utterance(synth.SPEAKERS["AST-01"], 2.0)
    bad[100] = np.nan
    assert enrolled.analyze(bad, "AST-01", TS).details["status"] == "invalid_input"
    assert enrolled.analyze(np.array([]), "AST-01", TS).details["status"] == "invalid_input"


def test_unreadable_file(enrolled, tmp_path):
    p = tmp_path / "broken.wav"
    p.write_bytes(b"not a wav")
    res = enrolled.analyze_file(p, "AST-01", TS)
    assert res.record is None and res.details["status"] == "invalid_input"


def test_timestamp_normalisation():
    assert normalise_timestamp("2026-11-14T17:30:00+02:00") == TS
    assert ISO_Z.match(normalise_timestamp(None))


# ---------------------------------------------------- baseline behaviour
def test_auto_enrollment_then_scoring():
    est = VoiceStressEstimator(baseline_path=None, model_path=None, min_enroll=3)
    prof = synth.SPEAKERS["AST-04"]
    statuses = [est.analyze(synth.utterance(prof, 3.0, seed=s), "AST-04", TS).details["status"] for s in range(5)]
    assert statuses[:3] == ["enrolling_baseline"] * 3
    assert statuses[3] == "ok"


def test_calm_low_aroused_high(enrolled):
    for i, (crew, prof) in enumerate(synth.SPEAKERS.items()):
        calm = [enrolled.analyze(synth.utterance(prof, 3.0, seed=5000 + 10 * i + s), crew, TS).record["stress_score"]
                for s in range(4)]
        hot = [enrolled.analyze(synth.utterance(synth.aroused(prof), 3.0, seed=6000 + 10 * i + s), crew, TS)
               .record["stress_score"] for s in range(4)]
        assert np.mean(calm) < 0.4, crew
        assert np.mean(hot) > 0.6, crew
        assert min(hot) > max(calm), crew


def test_score_is_personal_not_population(enrolled):
    """A naturally high voice (AST-02, ~205 Hz) speaking calmly is NOT stressed."""
    r = enrolled.analyze(synth.utterance(synth.SPEAKERS["AST-02"], 3.0, seed=4242), "AST-02", TS)
    assert r.record["stress_score"] < 0.5


def test_explanation_and_details(enrolled):
    r = enrolled.analyze(synth.utterance(synth.aroused(synth.SPEAKERS["AST-03"]), 3.0, seed=7), "AST-03", TS)
    d = r.details
    assert d["status"] == "ok" and "not a diagnosis" in d["explanation"]
    assert len(d["top_contributors"]) == 3 and "features" in d and d["baseline_n"] == 10


def test_low_snr_lowers_confidence(enrolled):
    prof = synth.SPEAKERS["AST-01"]
    clean = synth.utterance(prof, 3.0, seed=77)
    noisy = synth.mix_at_snr(clean, synth.cabin_noise(len(clean), seed=1), 3)
    c_clean = enrolled.analyze(clean, "AST-01", TS).record["confidence"]
    rn = enrolled.analyze(noisy, "AST-01", TS)
    assert rn.ok, rn.details
    assert rn.record["confidence"] < c_clean
    assert {"low_snr", "moderate_noise"} & set(rn.details["flags"])


def test_baseline_save_load_roundtrip(tmp_path):
    path = tmp_path / "baselines.json"
    prof = synth.SPEAKERS["AST-01"]
    est = VoiceStressEstimator(path, model_path=None)
    est.enroll("AST-01", [synth.utterance(prof, 3.0, seed=s) for s in range(6)])
    clip = synth.utterance(synth.aroused(prof, 0.5), 3.0, seed=99)
    s1 = est.analyze(clip, "AST-01", TS).record["stress_score"]
    s2 = VoiceStressEstimator(path, model_path=None).analyze(clip, "AST-01", TS).record["stress_score"]
    assert s1 == s2


def test_baseline_with_other_feature_set_is_rejected(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"feature_names": ["something_else"], "baselines": {}}))
    with pytest.raises(ValueError):
        BaselineStore(path)


def test_wav_file_roundtrip(enrolled, tmp_path):
    p = tmp_path / "clip.wav"
    wavfile.write(p, 44100, (F.resample(synth.utterance(synth.SPEAKERS["AST-01"], 3.0, seed=3), F.SR, 44100)
                             * 32767).astype(np.int16))
    res = enrolled.analyze_file(p, "AST-01", TS)
    assert res.ok and res.details["file"] == str(p)


# --------------------------------------------- optional model + scripts
def _fake_ravdess(root: Path, actors=(1, 2, 3, 4)) -> None:
    """Files named like RAVDESS (03-01-EMO-INT-STMT-REP-ACTOR.wav) with SYNTHETIC audio."""
    seed = 0
    for a in actors:
        base = synth.VoiceProfile(f0_hz=110 + 25 * a, tilt=0.92)
        for emo, amt in (("01", 0.0), ("02", 0.0), ("05", 1.0), ("06", 0.9)):
            for rep in ("01", "02"):
                for stmt in ("01", "02"):
                    seed += 1
                    x = synth.utterance(synth.aroused(base, amt), 1.6, seed=seed)
                    d = root / f"Actor_{a:02d}"
                    d.mkdir(parents=True, exist_ok=True)
                    wavfile.write(d / f"03-01-{emo}-01-{stmt}-{rep}-{a:02d}.wav", F.SR, (x * 32767).astype(np.int16))


@pytest.mark.skipif(not HAS_DATA, reason="Eleni's data layer not in repo")
def test_training_pipeline_on_fake_ravdess(tmp_path):
    from data.scripts.ravdess_prepare import build_manifest

    from models.voice import train
    _fake_ravdess(tmp_path / "RAVDESS")
    man = build_manifest(tmp_path / "RAVDESS", k=4)
    zdf = train.baseline_z(train.featurise(man))
    assert "neutral" not in set(zdf.emotion)          # enrollment clips are never scored
    res = train.evaluate(zdf)
    for kind in ("logreg", "rule"):
        assert 0 <= res["summary"][kind]["balanced_accuracy_mean"] <= 1
    model = train.fit_final(zdf)
    mpath = tmp_path / "model.json"
    mpath.write_text(json.dumps(model))
    est = VoiceStressEstimator(None, model_path=mpath)
    est.enroll("AST-01", [synth.utterance(synth.SPEAKERS["AST-01"], 3.0, seed=s) for s in range(6)])
    r = est.analyze(synth.utterance(synth.SPEAKERS["AST-01"], 3.0, seed=11), "AST-01", TS)
    assert r.ok and r.details["model_used"] is True


@pytest.mark.skipif(not (ROOT / "data" / "scenarios" / "09_demo_storyline").exists(), reason="no scenarios")
def test_scenario_demo_produces_valid_records(tmp_path, monkeypatch):
    from data.scripts.validate_data import check_outputs

    from models.voice import demo
    monkeypatch.chdir(ROOT)
    s = demo.run_scenario("09_demo_storyline", snr_db=15, out_root=tmp_path, limit=12)
    assert s["records"] > 0 and s["data_type"] == "synthetic"
    assert check_outputs(tmp_path / "09_demo_storyline.jsonl") == []


def test_artemis_demo_makes_no_stress_claims(tmp_path):
    from models.voice import artemis_demo
    clips = []
    for i in range(4):
        p = tmp_path / "in" / f"clip_{i}.wav"
        p.parent.mkdir(exist_ok=True)
        x = synth.mix_at_snr(synth.utterance(synth.SPEAKERS["AST-01"], 3.0, seed=i), synth.cabin_noise(F.SR * 3), 15)
        wavfile.write(p, F.SR, (x * 32767).astype(np.int16))
        clips.append(p)
    df = artemis_demo.run(clips, n_reference=2, out=tmp_path / "out", data_type="synthetic", source="test")
    assert (df["stress_label"] == "none").all()
    assert "stress_score" not in df.columns
    assert (tmp_path / "out" / "artemis_voice_features.csv").exists()
