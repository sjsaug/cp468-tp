import tkinter as tk
from tkinter import messagebox
from typing import List, Optional
import threading

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

EXAMPLE_PUZZLES = {
    "mate2": ("8/8/8/8/8/1Q6/5K2/7k w - - 0 1", "w", 2),
    "mate3": ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1", "w", 3),
}

DEFAULT_FEN = EXAMPLE_PUZZLES["mate2"][0]


class ChessGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Chess Mate-in-N Solver")
        self.root.geometry("1000x700")
        self.root.configure(bg="#2c3e50")

        self.board: Board = Board.from_fen(DEFAULT_FEN)
        self.solving = False

        # Main container
        main_frame = tk.Frame(root, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel: Board
        left_frame = tk.Frame(main_frame, bg="#2c3e50")
        left_frame.pack(side=tk.LEFT, padx=10)

        self.canvas = tk.Canvas(
            left_frame, 
            width=BOARD_SIZE + 30, 
            height=BOARD_SIZE + 30,
            bg="#2c3e50", 
            highlightthickness=0
        )
        self.canvas.pack()

        # Right panel: Controls
        right_frame = tk.Frame(main_frame, bg="#2c3e50")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        # Title
        title = tk.Label(
            right_frame,
            text="♟ Chess Mate Solver ♔",
            font=("Arial", 18, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        title.pack(pady=10)

        # FEN Input Section
        fen_section = tk.LabelFrame(
            right_frame,
            text=" Position Setup ",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#34495e",
            relief=tk.RIDGE,
            bd=2
        )
        fen_section.pack(fill=tk.X, pady=5)

        tk.Label(
            fen_section,
            text="FEN Position:",
            font=("Arial", 9),
            fg="white",
            bg="#34495e"
        ).pack(anchor="w", padx=5, pady=(5, 0))

        self.fen_entry = tk.Entry(
            fen_section,
            width=60,
            font=("Courier", 9),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        self.fen_entry.pack(fill=tk.X, padx=5, pady=5)
        self.fen_entry.insert(0, DEFAULT_FEN)

        tk.Button(
            fen_section,
            text="📥 Load FEN",
            command=self.load_fen,
            bg="#27ae60",
            fg="white",
            font=("Arial", 9, "bold"),
            activebackground="#229954",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2"
        ).pack(fill=tk.X, padx=5, pady=(0, 5))

        # Solver Settings Section
        solver_section = tk.LabelFrame(
            right_frame,
            text=" Solver Settings ",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#34495e",
            relief=tk.RIDGE,
            bd=2
        )
        solver_section.pack(fill=tk.X, pady=5)

        # Attacker selection
        attacker_frame = tk.Frame(solver_section, bg="#34495e")
        attacker_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(
            attacker_frame,
            text="Attacking Side:",
            font=("Arial", 9, "bold"),
            fg="white",
            bg="#34495e"
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.attacker_var = tk.StringVar(value="w")
        tk.Radiobutton(
            attacker_frame,
            text="White",
            variable=self.attacker_var,
            value="w",
            font=("Arial", 9),
            fg="white",
            bg="#34495e",
            selectcolor="#2c3e50",
            activebackground="#34495e",
            activeforeground="white",
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

        tk.Radiobutton(
            attacker_frame,
            text="Black",
            variable=self.attacker_var,
            value="b",
            font=("Arial", 9),
            fg="white",
            bg="#34495e",
            selectcolor="#2c3e50",
            activebackground="#34495e",
            activeforeground="white",
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

        # Mate depth selection
        depth_frame = tk.Frame(solver_section, bg="#34495e")
        depth_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(
            depth_frame,
            text="Find Mate in:",
            font=("Arial", 9, "bold"),
            fg="white",
            bg="#34495e"
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.mate_depth = tk.IntVar(value=2)
        tk.Spinbox(
            depth_frame,
            from_=1,
            to=3,
            textvariable=self.mate_depth,
            width=5,
            font=("Arial", 10, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50",
            buttonbackground="#3498db",
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

        tk.Label(
            depth_frame,
            text="moves",
            font=("Arial", 9),
            fg="white",
            bg="#34495e"
        ).pack(side=tk.LEFT)

        # Solve button
        self.solve_button = tk.Button(
            solver_section,
            text="🔍 SOLVE PUZZLE",
            command=self.solve_puzzle_threaded,
            bg="#3498db",
            fg="white",
            font=("Arial", 12, "bold"),
            activebackground="#2980b9",
            relief=tk.RAISED,
            bd=3,
            cursor="hand2",
            height=2
        )
        self.solve_button.pack(fill=tk.X, padx=5, pady=10)

        # Progress indicator
        self.progress_label = tk.Label(
            solver_section,
            text="",
            font=("Arial", 9, "italic"),
            fg="#f39c12",
            bg="#34495e"
        )
        self.progress_label.pack(pady=(0, 5))

        # Example Puzzles Section
        examples_section = tk.LabelFrame(
            right_frame,
            text=" Example Puzzles ",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#34495e",
            relief=tk.RIDGE,
            bd=2
        )
        examples_section.pack(fill=tk.X, pady=5)

        examples = [
            ("Mate in 2", "mate2", "#27ae60"),
            ("Mate in 3", "mate3", "#e67e22"),
        ]

        for text, key, color in examples:
            tk.Button(
                examples_section,
                text=text,
                command=lambda k=key: self.load_example(k),
                bg=color,
                fg="white",
                font=("Arial", 9),
                activebackground=color,
                relief=tk.RAISED,
                bd=1,
                cursor="hand2"
            ).pack(fill=tk.X, padx=5, pady=2)

        # Solution Display Section
        solution_section = tk.LabelFrame(
            right_frame,
            text=" Solution ",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#34495e",
            relief=tk.RIDGE,
            bd=2
        )
        solution_section.pack(fill=tk.BOTH, expand=True, pady=5)

        text_frame = tk.Frame(solution_section, bg="#34495e")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.solution_text = tk.Text(
            text_frame,
            height=12,
            width=40,
            yscrollcommand=scrollbar.set,
            font=("Courier", 10),
            wrap=tk.WORD,
            bg="#2c3e50",
            fg="#ecf0f1",
            insertbackground="white",
            relief=tk.FLAT,
            padx=5,
            pady=5
        )
        self.solution_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.solution_text.yview)

        # Status Bar
        self.status_label = tk.Label(
            right_frame,
            text="✓ Ready - Load a puzzle or enter FEN",
            font=("Arial", 9, "bold"),
            fg="#27ae60",
            bg="#2c3e50",
            wraplength=350,
            justify=tk.CENTER
        )
        self.status_label.pack(pady=10)

        # Animation state
        self.solution_line: List = []
        self.anim_board: Optional[Board] = None

        # Initial draw
        self.draw_board(self.board)

    def draw_board(self, board: Board) -> None:
        """Draw the chess board with pieces and coordinates."""
        self.canvas.delete("all")

        # Draw squares
        for r in range(8):
            for c in range(8):
                x1 = c * SQUARE_SIZE
                y1 = r * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE

                color = LIGHT_COLOR if (r + c) % 2 == 0 else DARK_COLOR
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Draw pieces
        for r in range(8):
            for c in range(8):
                piece = board.board[r][c]
                if piece:
                    symbol = PIECE_SYMBOLS.get(piece, "?")
                    x = c * SQUARE_SIZE + SQUARE_SIZE // 2
                    y = r * SQUARE_SIZE + SQUARE_SIZE // 2
                    self.canvas.create_text(
                        x, y,
                        text=symbol,
                        font=("Arial", 40),
                        fill="#000000"
                    )

        # Draw coordinates
        for i in range(8):
            x = i * SQUARE_SIZE + SQUARE_SIZE // 2
            self.canvas.create_text(
                x, BOARD_SIZE + 15,
                text=chr(ord('a') + i),
                font=("Arial", 10, "bold"),
                fill="white"
            )
            y = i * SQUARE_SIZE + SQUARE_SIZE // 2
            self.canvas.create_text(
                BOARD_SIZE + 15, y,
                text=str(8 - i),
                font=("Arial", 10, "bold"),
                fill="white"
            )

    def load_fen(self) -> None:
        """Load a chess position from FEN string."""
        fen = self.fen_entry.get().strip()
        if not fen:
            self.status_label.config(text="⚠ Please enter a FEN string", fg="#e74c3c")
            return

        try:
            self.board = Board.from_fen(fen)
            self.draw_board(self.board)
            self.solution_line = []
            self.solution_text.delete(1.0, tk.END)

            side = "White" if self.board.side_to_move == "w" else "Black"
            self.status_label.config(
                text=f"✓ Position loaded - {side} to move",
                fg="#27ae60"
            )
        except Exception as e:
            self.status_label.config(text=f"✗ Error loading FEN: {e}", fg="#e74c3c")

    def load_example(self, key: str) -> None:
        """Load a pre-defined example puzzle."""
        if key in EXAMPLE_PUZZLES:
            fen, attacker, depth = EXAMPLE_PUZZLES[key]
            self.fen_entry.delete(0, tk.END)
            self.fen_entry.insert(0, fen)
            self.attacker_var.set(attacker)
            self.mate_depth.set(depth)
            self.load_fen()

    def solve_puzzle_threaded(self) -> None:
        """Start solver in a separate thread to prevent GUI freeze."""
        if self.solving:
            messagebox.showwarning(
                "Busy",
                "Already solving a puzzle. Please wait for it to complete."
            )
            return

        self.solving = True
        self.solve_button.config(state="disabled", text="⏳ SOLVING...")
        self.progress_label.config(text="Searching for solution...")

        # Run solver in background thread
        thread = threading.Thread(target=self.solve_puzzle, daemon=True)
        thread.start()

    def solve_puzzle(self) -> None:
        """Execute the mate search algorithm."""
        attacker = self.attacker_var.get()
        depth = self.mate_depth.get()
        side = "White" if attacker == "w" else "Black"

        try:
            # Update UI
            self.status_label.config(
                text=f"⏳ Solving: {side} to mate in {depth}...",
                fg="#f39c12"
            )
            self.solution_text.delete(1.0, tk.END)
            self.solution_text.insert(
                tk.END,
                f"Searching for {side} mate in {depth}...\n"
            )
            self.solution_text.insert(
                tk.END,
                "This may take a moment depending on complexity.\n\n"
            )
            self.root.update()

            # Call the solver from your existing solver.py
            can_mate, line = find_mate_line(self.board, attacker, depth)
            self.solution_line = line

            # Clear previous results
            self.solution_text.delete(1.0, tk.END)

            if not can_mate:
                # No mate found
                self.status_label.config(
                    text=f"✗ No forced mate in {depth} moves",
                    fg="#e74c3c"
                )
                self.solution_text.insert(
                    tk.END,
                    f"❌ No forced mate in {depth} found.\n\n"
                )
                self.solution_text.insert(tk.END, "Suggestions:\n")
                self.solution_text.insert(tk.END, "• Try a different depth\n")
                self.solution_text.insert(tk.END, "• Verify the position is correct\n")
                self.solution_text.insert(tk.END, "• Check the attacking side\n")
            else:
                # Mate found!
                self.status_label.config(
                    text=f"✓ Solution found: Mate in {depth}!",
                    fg="#27ae60"
                )
                self.solution_text.insert(tk.END, "✓ SOLUTION FOUND!\n")
                self.solution_text.insert(tk.END, "=" * 35 + "\n\n")
                self.solution_text.insert(tk.END, f"{side} mates in {depth} moves:\n\n")

                # Format the move sequence
                move_num = 1
                for i, move in enumerate(line):
                    move_str = move_to_str(move)

                    if i % 2 == 0:
                        self.solution_text.insert(tk.END, f"{move_num}. ")

                    self.solution_text.insert(tk.END, f"{move_str} ")

                    if i % 2 == 1:
                        self.solution_text.insert(tk.END, "\n")
                        move_num += 1

                if len(line) % 2 == 1:
                    self.solution_text.insert(tk.END, "\n")

                self.solution_text.insert(tk.END, "\n✓ Checkmate!\n")

                # Start animation
                self.anim_board = self.board.clone()
                self.root.after(500, lambda: self.animate_solution_step(0))

        except Exception as e:
            self.status_label.config(text=f"✗ Error: {str(e)}", fg="#e74c3c")
            self.solution_text.delete(1.0, tk.END)
            self.solution_text.insert(tk.END, f"Error occurred:\n{str(e)}\n")

        finally:
            # Re-enable the solve button
            self.solving = False
            self.solve_button.config(state="normal", text="🔍 SOLVE PUZZLE")
            self.progress_label.config(text="")

    def animate_solution_step(self, index: int) -> None:
        """Animate the solution move by move."""
        if self.anim_board is None or index >= len(self.solution_line):
            return

        move = self.solution_line[index]
        self.anim_board.make_move(move)
        self.draw_board(self.anim_board)

        # Schedule next move
        self.root.after(1000, lambda: self.animate_solution_step(index + 1))


if __name__ == "__main__":
    root = tk.Tk()
    gui = ChessGUI(root)
    root.mainloop()
