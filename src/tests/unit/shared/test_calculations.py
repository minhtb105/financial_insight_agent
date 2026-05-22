"""Unit tests for financial calculations."""


import pytest
from shared.utils.calculations import calculate_volatility, calculate_std_dev


def test_volatility_less_than_two_points():
    assert calculate_volatility([{"close": 100}]) == 0.0
    assert calculate_volatility([]) == 0.0


def test_volatility_returns_positive():
    data = [{"close": 100}, {"close": 101}, {"close": 99}, {"close": 102}, {"close": 100}]
    vol = calculate_volatility(data)
    assert vol > 0
    assert vol == pytest.approx(38.83, rel=1e-1)


def test_std_dev_empty():
    assert calculate_std_dev([]) == 0.0


def test_std_dev_single():
    assert calculate_std_dev([5.0]) == 0.0


def test_std_dev_known():
    result = calculate_std_dev([1.0, 2.0, 3.0])
    assert result == 1.0


# -- edge cases -------------------------------------------------------------


def test_volatility_identical_values():
    data = [{"close": 100}, {"close": 100}, {"close": 100}, {"close": 100}]
    vol = calculate_volatility(data)
    assert vol == 0.0


def test_volatility_nan_in_data():
    data = [{"close": 100}, {"close": float("nan")}, {"close": 102}]
    vol = calculate_volatility(data)
    assert vol == 0.0


def test_volatility_null_close():
    data = [{"close": 100}, {"close": None}, {"close": 102}]
    vol = calculate_volatility(data)
    assert vol == 0.0


def test_volatility_missing_close_key():
    data = [{"close": 100}, {"open": 101}, {"close": 102}]
    vol = calculate_volatility(data)
    assert vol == 0.0


def test_volatility_negative_close():
    data = [{"close": -100}, {"close": -90}, {"close": -110}]
    vol = calculate_volatility(data)
    assert vol > 0


def test_std_dev_nan_in_list():
    result = calculate_std_dev([1.0, float("nan"), 3.0])
    assert result == pytest.approx(1.414, rel=1e-2)


def test_std_dev_all_same():
    assert calculate_std_dev([5.0, 5.0, 5.0]) == 0.0


def test_std_dev_negative_values():
    result = calculate_std_dev([-10.0, -5.0, 0.0])
    assert result == pytest.approx(5.0, rel=1e-1)


def test_volatility_zero_division_skipped():
    data = [{"close": 0}, {"close": 100}, {"close": 102}]
    vol = calculate_volatility(data)
    assert vol == 0.0


def test_volatility_single_return_returns_zero():
    data = [{"close": 100}, {"close": 101}, {"close": float("nan")}]
    vol = calculate_volatility(data)
    assert vol == 0.0


def test_std_dev_all_nan():
    result = calculate_std_dev([float("nan"), float("nan")])
    assert result == 0.0
