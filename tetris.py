from enum import Enum
from dataclasses import dataclass
from itertools import chain
import random
import curses
import time

@dataclass
class Loc:
    row: int
    col: int

class Dir(Enum):
    N = 0
    E = 1
    S = 2
    W = 3

def rotation(shape: tuple[int]):
    """
        Renvoie la forme,
        la nouvelle hauteur et la nouvelle largeur.
    """
    height = len(shape)
    width = max(layer.bit_length() for layer in shape)
    
    return tuple(int("".join(new_layer), 2) for new_layer in zip(*tuple(f"{layer:0>{width}b}" for layer in shape)[::-1]))

class Piece:
    def __init__(self, loc, shape):
        """
          'loc' est la position du coin inférieur gauche de la boîte englobante rectangulaire de l’œuvre
        """
        self.shapes: dict[Dir, tuple[int]] = {
            Dir.N: shape,
            Dir.W: rotation(shape),
            Dir.S: rotation(rotation(shape)),
            Dir.E: rotation(rotation(rotation(shape))),
        }
        self.loc: Loc = loc
        self.rot: Dir = Dir.N
        self.widths = {d: max(layer.bit_length() for layer in shape) for d, shape in self.shapes.items()}
        self.heights = {d: len(shape) for d, shape in self.shapes.items()}

    def get_width(self):
        return self.widths[self.rot]

    def get_height(self):
        return self.widths[self.rot]

    def get_bits(self):
        return (layer << (self.loc.col - self.get_width()) for layer in self.shapes[self.rot])

    def rot_right(self):
        self.rot = Dir((self.rot.value + 1) % 4)

    def rot_left(self):
        self.rot = Dir((self.rot.value - 1) % 4)

    def __str__(self):
        return "\n".join(f"{layer:0>{self.get_width()}b}" for layer in reversed(self.shapes[Dir.N]))

SHAPES = {"o": (0b11, 0b11), "i": (1, 1, 1, 1), "s": (0b110, 0b011), "z": (0b011, 0b110), "j": (0b11, 1, 1), "l": (0b11, 0b10, 0b10), "t": (0b010, 0b111), 
        }

class Tetris:
    # Le jeu se deroule sur une grille de 10 colonnes par 20 lignes
    def __init__(self, height=20, width=10, starting_level=0):
        """
        La rangée 0 est la couche la plus basse.
        La colonne 0 est la colonne la plus à droite.
        Il y a toujours une pièce actuelle.
        """
        self.width: int = width
        self.height: int = height
        self.board: list[int] = []
        self.FULL_ROW = 2 ** width - 1
        self.current_piece: None | int = None
        self._next_piece()

        self.hold_piece: None | Piece = None
        self.cleared_lines: int = 0
        self.starting_level: int = starting_level
        self.game_over: bool = False

    def _add_piece(self, shape):
        new_piece = Piece(Loc(self.height - len(shape), self.width // 2), shape)
        self.current_piece = new_piece
        if not self.piece_en_cours():
            self.game_over = True

    def _next_piece(self):
        self._add_piece(random.choice(list(SHAPES.values())))

    def _clear_rows(self):
        prev_num_lines = len(self.board)
        self.board = [layer for layer in self.board if layer != self.FULL_ROW]
        self.cleared_lines += prev_num_lines - len(self.board)

    def _stop_piece(self):
        shape = self.current_piece.get_bits()
        for row, layer in enumerate(shape):
            layer_row = row + self.current_piece.loc.row
            if layer_row < len(self.board):
                self.board[layer_row] |= layer
            else:
                self.board.append(layer)
        self._clear_rows()
        self._next_piece()
        self.can_hold = True

    def piece_en_cours(self):
        if self.current_piece.loc.row < 0:
            return False
        if self.current_piece.loc.col > self.width:
            return False
        if self.current_piece.loc.col - self.current_piece.get_width() < 0:
            return False
        shape = self.current_piece.get_bits()
        for row, layer in enumerate(shape):
            layer_row = row + self.current_piece.loc.row
            if layer_row >= len(self.board):
                break
            if self.board[layer_row] & layer != 0:
                return False
        return True

    def move_down(self):
        self.current_piece.loc.row -= 1
        if not self.piece_en_cours():
            self.current_piece.loc.row += 1
            self._stop_piece()
            return False
        return True

    def drop(self):
        while self.move_down():
            pass

    def move_left(self):
        self.current_piece.loc.col += 1
        if not self.piece_en_cours():
            self.current_piece.loc.col -= 1

    def move_right(self):
        self.current_piece.loc.col -= 1
        if not self.piece_en_cours():
            self.current_piece.loc.col += 1

    def rot_right(self):
        self.current_piece.rot_right()
        if not self.piece_en_cours():
            self.current_piece.rot_left()

    def rot_left(self):
        self.current_piece.rot_left()
        if not self.piece_en_cours():
            self.current_piece.rot_right()
    

    def hold(self):
        if self.hold_piece is None:
            self.hold_piece = self.current_piece
            self._next_piece()
        elif self.can_hold:
            held_shape = self.hold_piece.shapes[Dir.N]
            self.hold_piece = self.current_piece
            self._add_piece(held_shape)
        self.can_hold = False

    def get_level(self):
        return self.starting_level + (self.cleared_lines // 10)

    def __str__(self):
        current_piece_bits = tuple(self.current_piece.get_bits())
        current_piece_row = self.current_piece.loc.row
        def get_row_num_bits(row, layer):
            if 0 <= row - current_piece_row < len(current_piece_bits):
                return layer | current_piece_bits[row - current_piece_row]
            return layer
        return "\n".join(f"{get_row_num_bits(self.height - i - 1, layer):0>{self.width}b}" for i, layer in enumerate(chain([0] * (self.height - len(self.board)), reversed(self.board))))
     
def main(stdscr):
    stdscr.nodelay(True)
    stdscr.leaveok(True)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_BLACK)

    t = Tetris()
    NS_PER_FRAME = 800 * 1000 * 1000
    NS_PER_LEVEL = 50 * 1000 * 1000
    countdown_start = time.time_ns()

    def print_board():
        stdscr.clear()
        for c in str(t):
            stdscr.addch(c, curses.color_pair(1 if c == "1" else 2))
        stdscr.addstr(f"""

CORBEILLE:
""")
        for c in str(t.hold_piece):
            stdscr.addch(c, curses.color_pair(1 if c == "1" else 2))
        stdscr.addstr(f"""

SCORE: {t.cleared_lines}

NIVEAU: {t.get_level()}
""")
            
    print_board()
    while True:
        ch = stdscr.getch()
        if ch == curses.KEY_DOWN:
            t.move_down()
        if ch == curses.KEY_LEFT:
            t.move_left()
        if ch == curses.KEY_RIGHT:
            t.move_right()
        if ch == ord(" "):
            t.drop()
        if ch == ord("x"):
            t.rot_right()
        if ch == ord("z"):
            t.rot_left()
        if ch == ord("r"):
            t.__init__()
        if ch == ord("c"):
            t.hold()
        if ch != curses.ERR:
            print_board()
        if time.time_ns() - countdown_start >= NS_PER_FRAME - t.get_level() * NS_PER_LEVEL:
            countdown_start = time.time_ns()
            t.move_down()
            print_board()

    while True:
        pass

if __name__ == "__main__":
    curses.wrapper(main)
