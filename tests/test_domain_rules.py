from smart_sniper.domain.target_parser import parse_blacklist, parse_targets
from smart_sniper.domain.time_matching import matches_date


def test_parse_targets_preserves_original_line_and_fields() -> None:
    targets = parse_targets(["Math;22.01;Novak", "Physics;;", "  "])
    assert len(targets) == 2
    assert targets[0].subject == "Math"
    assert targets[0].date == "22.01"
    assert targets[0].teacher_filter == "Novak"
    assert targets[0].original_line == "Math;22.01;Novak"
    assert targets[1].subject == "Physics"


def test_parse_blacklist_trims_tokens() -> None:
    assert parse_blacklist("24.01; 8:00 ; Novak ;") == ["24.01", "8:00", "Novak"]


def test_matches_date_with_href() -> None:
    assert matches_date("24.04.", "2026-04-24", "24.04.")
    assert matches_date("24", "2026-04-24", "24.04.")
    assert not matches_date("25", "2026-04-24", "24.04.")


def test_matches_date_without_href_uses_cell_text() -> None:
    assert matches_date("24.04.", "", "Volno 24.04.")
    assert matches_date("8", "", "08:30")

