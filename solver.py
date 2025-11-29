from typing import List, Tuple
from engine import Board, Move

# Checkmate logic
def is_checkmate(board: Board) -> bool:
    color = board.side_to_move
    legal = board.generate_legal_moves()
    return board.is_in_check(color) and len(legal) == 0

def is_stalemate(board: Board) -> bool:
    color = board.side_to_move
    legal = board.generate_legal_moves()
    return (not board.is_in_check(color)) and len(legal) == 0

# Mate solver with move sequence output
def find_mate_line(board: Board, attacker: str, attacker_moves: int) -> Tuple[bool, List[Move]]:
    max_depth = attacker_moves * 2 - 1  # mate in 2 -> depth 3, mate in 3 -> depth 5
    return search(board, attacker, max_depth)

def search(board: Board, attacker: str, depth: int) -> Tuple[bool, List[Move]]:
    legal_moves = board.generate_legal_moves()

    # No moves at all
    if not legal_moves:
        if board.is_in_check(board.side_to_move):
            # Checkmate
            return (board.side_to_move != attacker, [])
        else:
            return (False, [])  # stalemate

    if depth == 0:
        # Depth gone, no forced mate proven
        return (False, [])

    # Attacker's turn -> find at least ONE move that forces mate
    if board.side_to_move == attacker:
        for move in legal_moves:
            nb = board.clone()
            nb.make_move(move)
            can_mate, line = search(nb, attacker, depth - 1)
            if can_mate:
                return (True, [move] + line)
        return (False, [])

    # Defender's turn -> if they find ANY move escaping mate, attacker fails
    else:
        all_force = True
        best_line = []
        for move in legal_moves:
            nb = board.clone()
            nb.make_move(move)
            can_mate, line = search(nb, attacker, depth - 1)
            if not can_mate:
                return (False, [])
            # record a possible continuation
            best_line = [move] + line
        return (True, best_line)


# Translate moves to something readable (like "e2e4")
def move_to_str(move: Move) -> str:
    fr, fc, tr, tc = move
    return f"{chr(fc+97)}{8-fr}{chr(tc+97)}{8-tr}"


if __name__ == "__main__":
    # Mate in 2 puzzle example:
    # White: King f2, Queen b3
    # Black: King h1
    fen = "8/8/8/8/8/1Q6/5K2/7k w - - 0 1"

    board = Board.from_fen(fen)
    print("Loaded puzzle position:")
    board.print_board()

    can_mate, line = find_mate_line(board, "w", 2)

    print("\nCan White mate in 2?", can_mate)
    print("Move sequence:", [move_to_str(m) for m in line])

