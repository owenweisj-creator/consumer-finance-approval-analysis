import pandas as pd
import pytest

from src.metrics import approval_rate, avg_ticket, decompose_rate_change, utilization_rate


def test_basic_metrics():
    assert approval_rate(30, 100) == 0.3
    assert utilization_rate(20, 30) == pytest.approx(0.6667, rel=1e-3)
    assert avg_ticket(1200, 20) == 60


def test_decompose_rate_change():
    current = pd.DataFrame(
        {"渠道类型": ["A", "B"], "进件量": [80, 20], "审批通过量": [8, 18]}
    )
    previous = pd.DataFrame(
        {"渠道类型": ["A", "B"], "进件量": [50, 50], "审批通过量": [10, 45]}
    )
    result = decompose_rate_change(current, previous)
    assert set(["结构效应", "比率效应", "总效应"]).issubset(result.columns)
    overall_change = (
        current["审批通过量"].sum() / current["进件量"].sum()
        - previous["审批通过量"].sum() / previous["进件量"].sum()
    )
    assert result["总效应"].sum() == pytest.approx(overall_change, abs=1e-9)

