"""Type chaos — every Python type that could be passed in."""

import json
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import NamedTuple

import pytest

import ptk


class TestTypeChaos:
    def test_none(self):
        assert isinstance(ptk.minimize(None), str)

    def test_bool_true(self):
        assert isinstance(ptk.minimize(True), str)

    def test_bool_false(self):
        assert isinstance(ptk.minimize(False), str)

    def test_int_zero(self):
        assert isinstance(ptk.minimize(0), str)

    def test_int_negative(self):
        assert isinstance(ptk.minimize(-42), str)

    def test_int_huge(self):
        assert isinstance(ptk.minimize(10**100), str)

    def test_float(self):
        assert isinstance(ptk.minimize(3.14159), str)

    def test_float_inf(self):
        assert isinstance(ptk.minimize(float("inf")), str)

    def test_float_neg_inf(self):
        assert isinstance(ptk.minimize(float("-inf")), str)

    def test_float_nan(self):
        assert isinstance(ptk.minimize(float("nan")), str)

    def test_complex(self):
        assert isinstance(ptk.minimize(complex(1, 2)), str)

    def test_bytes(self):
        assert isinstance(ptk.minimize(b"hello bytes"), str)

    def test_bytearray(self):
        assert isinstance(ptk.minimize(bytearray(b"hello")), str)

    def test_set(self):
        assert isinstance(ptk.minimize({1, 2, 3}), str)

    def test_frozenset(self):
        assert isinstance(ptk.minimize(frozenset({1, 2, 3})), str)

    def test_range(self):
        assert isinstance(ptk.minimize(range(10)), str)

    def test_tuple(self):
        assert isinstance(ptk.minimize((1, 2, 3)), str)

    def test_empty_tuple(self):
        assert isinstance(ptk.minimize(()), str)

    def test_lambda(self):
        assert isinstance(ptk.minimize(lambda x: x), str)

    def test_class_type(self):
        assert isinstance(ptk.minimize(int), str)

    def test_exception_object(self):
        assert isinstance(ptk.minimize(ValueError("test")), str)

    def test_generator(self):
        assert isinstance(ptk.minimize(i for i in range(5)), str)

    def test_module(self):
        import json as j

        assert isinstance(ptk.minimize(j), str)

    def test_custom_class_with_str(self):
        class MyObj:
            def __str__(self):
                return "MyObj(custom)"

        assert isinstance(ptk.minimize(MyObj()), str)

    def test_custom_class_without_str(self):
        class Bare:
            pass

        assert isinstance(ptk.minimize(Bare()), str)

    def test_custom_class_with_broken_str(self):
        class Broken:
            def __str__(self):
                raise RuntimeError("I'm broken")

        with pytest.raises(RuntimeError, match="I'm broken"):
            ptk.minimize(Broken())

    def test_custom_class_with_repr_only(self):
        class ReprOnly:
            def __repr__(self):
                return "ReprOnly(42)"

        assert isinstance(ptk.minimize(ReprOnly()), str)

    def test_dataclass(self):
        @dataclass
        class Point:
            x: int
            y: int

        assert isinstance(ptk.minimize(Point(1, 2)), str)

    def test_namedtuple(self):
        class Coord(NamedTuple):
            x: int
            y: int

        assert isinstance(ptk.minimize(Coord(1, 2)), str)

    def test_ordered_dict(self):
        d = OrderedDict([("z", 1), ("a", 2)])
        assert json.loads(ptk.minimize(d))["z"] == 1

    def test_defaultdict(self):
        assert isinstance(ptk.minimize(defaultdict(list, {"a": [1, 2]})), str)

    # ── weird dict keys ──
    def test_dict_with_int_keys(self):
        assert isinstance(ptk.minimize({1: "a", 2: "b"}), str)

    def test_dict_with_bool_keys(self):
        assert isinstance(ptk.minimize({True: "yes", False: "no"}), str)

    def test_dict_with_none_key(self):
        assert isinstance(ptk.minimize({None: "value"}), str)

    def test_dict_with_tuple_key(self):
        assert isinstance(ptk.minimize({(1, 2): "value"}), str)

    # ── weird dict values ──
    def test_dict_with_bytes_value(self):
        assert isinstance(ptk.minimize({"data": b"binary"}), str)

    def test_dict_with_set_value(self):
        assert isinstance(ptk.minimize({"tags": {"a", "b"}}), str)

    def test_dict_with_date_value(self):
        from datetime import date, datetime

        assert isinstance(ptk.minimize({"ts": datetime.now(), "d": date.today()}), str)

    def test_dict_with_mixed_value_types(self):
        d = {
            "str": "hello",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"a": 1},
        }
        assert isinstance(ptk.minimize(d), str)

    # ── weird list contents ──
    def test_list_of_none(self):
        assert isinstance(ptk.minimize([None, None, None]), str)

    def test_list_with_nested_lists(self):
        assert isinstance(ptk.minimize([[1, 2], [3, 4]]), str)

    def test_list_with_bytes_items(self):
        assert isinstance(ptk.minimize([b"a", b"b"]), str)

    def test_list_with_sets(self):
        assert isinstance(ptk.minimize([{1, 2}, {3, 4}]), str)
