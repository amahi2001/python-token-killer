"""Input mutation tests — ptk must NEVER modify its inputs."""

import copy

import ptk


class TestInputMutation:
    def test_dict_not_mutated(self):
        d = {"a": 1, "b": None, "c": {"d": None, "e": 2}, "f": [None, 1]}
        original = copy.deepcopy(d)
        ptk.minimize(d)
        assert d == original

    def test_dict_not_mutated_aggressive(self):
        d = {"configuration": {"environment": "production"}, "description": "test"}
        original = copy.deepcopy(d)
        ptk.minimize(d, aggressive=True)
        assert d == original

    def test_list_not_mutated(self):
        lst = [{"id": 1, "x": None}, {"id": 2}, None, "hello"]
        original = copy.deepcopy(lst)
        ptk.minimize(lst)
        assert lst == original

    def test_nested_dict_not_mutated(self):
        d = {"a": {"b": {"c": None, "d": {"e": ""}}, "f": [None, {"g": None}]}}
        original = copy.deepcopy(d)
        ptk.minimize(d, aggressive=True)
        assert d == original

    def test_stats_does_not_mutate(self):
        d = {"a": 1, "b": None}
        original = copy.deepcopy(d)
        ptk.stats(d)
        assert d == original
