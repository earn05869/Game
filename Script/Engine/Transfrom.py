from Script.Engine.Component import Component
import pygame

class Transfrom(Component):
	def __init__(self, x: float, y: float, w: float, h: float):
		super().__init__()
		self.transfrom = pygame.Rect(x, y, w, h)

	def move(self, spd: tuple):
		self.transfrom.move_ip(spd)

	def moveX(self, spd: float):
		self.move((spd, 0))

	def moveY(self, spd: float):
		self.move((0, spd))
  
	def scale(self, size: tuple):
		self.transfrom.width = size[0]
		self.transfrom.height = size[1]
  
	def scaleX(self, w: float):
		self.transfrom.width = w
  
	def scaleY(self, h: float):
		self.transfrom.height = h
  
	def get_pos(self):
		return (self.transfrom.x, self.transfrom.y)

	def get_size(self):
		return (self.transfrom.width, self.transfrom.height)
     