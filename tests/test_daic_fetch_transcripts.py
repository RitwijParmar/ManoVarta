from io import BytesIO
from pathlib import Path

from tools import fetch_daic_woz_transcripts as module


class _FakeRemoteZip:
    def __init__(self, url: str):
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def namelist(self):
        return ["300_TRANSCRIPT.csv", "ignore.txt"]

    def open(self, name: str):
        assert name == "300_TRANSCRIPT.csv"
        return BytesIO(b"start_time\tstop_time\tspeaker\tvalue\n")


def test_fetch_transcript_from_zip_writes_expected_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "RemoteZip", _FakeRemoteZip)

    transcript_path = module.fetch_transcript_from_zip(
        "https://example.com/300_P.zip",
        "300",
        tmp_path,
        overwrite=True,
    )

    assert transcript_path == tmp_path / "300_P" / "300_TRANSCRIPT.csv"
    assert transcript_path.exists()
    assert transcript_path.read_text(encoding="utf-8").startswith("start_time")
