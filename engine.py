import random

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

def fen_to_board(fen: str) -> "Board":
	# parse fen data into internal board state
    """Load a board position from a FEN string."""
    parts = fen.split()
    if len(parts) < 4:
        raise ValueError("FEN must include side, castling, and en-passant fields")
    rows = parts[0].split("/")
    side = parts[1]
    castling_part = parts[2]
    en_passant_part = parts[3]

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

    castling_rights: Set[str] = set() if castling_part == "-" else set(castling_part)
    en_passant_target = None if en_passant_part == "-" else algebraic_to_coords(en_passant_part)

    return Board(board, side, castling_rights, en_passant_target)


def algebraic_to_coords(square: str) -> Tuple[int, int]:
	# convert algebraic like e4 into matrix coords
    file_char = square[0]
    rank_char = square[1]
    col = ord(file_char) - ord("a")
    rank = int(rank_char)
    row = 8 - rank
    if not (0 <= row < 8 and 0 <= col < 8):
        raise ValueError(f"Invalid square {square}")
    return row, col

Piece = str  # e.g. "wp" = white pawn, "bK" = black king, "" = empty
# Move: (from_row, from_col, to_row, to_col, promotion, special)
# promotion is one of 'Q','R','B','N' or None
# special encodes values like "ep", "castle-k", "castle-q"
Move = Tuple[int, int, int, int, Optional[str], Optional[str]]

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
_CASTLING_FLAGS = ["K", "Q", "k", "q"]
_ZOBRIST_CASTLING = {flag: _RNG.getrandbits(64) for flag in _CASTLING_FLAGS}
_ZOBRIST_EP = [_RNG.getrandbits(64) for _ in range(64)]


@dataclass
class MoveUndo:
	# store info required to undo a move
    captured: Piece
    moved_piece: Piece
    prev_side: str
    prev_hash: int
    prev_castling: Set[str]
    prev_en_passant: Optional[Tuple[int, int]]
    rook_from: Optional[Tuple[int, int]] = None
    rook_to: Optional[Tuple[int, int]] = None
    ep_capture_square: Optional[Tuple[int, int]] = None


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
	# game state with board array and metadata
    board: List[List[Piece]]  # 8x8 list
    side_to_move: str         # "w" or "b"
    castling_rights: Set[str] = field(default_factory=set)
    en_passant_target: Optional[Tuple[int, int]] = None
    hash_key: int = field(init=False)

    def __post_init__(self) -> None:
        self.castling_rights = set(self.castling_rights)
        self.hash_key = self._compute_hash()

    @staticmethod
    def starting_position() -> "Board":
		# build the default chess setup
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

        return Board(b, "w", {"K", "Q", "k", "q"}, None)

    def print_board(self) -> None:
		# show ascii board for debugging
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
		# ensure a square sits on the board
        return 0 <= r < 8 and 0 <= c < 8

    # ---- clone (for testing moves) ----
    def clone(self) -> "Board":
		# create a deep copy for simulations
        new_board = [row[:] for row in self.board]
        return Board(new_board, self.side_to_move, set(self.castling_rights), self.en_passant_target)

    # ---- hashing helpers ----
    def _compute_hash(self) -> int:
		# rebuild zobrist hash for the whole state
        h = 0
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if not piece:
                    continue
                h ^= _ZOBRIST_PIECES[r * 8 + c][_PIECE_INDEX[piece]]
        if self.side_to_move == "b":
            h ^= _ZOBRIST_SIDE
        for flag in sorted(self.castling_rights):
            h ^= _ZOBRIST_CASTLING[flag]
        if self.en_passant_target is not None:
            idx = self.en_passant_target[0] * 8 + self.en_passant_target[1]
            h ^= _ZOBRIST_EP[idx]
        return h

    def _xor_piece(self, r: int, c: int, piece: Piece) -> None:
		# toggle a single piece contribution in hash
        if not piece:
            return
        self.hash_key ^= _ZOBRIST_PIECES[r * 8 + c][_PIECE_INDEX[piece]]

    def _xor_castling(self, flag: str) -> None:
		# toggle a castling right in hash
        self.hash_key ^= _ZOBRIST_CASTLING[flag]

    def _xor_en_passant(self, square: Tuple[int, int]) -> None:
		# toggle an ep square in hash
        idx = square[0] * 8 + square[1]
        self.hash_key ^= _ZOBRIST_EP[idx]

    def _set_en_passant(self, square: Optional[Tuple[int, int]]) -> None:
		# update ep square tracking in hash and state
        if self.en_passant_target is not None:
            self._xor_en_passant(self.en_passant_target)
        self.en_passant_target = square
        if square is not None:
            self._xor_en_passant(square)

    def _remove_castling_right(self, flag: str) -> None:
		# drop a castling right if still available
        if flag in self.castling_rights:
            self._xor_castling(flag)
            self.castling_rights.remove(flag)

    # ---- make a move ----
    def push_move(self, move: Move) -> MoveUndo:
		# apply a move and capture undo data
        """Apply move in-place, returning undo data for pop_move."""
        fr, fc, tr, tc = move[:4]
        promotion = move[4] if len(move) >= 5 else None
        special = move[5] if len(move) >= 6 else None

        moving_piece = self.board[fr][fc]
        original_piece_type = moving_piece[1]
        color = moving_piece[0]

        ep_capture_square: Optional[Tuple[int, int]] = None
        if special == "ep":
            direction = -1 if color == "w" else 1
            cap_r = tr - direction
            cap_c = tc
            ep_capture_square = (cap_r, cap_c)
            captured_piece = self.board[cap_r][cap_c]
        else:
            captured_piece = self.board[tr][tc]

        rook_from: Optional[Tuple[int, int]] = None
        rook_to: Optional[Tuple[int, int]] = None
        if special == "castle-k":
            rook_from = (fr, 7)
            rook_to = (fr, tc - 1)
        elif special == "castle-q":
            rook_from = (fr, 0)
            rook_to = (fr, tc + 1)

        undo = MoveUndo(
            captured=captured_piece,
            moved_piece=moving_piece,
            prev_side=self.side_to_move,
            prev_hash=self.hash_key,
            prev_castling=set(self.castling_rights),
            prev_en_passant=self.en_passant_target,
            rook_from=rook_from,
            rook_to=rook_to,
            ep_capture_square=ep_capture_square,
        )

        # reset en-passant target (updated later if double pawn move)
        self._set_en_passant(None)

        # hash updates: remove moving piece from source, captured from board
        self._xor_piece(fr, fc, moving_piece)
        if special == "ep" and ep_capture_square and captured_piece:
            self._xor_piece(ep_capture_square[0], ep_capture_square[1], captured_piece)
            self.board[ep_capture_square[0]][ep_capture_square[1]] = ""
        elif captured_piece:
            self._xor_piece(tr, tc, captured_piece)

        self.board[fr][fc] = ""
        if promotion:
            moving_piece = moving_piece[0] + promotion
        self.board[tr][tc] = moving_piece
        self._xor_piece(tr, tc, moving_piece)

        if rook_from and rook_to:
            rook_piece = self.board[rook_from[0]][rook_from[1]]
            self._xor_piece(rook_from[0], rook_from[1], rook_piece)
            self.board[rook_from[0]][rook_from[1]] = ""
            self.board[rook_to[0]][rook_to[1]] = rook_piece
            self._xor_piece(rook_to[0], rook_to[1], rook_piece)

        # update castling rights for moving piece
        if original_piece_type == "K":
            if color == "w":
                self._remove_castling_right("K")
                self._remove_castling_right("Q")
            else:
                self._remove_castling_right("k")
                self._remove_castling_right("q")
        elif original_piece_type == "R":
            if color == "w":
                if (fr, fc) == (7, 0):
                    self._remove_castling_right("Q")
                elif (fr, fc) == (7, 7):
                    self._remove_castling_right("K")
            else:
                if (fr, fc) == (0, 0):
                    self._remove_castling_right("q")
                elif (fr, fc) == (0, 7):
                    self._remove_castling_right("k")

        # update castling rights if a rook was captured on its original square
        capture_square = ep_capture_square if ep_capture_square else (tr, tc)
        if captured_piece and captured_piece[1] == "R":
            if captured_piece[0] == "w":
                if capture_square == (7, 0):
                    self._remove_castling_right("Q")
                elif capture_square == (7, 7):
                    self._remove_castling_right("K")
            else:
                if capture_square == (0, 0):
                    self._remove_castling_right("q")
                elif capture_square == (0, 7):
                    self._remove_castling_right("k")

        # update en-passant square if pawn moved two squares
        if original_piece_type == "p" and abs(tr - fr) == 2:
            direction = -1 if color == "w" else 1
            self._set_en_passant((tr - direction, tc))

        self.side_to_move = opposite(self.side_to_move)
        self.hash_key ^= _ZOBRIST_SIDE
        return undo

    def pop_move(self, move: Move, undo: MoveUndo) -> None:
		# revert a move using stored undo info
        fr, fc, tr, tc = move[:4]
        special = move[5] if len(move) >= 6 else None

        self.board[fr][fc] = undo.moved_piece
        if special == "ep" and undo.ep_capture_square:
            self.board[tr][tc] = ""
            cap_r, cap_c = undo.ep_capture_square
            self.board[cap_r][cap_c] = undo.captured
        else:
            self.board[tr][tc] = undo.captured

        if undo.rook_from and undo.rook_to:
            rook_piece = self.board[undo.rook_to[0]][undo.rook_to[1]]
            self.board[undo.rook_to[0]][undo.rook_to[1]] = ""
            self.board[undo.rook_from[0]][undo.rook_from[1]] = rook_piece

        self.side_to_move = undo.prev_side
        self.castling_rights = set(undo.prev_castling)
        self.en_passant_target = undo.prev_en_passant
        self.hash_key = undo.prev_hash

    def make_move(self, move: Move) -> None:
        # compatibility shim
        self.push_move(move)

    # ---------- pseudo-legal moves (piece rules only) ----------

    def generate_pawn_moves(self, r: int, c: int, moves: List[Move]) -> None:
		# add pawn pushes, captures, and en passant
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

                if self.en_passant_target == (cap_r, cap_c):
                    behind_r = cap_r - direction
                    if self.in_bounds(behind_r, cap_c):
                        behind_piece = self.board[behind_r][cap_c]
                        if behind_piece == enemy + "p":
                            moves.append((r, c, cap_r, cap_c, None, "ep"))

    def generate_knight_moves(self, r: int, c: int, moves: List[Move]) -> None:
		# add all jumps for a knight
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
		# helper for bishops, rooks, queens
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
		# diagonal sliding moves
        dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        self.generate_sliding_moves(r, c, dirs, moves)

    def generate_rook_moves(self, r: int, c: int, moves: List[Move]) -> None:
		# orthogonal sliding moves
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        self.generate_sliding_moves(r, c, dirs, moves)

    def generate_queen_moves(self, r: int, c: int, moves: List[Move]) -> None:
		# queen combines rook and bishop directions
        dirs = [
            (-1, -1), (-1, 1), (1, -1), (1, 1),
            (-1, 0), (1, 0), (0, -1), (0, 1),
        ]
        self.generate_sliding_moves(r, c, dirs, moves)

    def generate_king_moves(self, r: int, c: int, moves: List[Move]) -> None:
		# normal king steps plus castling helper
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

        self._generate_castling_moves(r, c, moves)

    def _generate_castling_moves(self, r: int, c: int, moves: List[Move]) -> None:
		# check castling rights and add castle moves
        piece = self.board[r][c]
        if piece == "" or piece[1] != "K":
            return
        color = piece[0]
        enemy = opposite(color)
        row = 7 if color == "w" else 0
        if (r, c) != (row, 4):
            return
        if self.is_in_check(color):
            return

        def path_clear(cols: List[int]) -> bool:
            return all(self.board[row][col] == "" for col in cols)

        def path_safe(cols: List[int]) -> bool:
            return all(not self.is_square_attacked(row, col, enemy) for col in cols)

        if (color == "w" and "K" in self.castling_rights) or (color == "b" and "k" in self.castling_rights):
            rook_col = 7
            empty_cols = [5, 6]
            king_path = [5, 6]
            rook_piece = self.board[row][rook_col]
            if rook_piece == color + "R" and path_clear(empty_cols) and path_safe(king_path):
                moves.append((r, c, row, 6, None, "castle-k"))

        if (color == "w" and "Q" in self.castling_rights) or (color == "b" and "q" in self.castling_rights):
            rook_col = 0
            empty_cols = [1, 2, 3]
            king_path = [3, 2]
            rook_piece = self.board[row][rook_col]
            if rook_piece == color + "R" and path_clear(empty_cols) and path_safe(king_path):
                moves.append((r, c, row, 2, None, "castle-q"))
    def generate_all_moves(self) -> List[Move]:
		# produce pseudo legal moves for moving side
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
		# locate a king of given color
        target = color + "K"
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == target:
                    return r, c
        raise ValueError(f"King for {color} not found")

    def is_square_attacked(self, r: int, c: int, by_color: str) -> bool:
		# check whether color attacks a target square
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
		# test if given color king is under attack
        kr, kc = self.find_king(color)
        return self.is_square_attacked(kr, kc, opposite(color))

    def generate_legal_moves(self) -> List[Move]:
		# brute force filter to only legal moves
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
