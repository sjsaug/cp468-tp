import tkinter as tk
from typing import List
from engine import Board
from solver import find_mate_line, move_to_str

SQUARE_SIZE = 60
BOARD_SIZE = SQUARE_SIZE * 8

LIGHT_COLOR = "#f0d9b5"
DARK_COLOR = "#b58863"

PIECE_SYMBOLS = {
    "wK": "♔", "wQ": "♕", "wR": "♖", "wB": "♗", "wN": "♘", "wp": "♙",
    "bK": "♚", "bQ": "♛", "bR": "♜", "bB": "♝", "bN": "♞", "bp": "♟",
}

# Default puzzle: White to move, mate in 2 (simple example)
DEFAULT_FEN = "8/8/8/8/8/1Q6/5K2/7k w - - 0 1"


class ChessGUI:
    def __init__(self, root: tk.Tk):
		# wire up widgets and load default board
        self.root = root
        self.root.title("Chess Mate-in-N Solver")

        # Current logical board (puzzle position)
        self.board: Board = Board.from_fen(DEFAULT_FEN)

        # Canvas for drawing the board
        self.canvas = tk.Canvas(root, width=BOARD_SIZE, height=BOARD_SIZE)
        self.canvas.pack(padx=10, pady=10)

        # FEN input
        fen_frame = tk.Frame(root)
        fen_frame.pack(pady=5)

        tk.Label(fen_frame, text="FEN:").pack(side=tk.LEFT)
        self.fen_entry = tk.Entry(fen_frame, width=70)
        self.fen_entry.pack(side=tk.LEFT, padx=5)
        self.fen_entry.insert(0, DEFAULT_FEN)

        tk.Button(
            fen_frame,
            text="Load FEN",
            command=self.load_fen
        ).pack(side=tk.LEFT, padx=5)

        # Control buttons
        controls = tk.Frame(root)
        controls.pack(pady=5)

        # White buttons
        tk.Button(
            controls,
            text="White mate in 2",
            command=lambda: self.solve_mate("w", 2)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            controls,
            text="White mate in 3",
            command=lambda: self.solve_mate("w", 3)
        ).pack(side=tk.LEFT, padx=5)

        # Black buttons
        tk.Button(
            controls,
            text="Black mate in 2",
            command=lambda: self.solve_mate("b", 2)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            controls,
            text="Black mate in 3",
            command=lambda: self.solve_mate("b", 3)
        ).pack(side=tk.LEFT, padx=5)

        # Info label
        self.info_label = tk.Label(
            root,
            text="Loaded default puzzle (White to move). Try any mate-in-N button."
        )
        self.info_label.pack(pady=5)

        # For animation
        self.solution_line: List = []
        self.anim_board: Board | None = None

        # Initial draw
        self.draw_board(self.board)

    # --- Drawing ---

    def draw_board(self, board: Board) -> None:
		# redraw squares and text symbols
        self.canvas.delete("all")

        # Draw squares
        for r in range(8):
            for c in range(8):
                x1 = c * SQUARE_SIZE
                y1 = r * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE

                color = LIGHT_COLOR if (r + c) % 2 == 0 else DARK_COLOR
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

        # Draw pieces (Board.board[0][0] is a8 = top-left)
        for r in range(8):
            for c in range(8):
                piece = board.board[r][c]
                if not piece:
                    continue
                symbol = PIECE_SYMBOLS.get(piece, "?")
                x = c * SQUARE_SIZE + SQUARE_SIZE // 2
                y = r * SQUARE_SIZE + SQUARE_SIZE // 2
                self.canvas.create_text(
                    x, y, text=symbol, font=("Arial", 32), fill="black"
                )

    # --- FEN loading ---

    def load_fen(self) -> None:
		# pull fen string from entry and refresh board
        fen = self.fen_entry.get().strip()
        try:
            self.board = Board.from_fen(fen)
            self.draw_board(self.board)
            self.info_label.config(
                text=f"FEN loaded. Side to move: {self.board.side_to_move.upper()}."
            )
        except Exception as e:
            self.info_label.config(text=f"Error loading FEN: {e}")

    # --- Solving ---

    def solve_mate(self, attacker_color: str, n: int) -> None:
		# run search for given color and depth
        side = "White" if attacker_color == "w" else "Black"
        self.info_label.config(text=f"Solving: {side} to move, mate in {n}...")
        self.root.update_idletasks()

        can_mate, line = find_mate_line(self.board, attacker=attacker_color, attacker_moves=n)
        self.solution_line = line

        if not can_mate:
            self.info_label.config(text=f"No forced mate in {n} found for {side}.")
            return

        # Show line in text form
        move_strs = [move_to_str(m) for m in line]
        self.info_label.config(
            text=f"{side} has mate in {n}! Line: " + " ".join(move_strs)
        )

        # Prepare animation
        self.anim_board = self.board.clone()
        self.draw_board(self.anim_board)
        self.animate_solution_step(0)

    # --- Animation ---

    def animate_solution_step(self, index: int) -> None:
		# play back search line on timer
        if self.anim_board is None:
            return
        if index >= len(self.solution_line):
            return

        move = self.solution_line[index]
        self.anim_board.make_move(move)
        self.draw_board(self.anim_board)

        # Schedule next move
        self.root.after(800, lambda: self.animate_solution_step(index + 1))


if __name__ == "__main__":
    root = tk.Tk()
    gui = ChessGUI(root)
    root.mainloop()

