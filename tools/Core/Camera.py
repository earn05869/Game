import pygame
from Core.Transform import Transform

class Camera:
	camera = None
	def __init__(self, width: int, height: int, zoom: float=1.0):
		self.rect = pygame.Rect(0, 0, width/zoom, height/zoom)
		Camera.camera = self

	def follow(self, target: pygame.sprite.Sprite):
		self.rect.center = target.rect.center

	def world_to_screen(self, world_rect: pygame.Rect) -> pygame.Rect:
		return world_rect.move(-self.rect.x, -self.rect.y)

	@staticmethod
	def get_camera():
		return Camera.camera