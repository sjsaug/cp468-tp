from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt

from testing import MateTestCase, TEST_CASES, run_case


def collect_results(cases: List[MateTestCase]) -> List[dict]:
	rows = []
	for idx, case in enumerate(cases, start=1):
		result = run_case(case)
		rows.append(
			{
				"index": idx,
				"label": case.label,
				"moves": case.moves,
				"attacker": case.attacker,
				"nodes": result["nodes"],
				"seconds": result["elapsed"],
				"nodes_per_sec": result["nodes"] / result["elapsed"] if result["elapsed"] > 0 else float("nan"),
				"success": result["success"],
			}
		)
	return rows


def nice_tick_step(max_value: float, target_ticks: int = 10) -> float:
	if max_value <= 0:
		return 1.0
	raw_step = max_value / target_ticks
	order = 10 ** math.floor(math.log10(raw_step))
	for multiplier in (1, 2, 5, 10):
		step = multiplier * order
		if raw_step <= step:
			return step
	return 10 * order


def plot_bar(rows: List[dict], metric: str, title: str, ylabel: str, output_path: Path, show_labels: bool = False) -> None:
	labels = [row["label"] for row in rows]
	values = [row[metric] for row in rows]
	indices = list(range(len(labels)))
	max_value = max(values) if values else 0
	step = nice_tick_step(max_value, target_ticks=12)
	y_limit = math.ceil(max_value / step) * step if step > 0 else max_value
	if y_limit <= 0:
		y_limit = 1

	fig, ax = plt.subplots(figsize=(12, 6))
	ax.bar(indices, values, color="#5b8def")
	ax.set_title(title)
	ax.set_ylabel(ylabel)
	ax.set_xticks(indices)
	if show_labels:
		ax.set_xticklabels(labels, rotation=60, ha="right")
	else:
		ax.set_xticklabels([])
	ax.set_ylim(0, y_limit if y_limit > 0 else max_value + 1)
	y_ticks = [tick for tick in frange(0, y_limit, step)] if step else []
	if y_ticks:
		ax.set_yticks(y_ticks)
	ax.margins(x=0.01)
	ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.7)

	fig.tight_layout()
	fig.savefig(output_path, bbox_inches="tight")
	plt.close(fig)


def frange(start: float, stop: float, step: float) -> List[float]:
	values = []
	current = start
	while current <= stop + 1e-9:
		values.append(round(current, 6))
		current += step
	return values


def plot_scatter(rows: List[dict], output_path: Path) -> None:
	colors = ["#f4a259" if row["moves"] == 2 else "#3da35d" for row in rows]
	fig, ax = plt.subplots(figsize=(8, 6))
	ax.scatter([row["nodes"] for row in rows], [row["seconds"] for row in rows], c=colors, s=80, edgecolors="black")

	for row in rows:
		ax.annotate(
			str(row["index"]),
			(row["nodes"], row["seconds"]),
			textcoords="offset points",
			xytext=(5, 5),
			fontsize=8,
		)

	ax.set_title("Nodes vs. solve time")
	ax.set_xlabel("Nodes searched")
	ax.set_ylabel("Solve time (s)")
	ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

	legend_labels = ["Mate in 2", "Mate in 3"]
	legend_handles = [plt.Line2D([0], [0], marker="o", color="w", label=label, markerfacecolor=color, markersize=8, markeredgecolor="black") for label, color in zip(legend_labels, ["#f4a259", "#3da35d"])]
	ax.legend(handles=legend_handles, title="Goal depth")

	fig.tight_layout()
	fig.savefig(output_path)
	plt.close(fig)


def main() -> None:
	parser = argparse.ArgumentParser(description="Run chess mate tests and create summary charts.")
	parser.add_argument("--output", type=Path, default=Path("reports"), help="Directory to store the generated charts.")
	args = parser.parse_args()

	rows = collect_results(TEST_CASES)
	output_dir = args.output
	output_dir.mkdir(parents=True, exist_ok=True)

	plot_bar(rows, "nodes", "Nodes searched per puzzle", "Nodes", output_dir / "nodes_per_puzzle.png")
	plot_bar(rows, "seconds", "Solve time per puzzle", "Seconds", output_dir / "time_per_puzzle.png")
	plot_bar(rows, "nodes_per_sec", "Nodes per second", "Nodes/sec", output_dir / "nodes_per_second.png")
	plot_scatter(rows, output_dir / "nodes_vs_time.png")

	print(f"Charts saved to {output_dir.resolve()}")


if __name__ == "__main__":
	main()
