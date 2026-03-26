from ctxai.helpers.dirty_json import DirtyJson, parse, stringify, try_parse


class TestDirtyJson:
    def test_try_parse_valid_json(self):
        result = try_parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_try_parse_invalid_json(self):
        result = try_parse("{key: value}")
        assert result == {"key": "value"}

    def test_parse_invalid_json(self):
        result = parse("{key: value}")
        assert result == {"key": "value"}

    def test_try_parse_empty_string(self):
        result = try_parse("")
        assert result is None

    def test_parse_valid_json(self):
        result = parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_stringify_basic(self):
        result = stringify({"key": "value"})
        assert result == '{"key": "value"}'

    def test_stringify_with_indent(self):
        result = stringify({"key": "value"}, indent=2)
        assert "\n" in result
        assert '\n  "key"' in result

    def test_dirty_json_init(self):
        dj = DirtyJson()
        assert dj.json_string == ""
        assert dj.index == 0
        assert dj.current_char is None

    def test_dirty_json_parse_empty_string(self):
        result = DirtyJson.parse_string("")
        assert result is None

    def test_dirty_json_parse_simple_object(self):
        result = DirtyJson.parse_string('{"a": 1}')
        assert result == {"a": 1}

    def test_dirty_json_parse_simple_array(self):
        result = DirtyJson.parse_string("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_dirty_json_parse_string(self):
        result = DirtyJson.parse_string('"hello"')
        assert result == "hello"

    def test_dirty_json_parse_number(self):
        result = DirtyJson.parse_string("42")
        assert result == 42

    def test_dirty_json_parse_boolean_true(self):
        result = DirtyJson.parse_string("true")
        assert result is True

    def test_dirty_json_parse_boolean_false(self):
        result = DirtyJson.parse_string("false")
        assert result is False

    def test_dirty_json_parse_null(self):
        result = DirtyJson.parse_string("null")
        assert result is None
