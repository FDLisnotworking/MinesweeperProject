from datetime import datetime
import sys
import matplotlib.pyplot as plt
import mysql.connector
import pygame
from settings import *
from sprites import *


class Game:

    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Minesweeper")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 28, bold=True)
        self.reset_game()
        #Initializing Pygame module and timer with class

    def reset_game(self):
        self.board = Board()
        self.game_over = False
        self.win = False
        self.start_ticks = None
        self.elapsed_ms = 0
        #Reset game

    def run(self):
        self.playing = True
        while self.playing:
            self.clock.tick(60)
            self.events()
            self.update()
            self.draw()

    def update(self):
        if self.start_ticks is not None and not self.game_over and not self.win:
            self.elapsed_ms = pygame.time.get_ticks() - self.start_ticks

    def check_win(self):
        #checks win condition is true
        for row in self.board.board_list:
            for tile in row:
                if tile.type != "X" and not tile.revealed:
                    return False
        return True

    def save_win_time(self):
        try:
            conn = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD
            )
            cursor = conn.cursor()

            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            cursor.execute(f"USE {DB_NAME}")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS leaderboard (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    time VARCHAR(20) NOT NULL,
                    victory_date DATETIME NOT NULL
                )
            """
            )

            mins = self.elapsed_ms // 60000
            secs = (self.elapsed_ms % 60000) // 1000
            ms = self.elapsed_ms % 1000
            formatted_time = f"{mins:02d}:{secs:02d}.{ms:03d}"
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            query = (
                "INSERT INTO leaderboard (time, victory_date) VALUES (%s, %s)"
            )
            cursor.execute(query, (formatted_time, current_date))
            conn.commit()

            cursor.close()
            conn.close()
            print(
                f"Victory saved! Time: {formatted_time} | Date: {current_date}"
            )
        #for saving the best times to MySQL Database
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")

    def time_str_to_seconds(self, time_str):
        #convert the saved time from python to something usable by SQL
        mins, rest = time_str.split(":")
        secs, ms = rest.split(".")
        return int(mins) * 60 + int(secs) + int(ms) / 1000.0

    def show_stats_graph(self):
        """Fetches score history from MySQL and plots recent attempts & best time using Matplotlib."""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
            )
            cursor = conn.cursor()

            #Fetch last 10 attempts
            cursor.execute(
                "SELECT time FROM leaderboard ORDER BY id DESC LIMIT 10"
            )
            recent_rows = cursor.fetchall()

            #Fetch all times to determine overall best time
            cursor.execute("SELECT time FROM leaderboard")
            all_rows = cursor.fetchall()

            cursor.close()
            conn.close()

            if not recent_rows:
                print("No victory statistics found in database yet.")
                return

            #Convert fetched strings to seconds
            recent_times = [
                self.time_str_to_seconds(r[0]) for r in reversed(recent_rows)
            ]
            all_times = [self.time_str_to_seconds(r[0]) for r in all_rows]

            best_time = min(all_times)
            attempts = list(range(1, len(recent_times) + 1))

            #Plot graph with Matplotlib
            plt.figure(figsize=(9, 5))
            plt.plot(
                attempts,
                recent_times,
                marker="o",
                color="#007acc",
                linewidth=2,
                label="Recent Victory Times",
            )
            plt.axhline(
                y=best_time,
                color="#e74c3c",
                linestyle="--",
                linewidth=2,
                label=f"Best Time ({best_time:.2f}s)",
            )

            #Graph
            for i, txt in enumerate(recent_times):
                plt.annotate(
                    f"{txt:.2f}s",
                    (attempts[i], recent_times[i]),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                )

            plt.title("Minesweeper Performance (Previous 10 Wins)")
            plt.xlabel("Attempt (Recent Wins)")
            plt.ylabel("Time (Seconds)")
            plt.xticks(attempts)
            plt.grid(True, linestyle=":", alpha=0.6)
            plt.legend()
            plt.tight_layout()
            plt.show()

        except mysql.connector.Error as err:
            print(f"Database Error while fetching stats: {err}")

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                if my < 50:
                    continue

                grid_x = mx // TILESIZE
                grid_y = (my - 50) // TILESIZE

                if self.start_ticks is None:
                    self.start_ticks = pygame.time.get_ticks()

                if not self.game_over and not self.win:
                    #Left click
                    if event.button == 1:
                        if not self.board.board_list[grid_x][grid_y].flagged:
                            if not self.board.dig(grid_x, grid_y):
                                self.game_over = True
                                self.board.reveal_all_mines()
                                print("Game Over!")
                            elif self.check_win():
                                self.win = True
                                print("You Win!")
                                self.save_win_time()

                    #Right click
                    elif event.button == 3:
                        tile = self.board.board_list[grid_x][grid_y]
                        if not tile.revealed:
                            tile.flagged = not tile.flagged

            if event.type == pygame.KEYDOWN:
                #Press 'R' to restart
                if event.key == pygame.K_r:
                    self.reset_game()

                #Press 'G' to show performance graph
                if event.key == pygame.K_g:
                    self.show_stats_graph()

    def draw_header(self):
        header_rect = pygame.Rect(0, 0, WIDTH, 50)
        pygame.draw.rect(self.screen, BLACK, header_rect)

        mins = self.elapsed_ms // 60000
        secs = (self.elapsed_ms % 60000) // 1000
        ms = self.elapsed_ms % 1000

        time_str = f"TIME: {mins:02d}:{secs:02d}.{ms:03d}"
        timer_surface = self.font.render(time_str, True, WHITE)
        timer_rect = timer_surface.get_rect(
            topright=(WIDTH - 15, 50 // 2 - 14)
        )

        flags_count = sum(
            1
            for col in self.board.board_list
            for tile in col
            if tile.flagged
        )
        mines_left = AMOUNT_MINES - flags_count

        if self.win:
            mines_str = "YOU WIN! (Press G for Stats)"
        elif self.game_over:
            mines_str = "GAME OVER"
        else:
            mines_str = f"MINES: {mines_left:03d}"

        mines_surface = self.font.render(mines_str, True, WHITE)
        mines_rect = mines_surface.get_rect(
            topleft=(15, 50 // 2 - 14)
        )

        self.screen.blit(timer_surface, timer_rect)
        self.screen.blit(mines_surface, mines_rect)

    def draw(self):
        self.screen.fill(BGCOLOUR)
        self.draw_header()
        self.board.draw(self.screen)
        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
