import random

from dataclasses import dataclass, field
from typing import List, Tuple

def fen_to_board(fen: str) -> "Board":
    """Load a board position from a FEN string."""
    parts = fen.split()
    rows = parts[0].split("/")
    side = parts[1]

    board = []
    for row in rows:
        current_row = []
        for char in row:
            if char.isdigit():
                for _ in range(int(char)):
                    current_row.append("")
            else:
                color = "w" if char.isupper() else "b"
                piece_type = char.lower()
                piece_map = {
                    "p": "p",
                    "n": "N",
                    "b": "B",
                    "r": "R",
                    "q": "Q",
                    "k": "K",
                }
                current_row.append(color + piece_map[piece_type])
        board.append(current_row)

    return Board(board, side)

Piece = str  # e.g. "wp" = white pawn, "bK" = black king, "" = empty
# Move: (from_row, from_col, to_row, to_col, promotion?)
# promotion is one of 'Q','R','B','N' or None
Move = Tuple[int, int, int, int, object]

# --- Zobrist hashing tables (deterministic for reproducibility) ---
_RNG = random.Random(0)
_PIECE_ORDER = [
    "wp", "wN", "wB", "wR", "wQ", "wK",
    "bp", "bN", "bB", "bR", "bQ", "bK",
]
_PIECE_INDEX = {p: idx for idx, p in enumerate(_PIECE_ORDER)}
_ZOBRIST_PIECES = [
    [_RNG.getrandbits(64) for _ in _PIECE_ORDER]
    for _ in range(64)
]
_ZOBRIST_SIDE = _RNG.getrandbits(64)


@dataclass
class MoveUndo:
    captured: Piece
    moved_piece: Piece
    prev_side: str
    prev_hash: int


# ---------- Helper functions ----------

def is_white(piece: Piece) -> bool:
    return piece.startswith("w")


def is_black(piece: Piece) -> bool:
    return piece.startswith("b")


def is_empty(piece: Piece) -> bool:
    return piece == ""


def opposite(color: str) -> str:
    return "b" if color == "w" else "w"


# ---------- Board + move generation ----------

@dataclass
class Board:
    board: List[List[Piece]]  # 8x8 list
    side_to_move: str         # "w" or "b"
    hash_key: int = field(init=False)

    def __post_init__(self) -> None:
        self.hash_key = self._compute_hash()

    @staticmethod
    def starting_position() -> "Board":
        # 8x8 empty board
        b = [["" for _ in range(8)] for _ in range(8)]

        # Pawns
        for c in range(8):
            b[6][c] = "wp"   # white pawns
            b[1][c] = "bp"   # black pawns

        # Rooks
        b[7][0] = b[7][7] = "wR"
        b[0][0] = b[0][7] = "bR"

        # Knights
        b[7][1] = b[7][6] = "wN"
        b[0][1] = b[0][6] = "bN"

        # Bishops
        b[7][2] = b[7][5] = "wB"
        b[0][2] = b[0][5] = "bB"

        # Queens
        b[7][3] = "wQ"
        b[0][3] = "bQ"

        # Kings
        b[7][4] = "wK"
        b[0][4] = "bK"

        return Board(b, "w")

    def print_board(self) -> None:
        print("  +------------------------+")
        for r in range(8):
            rank = 8 - r
            row_str = f"{rank} |"
            for c in range(8):
                piece = self.board[r][c]
                row_str += f" {piece or '..'}"
            row_str += " |"
            print(row_str)
        print("  +------------------------+")
        print("    a  b  c  d  e  f  g  h")

    # ---- bounds check ----
    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

    # ---- clone (for testing moves) ----
    def clone(self) -> "Board":
        new_board = [row[:] for row in self.board]
        return Board(new_board, self.side_to_move)

    # ---- hashing helpers ----
    def _compute_hash(self) -> int:
        h = 0
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if not piece:
                    continue
                h ^= _ZOBRIST_PIECES[r * 8 + c][_PIECE_INDEX[piece]]
        if self.side_to_move == "b":
            h ^= _ZOBRIST_SIDE
        return h

    def _xor_piece(self, r: int, c: int, piece: Piece) -> None:
        if not piece:
            return
        self.hash_key ^= _ZOBRIST_PIECES[r * 8 + c][_PIECE_INDEX[piece]]

    # ---- make a move ----
    def push_move(self, move: Move) -> MoveUndo:
        """Apply move in-place, returning undo data for pop_move."""
        fr, fc, tr, tc = move[:4]
        promotion = move[4] if len(move) >= 5 else None

        moving_piece = self.board[fr][fc]
        captured_piece = self.board[tr][tc]

        undo = MoveUndo(
            captured=captured_piece,
            moved_piece=moving_piece,
            prev_side=self.side_to_move,
            prev_hash=self.hash_key,
        )

        # hash updates: remove moving piece from source, captured from target
        self._xor_piece(fr, fc, moving_piece)
        if captured_piece:
            self._xor_piece(tr, tc, captured_piece)

        self.board[fr][fc] = ""
        if promotion:
            moving_piece = moving_piece[0] + promotion
        self.board[tr][tc] = moving_piece
        self._xor_piece(tr, tc, moving_piece)

        self.side_to_move = opposite(self.side_to_move)
        self.hash_key ^= _ZOBRIST_SIDE
        return undo

    def pop_move(self, move: Move, undo: MoveUndo) -> None:
        fr, fc, tr, tc = move[:4]
        self.board[fr][fc] = undo.moved_piece
        self.board[tr][tc] = undo.captured
        self.side_to_move = undo.prev_side
        self.hash_key = undo.prev_hash

    def make_move(self, move: Move) -> None:
        # compatibility shim
        self.push_move(move)

    # ---------- pseudo-legal moves (piece rules only) ----------

    def generate_pawn_moves(self, r: int, c: int, moves: List[Move]) -> None:
        piece = self.board[r][c]
        color = piece[0]
        direction = -1 if color == "w" else 1
        start_rank = 6 if color == "w" else 1
        enemy = opposite(color)

        # 1 square forward
        fwd_r = r + direction
        if self.in_bounds(fwd_r, c) and is_empty(self.board[fwd_r][c]):
            # promotion on last rank?
            if (color == "w" and fwd_r == 0) or (color == "b" and fwd_r == 7):
                for promo in ("Q", "R", "B", "N"):
                    moves.append((r, c, fwd_r, c, promo))
            else:
                moves.append((r, c, fwd_r, c, None))

            # 2 squares from starting rank
            if r == start_rank:
                fwd2_r = r + 2 * direction
                if self.in_bounds(fwd2_r, c) and is_empty(self.board[fwd2_r][c]):
                    moves.append((r, c, fwd2_r, c, None))

        # captures
        for dc in (-1, 1):
            cap_r, cap_c = r + direction, c + dc
            if self.in_bounds(cap_r, cap_c):
                target = self.board[cap_r][cap_c]
                if target and target[0] == enemy:
                    # promotion on capture to last rank
                    if (color == "w" and cap_r == 0) or (color == "b" and cap_r == 7):
                        for promo in ("Q", "R", "B", "N"):
                            moves.append((r, c, cap_r, cap_c, promo))
                    else:
                        moves.append((r, c, cap_r, cap_c, None))

    def generate_knight_moves(self, r: int, c: int, moves: List[Move]) -> None:
        piece = self.board[r][c]
        color = piece[0]
        enemy = opposite(color)

        knight_jumps = [
            (2, 1), (1, 2), (-1, 2), (-2, 1),
            (-2, -1), (-1, -2), (1, -2), (2, -1),
        ]
        for dr, dc in knight_jumps:
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc):
                continue
            target = self.board[nr][nc]
            if is_empty(target) or target[0] == enemy:
                moves.append((r, c, nr, nc, None))

    def generate_sliding_moves(self, r: int, c: int,
                               directions: List[Tuple[int, int]],
                               moves: List[Move]) -> None:
        piece = self.board[r][c]
        color = piece[0]
        enemy = opposite(color)

        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if is_empty(target):
                    moves.append((r, c, nr, nc, None))
                else:
                    if target[0] == enemy:
                        moves.append((r, c, nr, nc, None))
                    break
                nr += dr
                nc += dc

    def generate_bishop_moves(self, r: int, c: int, moves: List[Move]) -> None:
        dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        self.generate_sliding_moves(r, c, dirs, moves)

    def generate_rook_moves(self, r: int, c: int, moves: List[Move]) -> None:
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        self.generate_sliding_moves(r, c, dirs, moves)

    def generate_queen_moves(self, r: int, c: int, moves: List[Move]) -> None:
        dirs = [
            (-1, -1), (-1, 1), (1, -1), (1, 1),
            (-1, 0), (1, 0), (0, -1), (0, 1),
        ]
        self.generate_sliding_moves(r, c, dirs, moves)

    def generate_king_moves(self, r: int, c: int, moves: List[Move]) -> None:
        piece = self.board[r][c]
        color = piece[0]
        enemy = opposite(color)

        king_steps = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),          (0, 1),
            (1, -1), (1, 0),  (1, 1),
        ]
        for dr, dc in king_steps:
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc):
                continue
            target = self.board[nr][nc]
            if is_empty(target) or target[0] == enemy:
                moves.append((r, c, nr, nc, None))

    def generate_all_moves(self) -> List[Move]:
        """All pseudo-legal moves for side_to_move (ignores self-check)."""
        moves: List[Move] = []
        color = self.side_to_move

        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if not piece:
                    continue
                if color == "w" and not is_white(piece):
                    continue
                if color == "b" and not is_black(piece):
                    continue

                ptype = piece[1]  # 'p','N','B','R','Q','K'
                if ptype == "p":
                    self.generate_pawn_moves(r, c, moves)
                elif ptype == "N":
                    self.generate_knight_moves(r, c, moves)
                elif ptype == "B":
                    self.generate_bishop_moves(r, c, moves)
                elif ptype == "R":
                    self.generate_rook_moves(r, c, moves)
                elif ptype == "Q":
                    self.generate_queen_moves(r, c, moves)
                elif ptype == "K":
                    self.generate_king_moves(r, c, moves)

        return moves

    # ---------- check / attacks / legal moves ----------

    def find_king(self, color: str) -> Tuple[int, int]:
        target = color + "K"
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == target:
                    return r, c
        raise ValueError(f"King for {color} not found")

    def is_square_attacked(self, r: int, c: int, by_color: str) -> bool:
        enemy = by_color

        # Pawn attacks
        if enemy == "w":
            for dc in (-1, 1):
                rr, cc = r + 1, c + dc
                if self.in_bounds(rr, cc) and self.board[rr][cc] == "wp":
                    return True
        else:
            for dc in (-1, 1):
                rr, cc = r - 1, c + dc
                if self.in_bounds(rr, cc) and self.board[rr][cc] == "bp":
                    return True

        # Knights
        knight_jumps = [
            (2, 1), (1, 2), (-1, 2), (-2, 1),
            (-2, -1), (-1, -2), (1, -2), (2, -1),
        ]
        knight_piece = enemy + "N"
        for dr, dc in knight_jumps:
            rr, cc = r + dr, c + dc
            if self.in_bounds(rr, cc) and self.board[rr][cc] == knight_piece:
                return True

        # Bishops / queens (diagonals)
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            rr, cc = r + dr, c + dc
            while self.in_bounds(rr, cc):
                piece = self.board[rr][cc]
                if piece:
                    if piece[0] == enemy and piece[1] in ("B", "Q"):
                        return True
                    break
                rr += dr
                cc += dc

        # Rooks / queens (straight)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            rr, cc = r + dr, c + dc
            while self.in_bounds(rr, cc):
                piece = self.board[rr][cc]
                if piece:
                    if piece[0] == enemy and piece[1] in ("R", "Q"):
                        return True
                    break
                rr += dr
                cc += dc

        # King
        king_piece = enemy + "K"
        king_steps = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),          (0, 1),
            (1, -1), (1, 0),  (1, 1),
        ]
        for dr, dc in king_steps:
            rr, cc = r + dr, c + dc
            if self.in_bounds(rr, cc) and self.board[rr][cc] == king_piece:
                return True

        return False

    def is_in_check(self, color: str) -> bool:
        kr, kc = self.find_king(color)
        return self.is_square_attacked(kr, kc, opposite(color))

    def generate_legal_moves(self) -> List[Move]:
        """Only moves that do NOT leave own king in check."""
        legal: List[Move] = []
        color_moving = self.side_to_move
        for move in self.generate_all_moves():
            undo = self.push_move(move)
            king_in_check = self.is_in_check(color_moving)
            self.pop_move(move, undo)
            if not king_in_check:
                legal.append(move)
        return legal

Board.from_fen = staticmethod(fen_to_board)


# ---------- quick test ----------

if __name__ == "__main__":
    board = Board.starting_position()
    board.print_board()

    pseudo = board.generate_all_moves()
    legal = board.generate_legal_moves()

    print(f"\nSide to move: {board.side_to_move}")
    print(f"Pseudo-legal moves: {len(pseudo)}")
    print(f"Legal moves:        {len(legal)}")
