from Script.Engine.Scene import Scene
from Script.Engine.Camera import Camera
from Script.UI.Canvas import Canvas
from Script.UI.Text import Text
from Script.UI.Button import Button
from Script.UI.Panel import Panel
from Script.Engine.Transfrom import Transfrom
from Script.Engine.ResourceManager import ResourceManager
import pygame
from GameConfig import *


class SellectRole(Scene):
	def __init__(self, camera: Camera, zoom = 1):
		super().__init__(camera, "", zoom)
		self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
		camera.followRect(self.surface.get_rect())
		self.bg = ResourceManager.load_image(HOMEBG).convert()
		self.canvas = Canvas(self.surface.get_size())
		self.drawpanel()
		print("[LOADING]: HOME SCENE")
		
	def update(self):
		pass

	def event(self, event):
		self.playBTN.handle_event(event)
		self.exitBTN.handle_event(event)
		pass
		
	def render(self, screen: pygame.Surface):
		screen.blit(self.bg, (0, 0))
		self.obj.draw(screen)
		self.canvas.draw(screen)
  
	def drawpanel(self):
		self.shion_btn()
		self.shione_btn()
  
	def shion_btn(self):
		rect = Transfrom(200, SCREEN_HEIGHT//2 - 50, 300, 100)
		def startGame():
			print("[START CONNECTION]")
			UPDATE_STATE(STATE.CONNECT)
		image = ResourceManager.load_image()
		self.playBTN = Button(rect.get_pos(), rect.get_size(), image=, (33, 35, 59), callback=startGame)
		text = Text("Play", font_fam=FONT, font_size=32, h_align="center", v_align="middle")
		self.canvas.add_child(self.playBTN)
		self.playBTN.add_child(text)
  
	def shione_btn(self):
		rect = Transfrom(200, SCREEN_HEIGHT//2 + 100, 300, 100)
		def exit():
			print("[START QUIT]")
			UPDATE_STATE(STATE.QUIT)
		self.exitBTN = Button(rect.get_pos(), rect.get_size(), (33, 35, 59), callback=exit)
		text = Text("Exit", font_fam=FONT, font_size=32, h_align="center", v_align="middle")
		self.canvas.add_child(self.exitBTN)
		self.exitBTN.add_child(text)

		