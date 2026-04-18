from tools.fetch_edaic_public import map_available_session_archives, parse_index_links, parse_session_ids


def test_parse_index_links_for_edaic_directory_listing():
    html = """
    <a href="metadata_mapped.csv">metadata</a>
    <a href="labels/">labels</a>
    <a href="300_P.tar.gz">300</a>
    """
    links = parse_index_links(html)
    assert "metadata_mapped.csv" in links
    assert "labels/" in links
    assert "300_P.tar.gz" in links


def test_parse_session_ids_handles_tar_suffixes():
    assert parse_session_ids("300, 301_P, 302_P.tar.gz") == {"300", "301", "302"}


def test_map_available_session_archives():
    links = {"300_P.tar.gz", "301_P.tar.gz", "labels/"}
    assert map_available_session_archives(links) == {
        "300": "300_P.tar.gz",
        "301": "301_P.tar.gz",
    }
