import pygame

class InputHandle:
    keys = None
    mouse_pos = (0, 0)
    mouse_buttons = (0, 0, 0)

    @staticmethod
    def update():
        InputHandle.keys = pygame.key.get_pressed()
        InputHandle.mouse_pos = pygame.mouse.get_pos()
        InputHandle.mouse_buttons = pygame.mouse.get_pressed()

    @staticmethod
    def is_key_pressed(key):
        return InputHandle.keys[key]
