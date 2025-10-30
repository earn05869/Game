import pygame
from Script.UI.UIElement import UIElement

class Panel(UIElement):
	def __init__(self, position=(0,0), size=(100,50), color=(50,50,50), image=None, world_space=True):
		if image:
			img = pygame.transform.scale(image, size)
		else:
			img = pygame.Surface(size)
			img.fill(color)
		super().__init__(position=position, size=size, world_space=world_space, image=img)
