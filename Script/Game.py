import pygame
from GameConfig import *
from Script.SceneManager import SceneManager
from Script.Engine.Camera import Camera
from Script.Engine.Transfrom import Transfrom

class Game:
	_instance = None
	def __init__(self):
		if not Game._instance:
			Game._instance = self
		pygame.init()
		self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
		self.running = True
		self.camera = Camera(Transfrom(0,0,SCREEN_WIDTH, SCREEN_HEIGHT))
		self.scene_manager = SceneManager(self.camera)
		self.scene_manager.change_state(STATE.HOME)
		
	def run(self):
		while(self.running):
			self.event()
			self.update()
			self.draw()
			pygame.display.flip()

	def update(self):
		self.scene_manager.update()
			
	
	def draw(self):
		self.scene_manager.render(self.screen)
		pass

	def event(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False
			if GET_STATE() == STATE.QUIT:
				self.running = False
			self.scene_manager.event(event)