from Script.Engine.Transfrom import Transfrom
import pygame

class Sprite(pygame.sprite.Sprite):
	def __init__(self, sprite: pygame.Surface, rect: Transfrom):
		super().__init__()
		self.sprite = sprite
	
	def update(self, dt:float=0):
		super().update(dt)
  