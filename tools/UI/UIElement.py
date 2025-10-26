import pygame
from Core.Camera import Camera

class UIElement:
	def __init__(self, position=(0,0), size=(100,50), world_space=False, image=None):
		self.position = pygame.Vector2(position)
		self.size = pygame.Vector2(size)
		self.children = []
		self.parent = None
		self.visible = True
		self.world_space = world_space
		self.image = image  # image property
		self.rect = pygame.Rect(self.position.x, self.position.y, self.size.x, self.size.y)
		self.camera = Camera.get_camera();

	def add_child(self, child: 'UIElement'):
		child.parent = self
		self.children.append(child)
  
	def global_position(self):
		pos = self.position.copy()
		if self.parent:
			pos += self.parent.global_position()
		if self.world_space and self.camera:
			pos -= pygame.Vector2(self.camera.rect.topleft)
		return pos

	def draw(self, surface: pygame.Surface):
		if not self.visible:
			return
		pos = self.global_position()
		if self.image:
			surface.blit(self.image, pos)
		for child in self.children:
			child.draw(surface)
