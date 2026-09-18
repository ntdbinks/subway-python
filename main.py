"""Point d'entrée : python main.py"""
import pygame

from src import config as C
from src.game import Game


def main():
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass  # pas de carte son : le jeu tourne sans audio
    screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption(C.TITLE)
    clock = pygame.time.Clock()

    game = Game(screen)
    while game.running:
        dt = clock.tick(C.FPS) / 1000
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(dt)
        game.draw()
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
