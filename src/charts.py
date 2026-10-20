from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

NAVY = "#173B57"
TEAL = "#0E7C86"
ORANGE = "#D97706"
RED = "#B42318"
GRAY = "#6B7280"
LIGHT = "#E5E7EB"


def set_chinese_font() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150


def _style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LIGHT)
    ax.spines["bottom"].set_color(LIGHT)
    ax.tick_params(colors=GRAY, labelsize=9)
    ax.grid(axis="y", color=LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def monthly_trend(df: pd.DataFrame, path: Path) -> Path:
    set_chinese_font()
    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.bar(df["月份"], df["进件量"], color=TEAL, alpha=0.85, label="进件量")
    ax1.set_ylabel("进件量", color=GRAY)
    _style(ax1)
    ax2 = ax1.twinx()
    ax2.plot(df["月份"], df["审批通过率"] * 100, color=ORANGE, marker="o", linewidth=2, label="审批通过率")
    ax2.set_ylabel("审批通过率 (%)", color=GRAY)
    ax2.tick_params(colors=GRAY, labelsize=9)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(LIGHT)
    ax1.set_title("月度进件量与审批通过率", loc="left", fontsize=13, color=NAVY, fontweight="bold")
    ax1.tick_params(axis="x", rotation=40)
    return save(fig, path)


def channel_bar(df: pd.DataFrame, path: Path) -> Path:
    set_chinese_font()
    data = df.sort_values("进件量", ascending=True).tail(8)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.barh(data["渠道类型"], data["进件量"], color=TEAL, height=0.6)
    for bar, rate in zip(bars, data["审批通过率"]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2, f"{rate*100:.1f}%", va="center", fontsize=8, color=NAVY)
    _style(ax)
    ax.set_xlabel("进件量", color=GRAY)
    ax.set_title("渠道进件量与审批通过率", loc="left", fontsize=13, color=NAVY, fontweight="bold")
    return save(fig, path)


def contribution_bar(df: pd.DataFrame, path: Path) -> Path:
    set_chinese_font()
    data = df.sort_values("总效应")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    colors = [RED if value < 0 else TEAL for value in data["总效应"]]
    ax.barh(data["渠道类型"], data["总效应"] * 100, color=colors, height=0.6)
    for index, value in enumerate(data["总效应"] * 100):
        ax.text(value + (0.05 if value >= 0 else -0.05), index, f"{value:+.2f}pp", va="center", ha="left" if value >= 0 else "right", fontsize=8, color=NAVY)
    _style(ax)
    ax.axvline(0, color=GRAY, linewidth=0.8)
    ax.margins(x=0.18)
    ax.set_xlabel("对整体通过率的影响（百分点）", color=GRAY)
    ax.set_title("渠道对通过率变化的贡献", loc="left", fontsize=13, color=NAVY, fontweight="bold")
    return save(fig, path)


def risk_scatter(df: pd.DataFrame, path: Path) -> Path:
    set_chinese_font()
    fig, ax = plt.subplots(figsize=(7.5, 4))
    sizes = df["进件量"].clip(lower=1) / df["进件量"].max() * 500 + 30
    ax.scatter(df["审批通过率"] * 100, df["DPD30率"] * 100, s=sizes, color=TEAL, alpha=0.7, edgecolor="white")
    for _, row in df.iterrows():
        ax.annotate(str(row["渠道类型"])[:18], (row["审批通过率"] * 100, row["DPD30率"] * 100), fontsize=7, color=GRAY, xytext=(4, 4), textcoords="offset points")
    _style(ax)
    ax.set_xlabel("审批通过率 (%)", color=GRAY)
    ax.set_ylabel("DPD30率 (%)", color=GRAY)
    ax.set_title("审批通过率与 DPD30：通过率低是否对应低风险？", loc="left", fontsize=12, color=NAVY, fontweight="bold")
    return save(fig, path)
