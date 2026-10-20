from __future__ import annotations

import pandas as pd


def approval_rate(approved: float, applications: float) -> float:
    return approved / applications if applications else float("nan")


def utilization_rate(used: float, approved: float) -> float:
    return used / approved if approved else float("nan")


def avg_ticket(approved_amount: float, used: float) -> float:
    return approved_amount / used if used else float("nan")


def decompose_rate_change(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    dimension: str = "渠道类型",
) -> pd.DataFrame:
    """渠道通过率变化分解：结构效应 + 比率效应。"""
    current_total = current["进件量"].sum()
    previous_total = previous["进件量"].sum()
    current_rate = current["审批通过量"].sum() / current_total if current_total else float("nan")
    previous_rate = previous["审批通过量"].sum() / previous_total if previous_total else float("nan")

    merged = current.merge(
        previous[[dimension, "进件量", "审批通过量"]],
        on=dimension,
        how="outer",
        suffixes=("_当期", "_基期"),
    ).fillna(0)
    merged["当期占比"] = merged["进件量_当期"] / current_total if current_total else 0
    merged["基期占比"] = merged["进件量_基期"] / previous_total if previous_total else 0
    merged["当期通过率"] = merged["审批通过量_当期"] / merged["进件量_当期"].replace(0, pd.NA)
    merged["基期通过率"] = merged["审批通过量_基期"] / merged["进件量_基期"].replace(0, pd.NA)
    merged["结构效应"] = (merged["当期占比"] - merged["基期占比"]) * (
        merged["基期通过率"] - previous_rate
    )
    merged["比率效应"] = merged["当期占比"] * (merged["当期通过率"] - merged["基期通过率"])
    merged["总效应"] = merged["结构效应"] + merged["比率效应"]
    merged.attrs["当期整体通过率"] = current_rate
    merged.attrs["基期整体通过率"] = previous_rate
    return merged.sort_values("总效应").reset_index(drop=True)


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def pp(value: float, digits: int = 2) -> str:
    return f"{value * 100:+.{digits}f}pp"
