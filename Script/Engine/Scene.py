import pygame
from Script.Engine.Camera import Camera
from Script.Engine.GameObject import GameObject

class Scene:
	def __init__(self, camera: Camera, map_path: str, zoom: float = 1, ):
		self.obj = pygame.sprite.Group()
		self.gameOBJ = []
		self.rect_list: list = []
		self.camera = camera
		self.map_path = map_path
		self.width = 0
		self.height = 0
		self.zoom = zoom
  
	def add_gameOBJ(self, obj: GameObject):
		self.obj.add(obj.sprite)
		self.gameOBJ.append(obj)
		self.rect_list.append(obj.transfrom)
  
	def render(self, screen: pygame.Surface):
		pass

	def event(self, event):
		pass

	def update(self):
		pass