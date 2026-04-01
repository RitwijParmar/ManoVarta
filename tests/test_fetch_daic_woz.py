from pathlib import Path

from tools.fetch_daic_woz import map_available_session_zips, parse_index_links, parse_session_ids, read_split_ids, select_ids_by_split


def _write_csv(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_index_links_and_session_mapping():
    html = """
    <a href="300_P.zip">300_P.zip</a>
    <a href="301_P.zip">301_P.zip</a>
    <a href="dev_split_Depression_AVEC2017.csv">dev</a>
    """
    links = parse_index_links(html)
    assert "300_P.zip" in links
    assert "dev_split_Depression_AVEC2017.csv" in links

    mapping = map_available_session_zips(links)
    assert mapping == {"300": "300_P.zip", "301": "301_P.zip"}


def test_parse_session_ids_handles_suffix_and_whitespace():
    assert parse_session_ids("300, 301_P, , 002") == {"300", "301", "2"}


def test_read_split_ids_and_select_ids_by_split(tmp_path: Path):
    train_csv = _write_csv(
        tmp_path / "train_split_Depression_AVEC2017.csv",
        "\n".join(
            [
                "Participant_ID,PHQ8_Binary",
                "300,1",
                "301,0",
            ]
        ),
    )
    dev_csv = _write_csv(
        tmp_path / "dev_split_Depression_AVEC2017.csv",
        "\n".join(
            [
                "session_id,score",
                "401,3",
            ]
        ),
    )
    test_csv = _write_csv(
        tmp_path / "test_split_Depression_AVEC2017.csv",
        "\n".join(
            [
                "participantid,label",
                "501,0",
            ]
        ),
    )

    assert read_split_ids(train_csv) == {"300", "301"}
    split_paths = {"train": train_csv, "dev": dev_csv, "test": test_csv}
    assert select_ids_by_split("dev", split_paths) == {"401"}
    assert select_ids_by_split("all", split_paths) == {"300", "301", "401", "501"}
