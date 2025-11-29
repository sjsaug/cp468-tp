from typing import List, Tuple
from engine import Board, Move


# MVV-LVA scoring (Most Valuable Victim - Least Valuable Attacker)
PIECE_VALUE = {
    "p": 1,
    "N": 3, "B": 3,
    "R": 5,
    "Q": 9,
    "K": 100   # very high just to discourage bad eval
}

def move_score(board: Board, move: Move) -> int:
    """Return a score for move ordering.
       Higher = searched earlier."""
    fr, fc, tr, tc = move[:4]
    piece = board.board[fr][fc]
    target = board.board[tr][tc]

    score = 0

    # 1. Checking moves (highest priority)
    temp = board.clone()
    temp.make_move(move)
    if temp.is_in_check(board.side_to_move):  
        score += 500

    # 2. Captures (MVV-LVA)
    if target != "":
        victim_val = PIECE_VALUE[target[1]]
        attacker_val = PIECE_VALUE[piece[1]]
        score += 100 + (victim_val * 10 - attacker_val)

    # 3. Quiet moves: small bonus based on centrality
    score += (3 - abs(tr - 3.5)) + (3 - abs(tc - 3.5))

    return score


def order_moves(board: Board, moves: List[Move]) -> List[Move]:
    """Sort moves by heuristic score."""
    return sorted(moves, key=lambda mv: move_score(board, mv), reverse=True)


# Checkmate / Stalemate 

def is_checkmate(board: Board) -> bool:
    color = board.side_to_move
    legal = board.generate_legal_moves()
    return board.is_in_check(color) and len(legal) == 0


def is_stalemate(board: Board) -> bool:
    color = board.side_to_move
    legal = board.generate_legal_moves()
    return (not board.is_in_check(color)) and len(legal) == 0


# MATE SOLVER WITH ORDERING 

def find_mate_line(board: Board, attacker: str, attacker_moves: int) -> Tuple[bool, List[Move]]:
    # Depth depends on whose turn it is
    if board.side_to_move == attacker:
        max_depth = attacker_moves * 2 - 1
    else:
        max_depth = attacker_moves * 2

    return search(board, attacker, max_depth)


def search(board: Board, attacker: str, depth: int) -> Tuple[bool, List[Move]]:
    legal_moves = board.generate_legal_moves()
    legal_moves = order_moves(board, legal_moves)   # 🔥 USE ORDERING HERE

    # No moves at all
    if not legal_moves:
        if board.is_in_check(board.side_to_move):
            return (board.side_to_move != attacker, [])
        else:
            return (False, [])

    if depth == 0:
        return (False, [])

    # Attacker’s turn: needs at least one forced mate move
    if board.side_to_move == attacker:
        for move in legal_moves:
            nb = board.clone()
            nb.make_move(move)
            can_mate, line = search(nb, attacker, depth - 1)
            if can_mate:
                return (True, [move] + line)
        return (False, [])

    # Defender’s turn: if ANY reply avoids mate, attacker fails
    else:
        best_line = []
        for move in legal_moves:
            nb = board.clone()
            nb.make_move(move)
            can_mate, line = search(nb, attacker, depth - 1)
            if not can_mate:
                return (False, [])
            best_line = [move] + line  # store one valid line
        return (True, best_line)


#  Move Formatting 

def move_to_str(move: Move) -> str:
    fr, fc, tr, tc = move[:4]
    s = f"{chr(fc+97)}{8-fr}{chr(tc+97)}{8-tr}"
    if len(move) >= 5 and move[4]:
        s += move[4]
    return s



if __name__ == "__main__":
    # Simple mate in 2 test
    fen = "8/8/8/8/8/1Q6/5K2/7k w - - 0 1"

    board = Board.from_fen(fen)
    print("Loaded puzzle position:")
    board.print_board()

    can_mate, line = find_mate_line(board, "w", 2)

    print("\nCan White mate in 2?", can_mate)
    print("Move sequence:", [move_to_str(m) for m in line])
