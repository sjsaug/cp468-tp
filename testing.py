from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

from engine import Board
import solver


@dataclass(frozen=True)
class MateTestCase:
	fen: str
	attacker: str  # "w" or "b"
	moves: int
	label: str


TEST_CASES: List[MateTestCase] = [
	MateTestCase(
		fen="8/8/8/8/8/1Q6/5K2/7k w - - 0 1",
		attacker="w",
		moves=2,
		label="Baseline: textbook mate in 2",
	),
	MateTestCase(
		fen="N2kr3/pp1b1ppp/2n5/2b5/5P2/PP1P1N2/3P1qPP/R1BQ3K b - - 0 17",
		attacker="b",
		moves=3,
		label="https://www.chess.com/forum/view/more-puzzles/mate-in-3-for-black",
	),
	MateTestCase(
		fen="r7/6p1/6pk/4Q1N1/6pK/5N2/8/1b6 w - - 0 1",
		attacker="w",
		moves=3,
		label="https://www.chess.com/forum/view/more-puzzles/mate-in-3-moves-medium",
	),
	MateTestCase(
		fen="8/7b/7b/p7/Pp2k3/1P6/KP2p2p/3N4 b - - 0 1",
		attacker="b",
		moves=3,
		label="https://www.chess.com/forum/view/more-puzzles/black-mates-in-3",
	),
	MateTestCase(
		fen="kbK5/pp6/1P6/8/8/8/8/R7 w - - 0 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	MateTestCase(
		fen="8/8/2Q5/3B4/1K6/2P5/Nk6/2R5 w - - 0 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	MateTestCase(
		fen="1B2q1B1/2n1kPR1/R1b2n1Q/2p1r3/8/3Q2B1/4p3/4K3 w - - 0 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	MateTestCase(
		fen="3N4/KPP1p3/3k4/4R3/3P4/6R1/7B/8 w - - 1 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	MateTestCase(
		fen="8/p4p2/Q7/3P4/1p1kB3/1K4N1/5R2/8 w - - 0 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	MateTestCase(
		fen="2b3N1/8/1r2pN1b/1p2kp2/1P1R4/8/4K3/6Q1 w - - 0 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	MateTestCase(
		fen="5B2/8/K7/8/kpp5/7R/8/1B6 w - - 0 1",
		attacker="w",
		moves=2,
		label="https://www.chess.com/blog/ThePawnSlayer/checkmate-in-two-puzzles-test-very-hard",
	),
	
]


def run_case(case: MateTestCase) -> dict:
	board = Board.from_fen(case.fen)
	original_search = solver.search
	nodes = 0

	def counting_search(board_obj, attacker, depth, memo):
		nonlocal nodes
		nodes += 1
		return original_search(board_obj, attacker, depth, memo)

	solver.search = counting_search
	start = time.perf_counter()
	error = None
	try:
		success, line = solver.find_mate_line(board, case.attacker, case.moves)
	except Exception as exc:  # pragma: no cover - diagnostic output desired
		success = False
		line = []
		error = exc
	finally:
		solver.search = original_search
	elapsed = time.perf_counter() - start

	line_san = [solver.move_to_str(mv) for mv in line]
	return {
		"case": case,
		"success": success,
		"line": line_san,
		"nodes": nodes,
		"elapsed": elapsed,
		"error": error,
	}


def print_result(result: dict) -> None:
	case = result["case"]
	attacker = "White" if case.attacker == "w" else "Black"
	print(f"\n{case.label}")
	print(f"FEN       : {case.fen}")
	print(f"Task      : {attacker} to force mate in {case.moves}")
	if result["error"]:
		print(f"Status    : ERROR -> {result['error']}")
		return
	print(f"Status    : {'SUCCESS' if result['success'] else 'FAILED'}")
	if result["line"]:
		print(f"Line      : {' '.join(result['line'])}")
	print(f"Nodes     : {result['nodes']:,}")
	print(f"Time (s)  : {result['elapsed']:.4f}")
	if result["elapsed"] > 0:
		print(f"Nodes/sec : {result['nodes'] / result['elapsed']:.0f}")


def main() -> None:
	print("Testing")
	overall = []
	for case in TEST_CASES:
		result = run_case(case)
		overall.append(result)
		print_result(result)

	passed = sum(1 for r in overall if r["success"] and not r["error"])
	print("\nSummary")
	print(f"  {passed}/{len(overall)} ({passed / len(overall) * 100}%) cases reported a forced mate found.")


if __name__ == "__main__":
	main()