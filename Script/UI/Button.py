from Script.UI.Panel import Panel
import pygame

class Button(Panel):
	def __init__(self, position=(0,0), size=(100,50), color=(0,0,0), image=None, world_space=True, callback=None):
		super().__init__(position=position, size=size, color=color, world_space=world_space)
		self.callback = callback
		self.hovered = False
  
	def handle_event(self, event):
		if not self.visible: return
		if event.type == pygame.MOUSEBUTTONDOWN:
			mouse_pos = pygame.Vector2(event.pos)
			rect = pygame.Rect(*self.global_position(), *self.size)
			if rect.collidepoint(mouse_pos):
				if self.callback:
					self.callback()