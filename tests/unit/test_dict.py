"""DictMinimizer tests — null stripping, key shortening, formatting."""

import json

import ptk


class TestDictMinimizer:
    def test_basic_compact_json(self):
        d = {"name": "Alice", "age": 30, "email": None}
        parsed = json.loads(ptk.minimize(d))
        assert "email" not in parsed
        assert parsed["name"] == "Alice"

    def test_nested_null_strip(self):
        d = {"user": {"name": "Bob", "bio": "", "meta": {"x": None}}}
        parsed = json.loads(ptk.minimize(d))
        assert "bio" not in parsed["user"]
        assert "meta" not in parsed["user"]

    def test_deeply_nested_nulls(self):
        d = {"a": {"b": {"c": {"d": None, "e": {"f": None}}, "g": "keep"}}}
        parsed = json.loads(ptk.minimize(d))
        assert parsed["a"]["b"]["g"] == "keep"
        assert "d" not in parsed["a"]["b"].get("c", {})

    def test_preserves_zero_and_false(self):
        d = {"count": 0, "active": False, "name": "test"}
        parsed = json.loads(ptk.minimize(d))
        assert parsed["count"] == 0
        assert parsed["active"] is False

    # ── aggressive mode ──
    def test_aggressive_flattens_single_children(self):
        d = {"config": {"database": {"host": "localhost"}}}
        parsed = json.loads(ptk.minimize(d, aggressive=True))
        assert "cfg.db.host" in parsed

    def test_aggressive_shortens_keys(self):
        d = {"description": "A thing", "timestamp": "2024-01-01"}
        parsed = json.loads(ptk.minimize(d, aggressive=True))
        assert "desc" in parsed
        assert "ts" in parsed

    def test_aggressive_flattens_and_shortens_combined(self):
        d = {"configuration": {"environment": "production"}}
        parsed = json.loads(ptk.minimize(d, aggressive=True))
        assert "cfg.env" in parsed

    def test_aggressive_does_not_flatten_multi_child(self):
        d = {"settings": {"host": "localhost", "port": 8080}}
        parsed = json.loads(ptk.minimize(d, aggressive=True))
        assert "settings" in parsed
        assert parsed["settings"]["host"] == "localhost"

    # ── output formats ──
    def test_kv_format(self):
        result = ptk.minimize({"name": "Alice", "age": 30}, format="kv")
        assert "name:Alice" in result
        assert "age:30" in result

    def test_tabular_format(self):
        d = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        result = ptk.minimize(d, format="tabular")
        assert "users[2]{name,age}:" in result
        assert "Alice,30" in result
        assert "Bob,25" in result

    # ── edge cases ──
    def test_empty_dict(self):
        assert ptk.minimize({}) == "{}"

    def test_single_key(self):
        assert json.loads(ptk.minimize({"a": 1})) == {"a": 1}

    def test_unicode_keys_and_values(self):
        d = {"名前": "太郎", "город": "Москва"}
        assert json.loads(ptk.minimize(d))["名前"] == "太郎"

    def test_large_nested_dict(self):
        d: dict = {"level": 0}
        current = d
        for i in range(1, 20):
            current["child"] = {"level": i}
            current = current["child"]
        assert json.loads(ptk.minimize(d))["level"] == 0

    def test_numeric_values_preserved(self):
        d = {"int": 42, "float": 3.14, "neg": -1, "big": 10**18}
        parsed = json.loads(ptk.minimize(d))
        assert parsed["int"] == 42
        assert parsed["float"] == 3.14

    # ── integration ──
    def test_real_world_api_response(self):
        response = {
            "data": {
                "users": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "email": "a@b.com",
                        "bio": None,
                        "avatar_url": "",
                        "metadata": {},
                        "settings": {"theme": "dark", "notifications": None},
                    },
                ]
            },
            "meta": {"page": 1, "total": 1, "next_cursor": None},
            "errors": None,
        }
        parsed = json.loads(ptk.minimize(response))
        assert "errors" not in parsed
        assert "bio" not in parsed["data"]["users"][0]
        assert parsed["data"]["users"][0]["name"] == "Alice"

    def test_real_world_aggressive(self):
        payload = {
            "description": "User management endpoint",
            "timestamp": "2024-01-01T00:00:00Z",
            "configuration": {"environment": "production"},
        }
        parsed = json.loads(ptk.minimize(payload, aggressive=True))
        assert "desc" in parsed
        assert "ts" in parsed
        assert "cfg.env" in parsed

    def test_minimize_is_idempotent(self):
        d = {"a": 1, "b": 2}
        first = ptk.minimize(d)
        assert first == ptk.minimize(json.loads(first))
