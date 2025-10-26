import pygame
from pytmx.util_pygame import load_pygame
from Core.GameObject import GameObject
from Core.Vector import Vector
from Core.Camera import Camera
from Core.ResourceManager import ResourceManager as Resource

class Scene:
	def __init__(self, name: str, zoom: float = 1.0, camera: Camera = None):
		self.name = name
		self.map_path = None
		self.map_data = None
		self.camera = camera
		self.zoom = zoom
		self.tile_size = 0
		self.width = 0
		self.height = 0
		self.game_objects = pygame.sprite.Group()
		self.image_layers = []
		self.object_layers = []
  
	def create_empty_scene(self, screen: pygame.Surface, color: tuple=(0,0,0)):
		self.map_surface = pygame.Surface(screen.get_size())
		self.map_surface.fill(color)
		self.image_layers = [self.map_surface]

	def render_map(self, path: str):
		self.map_data = Resource.load_tmx(path)
		self.map_path = path

		w = self.map_data.width * self.map_data.tilewidth
		h = self.map_data.height * self.map_data.tileheight

		self.map_surface = pygame.Surface((w, h), pygame.SRCALPHA)
		for layer in self.map_data.visible_layers:
			if hasattr(layer, "data"):
				for x, y, gid in layer:
					tile = self.map_data.get_tile_image_by_gid(gid)
					if tile:
						self.map_surface.blit(
							tile, (x * self.map_data.tilewidth, y * self.map_data.tileheight)
						)

		# ถ้ามีการ zoom ให้ scale surface ทั้งแผ่น
		if self.zoom != 1.0:
			new_w = int(self.map_surface.get_width() * self.zoom)
			new_h = int(self.map_surface.get_height() * self.zoom)
			self.map_surface = pygame.transform.scale(self.map_surface, (new_w, new_h))

		self.width, self.height = self.map_surface.get_size()
		self.image_layers = [self.map_surface]

		print(f"[Scene] Map loaded: {path} ({self.width}x{self.height})")

	def update(self):
		for obj in self.game_objects:
			obj.update()

	def add_game_object(self, game_object: GameObject):
		self.game_objects.add(game_object)

	def set_camera(self, camera: Camera):
		self.camera = camera

	def draw(self, screen: pygame.Surface):
		# --- Draw map ---
		if self.image_layers:
			map_surface = self.image_layers[0]
			if self.camera:
				screen.blit(
					map_surface,
					(-self.camera.rect.x, -self.camera.rect.y),
				)
			else:
				screen.blit(map_surface, (0, 0))

		# --- Draw game objects ---
		for obj in self.game_objects:
			draw_pos = obj.rect.topleft
			if self.camera:
				draw_pos = (
					obj.transform.position.x - self.camera.rect.x,
					obj.transform.position.y - self.camera.rect.y,
				)
			screen.blit(obj.sprite, draw_pos)
