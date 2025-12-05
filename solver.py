from typing import Dict, List, Tuple

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
    special = move[5] if len(move) >= 6 else None
    target = board.board[tr][tc]
    if special == "ep":
        direction = -1 if piece[0] == "w" else 1
        cap_r = tr - direction
        target = board.board[cap_r][tc]

    score = 0

    # 1. Checking moves (highest priority)
    undo = board.push_move(move)
    gives_check = board.is_in_check(board.side_to_move)
    board.pop_move(move, undo)
    if gives_check:
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

    memo: Dict[Tuple[int, int], Tuple[bool, Tuple[Move, ...]]] = {}
    success, line = search(board, attacker, max_depth, memo)
    return success, line


def search(board: Board, attacker: str, depth: int,
           memo: Dict[Tuple[int, int], Tuple[bool, Tuple[Move, ...]]]) -> Tuple[bool, List[Move]]:
    key = (board.hash_key, depth)
    if key in memo:
        cached_result, cached_line = memo[key]
        return cached_result, list(cached_line)

    legal_moves = board.generate_legal_moves()
    legal_moves = order_moves(board, legal_moves)   # 🔥 USE ORDERING HERE

    # No moves at all
    if not legal_moves:
        if board.is_in_check(board.side_to_move):
            result = board.side_to_move != attacker
            memo[key] = (result, tuple())
            return (result, [])
        else:
            memo[key] = (False, tuple())
            return (False, [])

    if depth == 0:
        memo[key] = (False, tuple())
        return (False, [])

    # Attacker’s turn: needs at least one forced mate move
    if board.side_to_move == attacker:
        for move in legal_moves:
            undo = board.push_move(move)
            can_mate, line = search(board, attacker, depth - 1, memo)
            board.pop_move(move, undo)
            if can_mate:
                result_line = [move] + line
                memo[key] = (True, tuple(result_line))
                return (True, result_line)
        memo[key] = (False, tuple())
        return (False, [])

    # Defender’s turn: if ANY reply avoids mate, attacker fails
    else:
        best_line = []
        for move in legal_moves:
            undo = board.push_move(move)
            can_mate, line = search(board, attacker, depth - 1, memo)
            board.pop_move(move, undo)
            if not can_mate:
                memo[key] = (False, tuple())
                return (False, [])
            best_line = [move] + line  # store one valid line
        memo[key] = (True, tuple(best_line))
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
