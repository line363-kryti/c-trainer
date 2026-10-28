from app.runner.checker import Diff, first_diff, normalize


def test_normalize_ignores_trailing_spaces_and_newlines():
    assert normalize("1 2 \r\n3\n\n\n") == ["1 2", "3"]
    assert normalize("") == []


def test_equal_outputs():
    assert first_diff("5\n", "5") is None
    assert first_diff("a\r\nb", "a  \nb\n\n") is None


def test_different_line():
    assert first_diff("1\n2\n3", "1\n5\n3") == Diff(line=2, expected="2", got="5")


def test_missing_and_extra_lines():
    assert first_diff("1\n2", "1") == Diff(line=2, expected="2", got=None)
    assert first_diff("1", "1\n2") == Diff(line=2, expected=None, got="2")


def test_leading_spaces_matter():
    assert first_diff("5", " 5") == Diff(line=1, expected="5", got=" 5")
