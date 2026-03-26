from ctxai.helpers.self_update import (
    _filter_selector_supported_tags,
    _is_selector_supported_tag,
    _parse_major_version,
    _parse_selector_version,
    _sort_selector_supported_tags,
    is_valid_selector_tag,
)


def test_parse_selector_version():
    assert _parse_selector_version("v1.0") == (1, 0)
    assert _parse_selector_version("v2.15") == (2, 15)
    assert _parse_selector_version("v0.9") == (0, 9)
    # Invalid formats
    assert _parse_selector_version("1.0") is None
    assert _parse_selector_version("v1") is None
    assert _parse_selector_version("v1.0.0") is None
    assert _parse_selector_version("v1.0-alpha") is None
    assert _parse_selector_version("  v1.0  ") == (1, 0)


def test_is_selector_supported_tag():
    assert _is_selector_supported_tag("v1.0") is True
    assert _is_selector_supported_tag("v1.1") is True
    assert _is_selector_supported_tag("v2.0") is True
    assert _is_selector_supported_tag("v0.9") is False
    assert _is_selector_supported_tag("invalid") is False


def test_filter_selector_supported_tags():
    tags = ["v0.9", "v1.0", "v1.1", "v2.0", "invalid", "v1.0.0"]
    assert _filter_selector_supported_tags(tags) == ["v1.0", "v1.1", "v2.0"]


def test_sort_selector_supported_tags():
    tags = ["v1.0", "v2.0", "v1.1", "v1.10", "v1.2", "v0.9"]
    # Should sort in descending order based on parsed version tuple:
    # (2,0), (1,10), (1,2), (1,1), (1,0), (0,9)
    assert _sort_selector_supported_tags(tags) == ["v2.0", "v1.10", "v1.2", "v1.1", "v1.0", "v0.9"]


def test_is_valid_selector_tag():
    assert is_valid_selector_tag("v1.0") is True
    assert is_valid_selector_tag("v2.15") is True
    assert is_valid_selector_tag("2.0") is False
    assert is_valid_selector_tag("v1") is False


def test_parse_major_version():
    assert _parse_major_version("v1.0") == 1
    assert _parse_major_version("v2") == 2
    assert _parse_major_version("v3.1.4") == 3
    assert _parse_major_version("v4-alpha") == 4
    assert _parse_major_version("1.0") is None
    assert _parse_major_version("invalid") is None
    assert _parse_major_version("  v5.0  ") == 5
