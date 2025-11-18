import pygame
import random
import sys
from copy import deepcopy

# Configurações principais
CELL_SIZE = 30
COLS = 10
ROWS = 20

FIELD_WIDTH = CELL_SIZE * COLS
FIELD_HEIGHT = CELL_SIZE * ROWS
SIDE_PANEL = 200
WIDTH = FIELD_WIDTH + SIDE_PANEL
HEIGHT = FIELD_HEIGHT
FPS = 5

BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
WHITE = (255, 255, 255)

COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0)
}


PIECES = {
    'I': [
        ["....",
         "1111",
         "....",
         "...."],
        ["..1.",
         "..1.",
         "..1.",
         "..1."]
    ],
    'O': [
        ["....",
         ".11.",
         ".11.",
         "...."]
    ],
    'T': [
        ["....",
         ".1..",
         "111.",
         "...."],
        ["....",
         ".1..",
         ".11.",
         ".1.."],
        ["....",
         "111.",
         ".1..",
         "...."],
        ["....",
         ".1..",
         "11..",
         ".1.."]
    ],
    'S': [
        ["....",
         ".11.",
         "11..",
         "...."],
        ["....",
         ".1..",
         ".11.",
         "..1."]
    ],
    'Z': [
        ["....",
         "11..",
         ".11.",
         "...."],
        ["....",
         "..1.",
         ".11.",
         ".1.."]
    ],
    'J': [
        ["....",
         "1...",
         "111.",
         "...."],
        ["....",
         ".11.",
         ".1..",
         ".1.."],
        ["....",
         "111.",
         "..1.",
         "...."],
        ["....",
         ".1..",
         ".1..",
         "11.."]
    ],
    'L': [
        ["....",
         "..1.",
         "111.",
         "...."],
        ["....",
         ".1..",
         ".1..",
         ".11."],
        ["....",
         "111.",
         "1...",
         "...."],
        ["....",
         "11..",
         ".1..",
         ".1.."]
    ]
}

def rotate_shape(shape, r):
    return shape[r % len(shape)]

def shape_to_coords(matrix):
    coords = []
    for y, row in enumerate(matrix):
        for x, ch in enumerate(row):
            if ch == '1':
                coords.append((x, y))
    return coords

class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.variants = PIECES[kind]
        self.rotation = 0
        self.x = COLS // 2 - 2
        self.y = -2

    def get_shape(self):
        return rotate_shape(self.variants, self.rotation)

    def get_coords(self):
        shape = self.get_shape()
        coords = shape_to_coords(shape)
        return [(self.x + x, self.y + y) for x, y in coords]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(self.variants)

    def undo_rotate(self):
        self.rotation = (self.rotation - 1) % len(self.variants)

class Board:
    def __init__(self):
        self.grid = [['' for _ in range(COLS)] for _ in range(ROWS)]

    def clone(self):
        b = Board()
        b.grid = deepcopy(self.grid)
        return b

    def is_valid_position(self, piece, offset_x=0, offset_y=0):
        for x, y in piece.get_coords():
            x_off = x + offset_x
            y_off = y + offset_y
            if x_off < 0 or x_off >= COLS:
                return False
            if y_off >= ROWS:
                return False
            if y_off >= 0 and self.grid[y_off][x_off]:
                return False
        return True

    def place_piece(self, piece):
        for x, y in piece.get_coords():
            if 0 <= y < ROWS and 0 <= x < COLS:
                self.grid[y][x] = piece.kind

    def remove_full_lines(self):
        new_grid = [row for row in self.grid if '' in row]
        removed = ROWS - len(new_grid)
        for _ in range(removed):
            new_grid.insert(0, ['' for _ in range(COLS)])
        self.grid = new_grid
        return removed

    
    def aggregate_height(self):
        heights = []
        for x in range(COLS):
            h = 0
            for y in range(ROWS):
                if self.grid[y][x]:
                    h = ROWS - y
                    break
            heights.append(h)
        return sum(heights), heights

    def count_holes(self):
        holes = 0
        for x in range(COLS):
            block_found = False
            for y in range(ROWS):
                if self.grid[y][x]:
                    block_found = True
                elif block_found and not self.grid[y][x]:
                    holes += 1
        return holes

    def bumpiness(self, heights):
        b = 0
        for i in range(len(heights)-1):
            b += abs(heights[i] - heights[i+1])
        return b

class Game:
    def __init__(self):
        self.board = Board()
        self.piece = self.get_new_piece()
        self.next_piece = self.get_new_piece()
        self.game_over = False
        self.score = 0

        
        self.drop_interval_ms = 500
        self.last_drop_time = pygame.time.get_ticks()

        
        self.ai_enabled = True 
        self.ai_target_x = None
        self.ai_target_rot = None
        self.ai_action_delay = 50  
        self.last_ai_action = pygame.time.get_ticks()

    def get_new_piece(self):
        return Piece(random.choice(list(PIECES.keys())))

    def step(self):
        now = pygame.time.get_ticks()
        if now - self.last_drop_time >= self.drop_interval_ms:
            self.last_drop_time = now
            if not self.move_piece(0, 1):
                self.board.place_piece(self.piece)
                lines = self.board.remove_full_lines()
                self.score += [0, 40, 100, 300, 1200][lines] if lines < 5 else 1200 * (lines // 4)
                self.piece = self.next_piece
                self.next_piece = self.get_new_piece()
                if not self.board.is_valid_position(self.piece):
                    self.game_over = True

        #  calcula ações aos poucos
        if self.ai_enabled and not self.game_over:
            # Recalcula 
            if self.ai_target_x is None or self.ai_target_rot is None:
                best = self.compute_best_move()
                if best:
                    self.ai_target_x, self.ai_target_rot = best
            
            if self.ai_target_x is not None and self.ai_target_rot is not None:
                if now - self.last_ai_action >= self.ai_action_delay:
                    self.last_ai_action = now
                   
                    if self.piece.rotation != self.ai_target_rot:
                        self.rotate_piece()
                    else:
                       
                        if self.piece.x < self.ai_target_x:
                            self.move_piece(1, 0)
                        elif self.piece.x > self.ai_target_x:
                            self.move_piece(-1, 0)
                        else:
                            
                            self.hard_drop()
                            
                            self.ai_target_x = None
                            self.ai_target_rot = None

    def move_piece(self, dx, dy):
        new_piece = deepcopy(self.piece)
        new_piece.x += dx
        new_piece.y += dy
        if self.board.is_valid_position(new_piece):
            self.piece = new_piece
            return True
        return False

    def rotate_piece(self):
        self.piece.rotate()
        kicks = [(0,0), (-1,0), (1,0), (-2,0), (2,0)]
        for kx, ky in kicks:
            if self.board.is_valid_position(self.piece, offset_x=kx, offset_y=ky):
                self.piece.x += kx
                self.piece.y += ky
                return
        self.piece.undo_rotate()

    def hard_drop(self):
        while self.move_piece(0, 1):
            pass
        self.board.place_piece(self.piece)
        lines = self.board.remove_full_lines()
        self.score += [0, 40, 100, 300, 1200][lines] if lines < 5 else 1200 * (lines // 4)
        self.piece = self.next_piece
        self.next_piece = self.get_new_piece()
        if not self.board.is_valid_position(self.piece):
            self.game_over = True
        # reseta IA apos queda
        self.ai_target_x = None
        self.ai_target_rot = None

   
    def compute_best_move(self):
    #peso e simular jogadas
        w_lines = 1000.0
        w_height = 4.0
        w_holes = 100.0
        w_bump = 4.0

        best_score = -1e9
        best_move = None

        
        for rot in range(len(self.piece.variants)):
           
            test_piece = Piece(self.piece.kind)
            test_piece.rotation = rot

            min_x = -2  
            max_x = COLS + 2
            # testar  colunas
            for x in range(-2, COLS+2):
                test_piece.x = x
                test_piece.y = self.piece.y

          
                sim_piece = deepcopy(test_piece)
                while self.board.is_valid_position(sim_piece):
                    sim_piece.y += 1
                sim_piece.y -= 1  

            
                if not self.board.is_valid_position(sim_piece):
                    continue

                # simular tabuleiro
                b_clone = self.board.clone()
                b_clone.place_piece(sim_piece)
                lines = b_clone.remove_full_lines()

                total_height, heights = b_clone.aggregate_height()
                holes = b_clone.count_holes()
                bump = b_clone.bumpiness(heights)

                score = (w_lines * lines) - (w_height * total_height) - (w_holes * holes) - (w_bump * bump)

                
                score -= abs(x - COLS/2) * 0.1

                if score > best_score:
                    best_score = score
                    best_move = (x, rot)

        return best_move

def draw_board(screen, board):
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, GRAY, rect, 1)
            if board.grid[y][x]:
                color = COLORS[board.grid[y][x]]
                pygame.draw.rect(screen, color, rect.inflate(-2,-2))

def draw_piece(screen, piece):
    for x, y in piece.get_coords():
        if y >= 0:
            rect = pygame.Rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            color = COLORS[piece.kind]
            pygame.draw.rect(screen, color, rect.inflate(-2,-2))

def draw_next_piece(screen, piece):
    shape = rotate_shape(piece.variants, 0)
    for x, y in shape_to_coords(shape):
        rect = pygame.Rect(FIELD_WIDTH + 40 + x*CELL_SIZE, 60 + y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
        color = COLORS[piece.kind]
        pygame.draw.rect(screen, color, rect.inflate(-2,-2))

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 28)
    game = Game()

    while True:
        screen.fill(BLACK)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
              
                if not game.game_over and not game.ai_enabled:
                    if event.key == pygame.K_LEFT:
                        game.move_piece(-1,0)
                    elif event.key == pygame.K_RIGHT:
                        game.move_piece(1,0)
                    elif event.key == pygame.K_DOWN:
                        game.move_piece(0,1)
                    elif event.key == pygame.K_UP:
                        game.rotate_piece()
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()
                
               

        if not game.game_over:
            game.step()

        draw_board(screen, game.board)
        draw_piece(screen, game.piece)
        draw_next_piece(screen, game.next_piece)

        score_surf = font.render(f'Score: {game.score}', True, WHITE)
        screen.blit(score_surf, (FIELD_WIDTH + 20, 20))

     
        if game.game_over:
            over_surf = font.render('GAME OVER!', True, (200,40,40))
            screen.blit(over_surf, (FIELD_WIDTH // 2 - 90, FIELD_HEIGHT // 2))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
