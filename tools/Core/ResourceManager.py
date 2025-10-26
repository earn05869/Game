import pygame
from pytmx.util_pygame import load_pygame

class ResourceManager:
	cache = {}
	global_cache = {}  # Fixed typo in variable name

	@staticmethod
	def load_image(path: str, isglobal = False):
		"""โหลดและ cache รูปภาพ"""
		if isglobal:
			if path not in ResourceManager.global_cache:
				ResourceManager.global_cache[path] = pygame.image.load(path).convert_alpha()
			return ResourceManager.global_cache[path]
		else:
			if path not in ResourceManager.cache:
				ResourceManager.cache[path] = pygame.image.load(path).convert_alpha()
			return ResourceManager.cache[path]

	@staticmethod
	def load_sound(path: str, isglobal = False):
		"""โหลดและ cache เสียง"""
		if isglobal:
			if path not in ResourceManager.global_cache:
				ResourceManager.global_cache[path] = pygame.mixer.Sound(path)
			return ResourceManager.global_cache[path]
		else:
			if path not in ResourceManager.cache:
				ResourceManager.cache[path] = pygame.mixer.Sound(path)
			return ResourceManager.cache[path]

	@staticmethod
	def load_music(path: str):
		"""เตรียมเพลง (ไม่เก็บ cache เพราะ pygame มี global music channel)"""
		pygame.mixer.music.load(path)

	@staticmethod
	def load_font(path: str, size: int, isglobal = False):
		"""โหลดฟอนต์ตามขนาด"""
		key = f"{path}_{size}"
		if isglobal:
			if key not in ResourceManager.global_cache:
				ResourceManager.global_cache[key] = pygame.font.Font(path, size)
			return ResourceManager.global_cache[key]
		else:
			if key not in ResourceManager.cache:
				ResourceManager.cache[key] = pygame.font.Font(path, size)
			return ResourceManager.cache[key]

	@staticmethod
	def load_tmx(path: str, isglobal = False):
		"""โหลด TMX map ด้วย pytmx"""
		if isglobal:
			if path not in ResourceManager.global_cache:
				ResourceManager.global_cache[path] = load_pygame(path)
			return ResourceManager.global_cache[path]
		else:
			if path not in ResourceManager.cache:
				ResourceManager.cache[path] = load_pygame(path)
			return ResourceManager.cache[path]

	@staticmethod
	def clear(clear_global = False):
		"""ล้าง cache ทั้งหมด"""
		ResourceManager.cache.clear()
		if clear_global:
			ResourceManager.global_cache.clear()
