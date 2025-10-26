import pygame
from Core.Camera import Camera
class Collider:
	def __init__(self, game_object, offset=(0,0), is_trigger=False):
		self.camera = Camera.camera
		self.game_object = game_object  # parent GameObject
		self.offset = pygame.Vector2(offset)
		self.is_trigger = is_trigger
		self.isdebug = False
		self.rect = pygame.Rect(
			self.game_object.transform.position.x + self.offset.x,
			self.game_object.transform.position.y + self.offset.y,
			self.game_object.rect.width,
			self.game_object.rect.height
		)
	
	def set_debug(self, isdebug):
		self.isdebug = isdebug
		
	def draw(self, surface: pygame.Surface):
		if self.isdebug:
			rect_to_draw = self.rect.copy()
			if self.camera:
				rect_to_draw.topleft = (
					self.rect.x - self.camera.rect.x,
					self.rect.y - self.camera.rect.y
				)
			pygame.draw.rect(surface, (255,0,0), rect_to_draw, 2)

	def update(self):
		self.rect.topleft = (
			self.game_object.transform.position.x + self.offset.x,
			self.game_object.transform.position.y + self.offset.y
		)

	def on_collision_enter(self, other):
		pass  # override by subclass

	def on_collision_stay(self, other):
		pass

	def on_collision_exit(self, other):
		pass


class BoxCollider(Collider):
	def __init__(self, game_object, offset=(0,0)):
		super().__init__(game_object, offset)
