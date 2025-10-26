import pygame
from Core.Scene import Scene
from Core.ResourceManager import ResourceManager as Resource

class SceneManager:
	def __init__(self):
		self.current_scene: Scene | None = None

	def load_scene(self, scene: Scene):
		"""
		โหลด Scene ใหม่เข้ามาใช้งาน
		ถ้ามี Scene เก่าจะถูกแทนที่ด้วย Scene ใหม่ทันที
		"""
		if self.current_scene is not None:
			print(f"[SceneManager] Unloading scene: {self.current_scene.name}")
		Resource.clear()
		self.current_scene = scene
		print(f"[SceneManager] Loaded scene: {scene.name}")

	def update(self):
		"""
		เรียกอัปเดต Scene ปัจจุบัน (รวมถึง GameObject ทั้งหมดใน Scene)
		"""
		if self.current_scene:
			self.current_scene.update()

	def render(self, screen: pygame.Surface):
		"""
		เรียกให้ Scene ปัจจุบันวาดตัวเองลงบน screen
		"""
		if self.current_scene:
			self.current_scene.draw(screen)
