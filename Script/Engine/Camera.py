from Script.Engine.Transfrom import Transfrom
import pygame

class Camera:
	_instance = None
	def __init__(self, transfrom: Transfrom):
		if not Camera._instance:
			Camera._instance = self
		self.rect = transfrom
		

	def follow(self, target: Transfrom):
		self.rect.center = target.transfrom.center
  
	def followRect(self, rect: pygame.Rect):
		self.rect.center = rect.center
  
	@staticmethod
	def get_camera():
		return Camera._instance