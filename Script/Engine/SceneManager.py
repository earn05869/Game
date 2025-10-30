import pygame
from Script.Engine.Scene import Scene
from Script.Engine.ResourceManager import ResourceManager

class SceneManager:
	_instance = None
	def __init__(self):
		if not SceneManager._instance:
			SceneManager._instance = self
		self.current_scene: Scene = None

	def change_scene(self, scene: Scene):	
		self.current_scene = scene
  
	def update(self):
		if self.current_scene:
			self.current_scene.update()
   
	def event(self, event):
		if self.current_scene:
			self.current_scene.event(event)

	def render(self, screen: pygame.Surface):
		if self.current_scene:
			self.current_scene.render(screen)
