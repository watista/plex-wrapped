import json
from pathlib import Path

from app.utils.json_io import load_json_dict, strip_json_comments


def test_strip_line_comments():
    raw = '{\n  "a": 1 // comment\n}\n'
    assert json.loads(strip_json_comments(raw)) == {"a": 1}


def test_merge_multiple_objects(tmp_path: Path):
    path = tmp_path / "mapping.json"
    path.write_text(
        '{"1": {"plex_user_id": 1}}\n{"2": {"plex_user_id": 2}}\n',
        encoding="utf-8",
    )
    data = load_json_dict(path)
    assert data["1"]["plex_user_id"] == 1
    assert data["2"]["plex_user_id"] == 2


def test_load_test_user_entries():
    from app.fixtures.test_wrapped import load_test_user_entries

    entries = load_test_user_entries()
    ids = {e.plex_user_id for e in entries}
    assert 1 in ids
    assert 14983182 in ids
    assert 3 in ids
    assert 6 in ids
    assert 9 in ids
