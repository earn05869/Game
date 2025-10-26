import pygame
from Core.Transform import Transform
from Core.Vector import Vector
from Core.CollisionManager import CollisionManager
from Core.Collider import BoxCollider

class GameObject(pygame.sprite.Sprite):
	def __init__(self, name: str="GameObject", sprite: str=None, position: tuple=(0,0)):
		super().__init__()
		self.name = name
		self.transform = Transform(Vector(*position))
		self.sprite = sprite or pygame.Surface((50,50))
		if not sprite:
			self.sprite.fill((0, 255, 0))
		self.active = True
		self.rect = self.sprite.get_rect(center=position)
  
	def add_collision(self, collision, collider):
		self.collider = collider
		collision.add_collider(self.collider)

	def update(self):
		super().update()
		self.rect.topleft = self.transform.to_tuple()

	def draw(self, screen: pygame.Surface):
		if not self.active:
			return
		x, y = self.transform.position.x, self.transform.position.y
		screen.blit(self.sprite, self.rect.topleft)
  
	def on_collision_enter(self, other):
		print(f"Collided with {other.game_object.name}")
