from Script.Engine.Component import Component
from Script.Engine.Transfrom import Transfrom
from Script.Engine.Sprite import Sprite
import pygame

class GameObject(Component):
	def __init__(self, name: str, transfrom: Transfrom):
		super().__init__()
		self.name = name
		self.transfrom = transfrom
		surface = pygame.Surface(transfrom.get_size())
		surface.set_alpha(255)
		self.sprite = Sprite(surface, self.transfrom)

	def update(dt: float):
		pass

	def draw(screen: pygame.Surface):
		pass