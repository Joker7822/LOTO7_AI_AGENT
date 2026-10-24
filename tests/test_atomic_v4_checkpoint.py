"""State persistence must never expose half-written v4 JSON checkpoints."""
import json

import pytest

import loto7_v4_runner as v4


def test_atomic_write_json_create_and_replace(tmp_path):
    target = tmp_path / "new" / "state.json"
    v4.write_json(target, {"version": 1, "note": "研究"})
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "version": 1, "note": "研究",
    }
    v4.write_json(target, {"version": 2, "nested": {"ok": True}})
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "version": 2, "nested": {"ok": True},
    }
    assert list(target.parent.glob(".state.json.*.tmp")) == []


def test_atomic_write_json_failure_keeps_original_and_cleans_temp(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    target.write_text('{"trusted":true}', encoding="utf-8")
    original = target.read_bytes()

    def fail_replace(source, destination):
        assert str(destination) == str(target)
        assert json.loads(open(source, encoding="utf-8").read()) == {"trusted": False}
        raise OSError("simulated crash before atomic replace")

    monkeypatch.setattr(v4.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated crash"):
        v4.write_json(target, {"trusted": False})
    assert target.read_bytes() == original
    assert list(tmp_path.glob(".state.json.*.tmp")) == []
