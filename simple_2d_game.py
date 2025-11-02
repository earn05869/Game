"""
Pygame Top-Down Adventure Game
=====================================================
A narrative-driven adventure game with dialogue system, 
scene transitions, and visual novel elements.

Key Features:
- Component-based GameObject system (Unity-like)
- Multi-scene management with spawn points
- Typewriter dialogue with emotion colors and portraits
- 4-directional sprite animation
- Camera system with zoom
- Fade transitions between scenes
"""

import pygame
import sys
import random
import os
import math
from pytmx.util_pygame import load_pygame
from typing import List, Optional, Dict, Type, TypeVar

# ============================================================================
# GAME CONFIGURATION
# ============================================================================

class GameConfig:
	"""
	All game constants in one place for easy tuning.
	Think of this as your game's "settings panel".
	"""
	HOMEBG = "./asset/Images/homeBG.png"
	CHAR_LOGO = "./asset/Images/character.png"
	LOGO = "./asset/Images/logo.png"
	
	# ===== DISPLAY SETTINGS =====
	SCREEN_WIDTH = 1250
	SCREEN_HEIGHT = 720
	FPS = 60
	ZOOM_LEVEL = 2  # Game renders at half size, then scales up for pixel art look
	
	# ===== PLAYER SETTINGS =====
	# Two separate sizes: hitbox (collision) vs visual sprite
	PLAYER_HITBOX_SIZE = 32      # Collision detection (small, for tight gameplay)
	PLAYER_SPRITE_WIDTH = 48     # Visual representation (bigger, for clarity)
	PLAYER_SPRITE_HEIGHT = 72    
	PLAYER_COLOR = (255, 0, 0)   # Fallback color if sprites fail to load
	PLAYER_SPRITE_PATH = "asset/shion/"
	PLAYER_SPEED = 2.5
	
	# ===== UI SETTINGS =====
	DIALOG_FONT_SIZE = 32
	PROMPT_FONT_SIZE = 24
	DIALOG_FONT_PATH = "asset/font/NotoSansThaiLooped-VariableFont_wdth,wght.ttf"
	DIALOG_BG_COLOR = (0, 0, 0)
	DIALOG_BORDER_COLOR = (255, 255, 255)
	PROMPT_BG_COLOR = (0, 0, 0)
	PROMPT_TEXT_COLOR = (255, 255, 255)
	
	# ===== MAP SETTINGS =====
	START_MAP_PATH = "asset/room1/room1.tmx"
	
	# ===== NETWORK SETTINGS =====
	# SERVER_HOST can be set via environment variable TELEPORT_SERVER_HOST
	# Defaults to "localhost" for local testing
	# For network play, set it to the server's IP address (e.g., "192.168.1.100")
	SERVER_HOST = os.environ.get("TELEPORT_SERVER_HOST", "localhost")
	SERVER_PORT = 5555
	
	# ===== GAME STATES =====
	# These control what the game is currently doing
	STATE_HOME = "HOME"                 # Home screen with menu
	STATE_JOIN_INPUT = "JOIN_INPUT"     # IP input screen for Join player
	STATE_CONNECTING = "CONNECTING"     # Connecting to server
	STATE_WAITING = "WAITING"           # Waiting for other players
	STATE_PLAYING = "PLAYING"           # Normal gameplay
	STATE_DIALOGUE = "DIALOGUE"         # Dialogue box is active
	STATE_FADING_OUT = "FADING_OUT"     # Screen going black (before teleport)
	STATE_FADING_IN = "FADING_IN"       # Screen coming back (after teleport)
	STATE_END_SCREEN = "END_SCREEN"     # End credits sequence
	
	# ===== TRANSITION SETTINGS =====
	FADE_SPEED = 20  # Alpha change per frame (higher = faster fade)
	TEXT_SPEED = 30  # Milliseconds between characters (lower = faster typing)
	
	# ===== DIALOGUE COLORS =====
	# Different emotions get different text colors
	TEXT_COLOR_NEUTRAL = (255, 255, 255)   # White - default
	TEXT_COLOR_SURPRISE = (255, 255, 100)  # Light yellow
	TEXT_COLOR_ANGER = (255, 100, 100)     # Light red
	TEXT_COLOR_SADNESS = (150, 200, 255)   # Light blue
	
	# Each character can also have their own color
	CHARACTER_COLORS = {
		"Shion": (220, 190, 255),   # Light purple
		"Shione": (190, 220, 255),  # Light cyan
	}
	
	# ===== PORTRAIT SETTINGS =====
	PORTRAIT_ASSET_PATH = "asset/portrait"
	PORTRAIT_DISPLAY_WIDTH = None   # None = keep original width
	PORTRAIT_DISPLAY_HEIGHT = 720   # Scale height to this


# Type hint helper for get_component method
T = TypeVar('T')


# ============================================================================
# GAMEOBJECT & COMPONENT SYSTEM
# ============================================================================

class GameObject:
	"""
	A container for Components - similar to Unity's GameObject.
	
	Think of this as a "thing" in your game (player, wall, NPC).
	The GameObject itself doesn't do anything - it just holds Components
	that give it behavior (movement, collision, rendering, etc.)
	"""
	
	def __init__(self, scene: 'Scene', name: str):
		self.scene = scene
		self.name = name
		self._components: List['Component'] = []
		self._component_map: Dict[Type, 'Component'] = {}  # Fast lookup by type
	
	def add_component(self, component_instance: 'Component') -> 'Component':
		"""Attach a new behavior/feature to this GameObject."""
		component_instance.game_object = self  # Components need to know their parent
		self._components.append(component_instance)
		self._component_map[type(component_instance)] = component_instance
		return component_instance

	def get_component(self, component_type: Type[T]) -> Optional[T]:
		"""
		Find a specific component on this GameObject.
		Example: player.get_component(Transform) returns the Transform component.
		"""
		return self._component_map.get(component_type)
		
	def has_component(self, component_type: Type) -> bool:
		"""Quick check if this GameObject has a specific component type."""
		return component_type in self._component_map

	# ===== LIFECYCLE METHODS =====
	# These run automatically at different stages of the object's life
	
	def awake(self):
		"""Initialize all components (runs once when object is created)."""
		for component in self._components:
			component.awake()

	def start(self):
		"""Start all components (runs once after all objects are created)."""
		for component in self._components:
			component.start()

	def update(self):
		"""Update all components every frame."""
		for component in self._components:
			component.update()
			
	def draw(self, surface: pygame.Surface, camera: 'Camera'):
		"""Draw all components that have visuals."""
		for component in self._components:
			component.draw(surface, camera)


class Component:
	"""
	Base class for all components (behaviors attached to GameObjects).
	
	Each component adds ONE specific feature:
	- Transform = position/size
	- BoxCollider = collision detection
	- SpriteRenderer = shows an image
	- PlayerController = movement logic
	etc.
	"""
	
	def __init__(self):
		self.game_object: Optional[GameObject] = None
	
	@property
	def scene(self) -> 'Scene':
		"""Shortcut to access the scene from any component."""
		return self.game_object.scene

	# ===== LIFECYCLE HOOKS =====
	# Override these in child classes to add behavior at specific times
	def awake(self): pass
	def start(self): pass
	def update(self): pass
	def draw(self, surface: pygame.Surface, camera: 'Camera'): pass


# ============================================================================
# CORE COMPONENTS
# ============================================================================

class Transform(Component):
	"""
	Where is this object? How big is it?
	Every GameObject needs this to exist in the game world.
	"""
	
	def __init__(self, x: int, y: int, width: int, height: int):
		super().__init__()
		self.rect = pygame.Rect(x, y, width, height)


class BoxCollider(Component, pygame.sprite.Sprite):
	"""
	Can this object collide with things?
	
	Two types:
	- Solid (is_solid=True): Blocks movement (walls, NPCs)
	- Trigger (is_solid=False): Detects overlap but doesn't block (player, items)
	"""
	
	def __init__(self, is_solid: bool = True):
		Component.__init__(self)
		pygame.sprite.Sprite.__init__(self)  # Needed for pygame's collision groups
		self.is_solid = is_solid
		self.transform: Optional[Transform] = None
		self.rect: Optional[pygame.Rect] = None
		
	def awake(self):
		# Get the Transform component to know where we are
		self.transform = self.game_object.get_component(Transform)
		if not self.transform:
			raise TypeError(f"GameObject '{self.game_object.name}' needs Transform for BoxCollider")
		
		# Copy the transform's rect for collision detection
		self.rect = self.transform.rect.copy()
		
		# Add to collision group if this is a solid object
		if self.is_solid:
			self.scene.solid_objects.add(self)
			
	def update(self):
		# Keep collider position synced with transform
		self.rect.center = self.transform.rect.center


class SpriteRenderer(Component):
	"""
	Shows a static image for this GameObject.
	Used for non-animated objects (items, decorations).
	"""
	
	def __init__(self, image: pygame.Surface):
		super().__init__()
		self.image = image
		self.transform: Optional[Transform] = None
		
	def awake(self):
		self.transform = self.game_object.get_component(Transform)
		if not self.transform:
			raise TypeError(f"GameObject '{self.game_object.name}' needs Transform for SpriteRenderer")
			
	def draw(self, surface: pygame.Surface, camera: 'Camera'):
		# Convert world position to screen position (accounting for camera)
		screen_rect = camera.world_to_screen(self.transform.rect)
		surface.blit(self.image, screen_rect)


class SpriteAnimator(Component):
	"""
	Shows directional sprites (front/back/left/right).
	Used for NPCs and other objects that face different directions.
	
	Note: Player has custom rendering logic and doesn't use this.
	"""
	
	def __init__(self, sprite_folder_path: str, initial_direction: str = "front"):
		super().__init__()
		self.sprite_folder_path = sprite_folder_path
		self.initial_direction = initial_direction
		self.sprites: Dict[str, pygame.Surface] = {}
		self.current_sprite: Optional[pygame.Surface] = None
		self.transform: Optional[Transform] = None

	def awake(self):
		self.transform = self.game_object.get_component(Transform)
		if not self.transform:
			raise TypeError(f"GameObject '{self.game_object.name}' needs Transform for SpriteAnimator")
		
		try:
			# Load all 4 direction sprites from folder
			direction_names = ["front", "back", "left", "right"]
			for direction in direction_names:
				path = f"{self.sprite_folder_path}{direction}.png"
				img = pygame.image.load(path).convert_alpha()
				# Scale to match Transform size
				size = (self.transform.rect.width, self.transform.rect.height)
				self.sprites[direction] = pygame.transform.scale(img, size)
			
			# Set initial sprite
			self.current_sprite = self.sprites.get(
				self.initial_direction, 
				self.sprites["front"]
			)
		
		except Exception as e:
			print(f"Error loading sprites for {self.game_object.name}: {e}")
			# Fallback: create magenta square (easy to spot errors)
			error_surface = pygame.Surface(
				(self.transform.rect.width, self.transform.rect.height)
			)
			error_surface.fill((255, 0, 255))  # Magenta = "something went wrong"
			self.current_sprite = error_surface
			
	def set_direction(self, direction: str):
		"""Change which direction this sprite is facing."""
		if direction in self.sprites:
			self.current_sprite = self.sprites[direction]
		else:
			print(f"Warning: Direction '{direction}' not found for {self.game_object.name}")

	def draw(self, surface: pygame.Surface, camera: 'Camera'):
		"""Draw current sprite at world position."""
		if self.current_sprite:
			screen_rect = camera.world_to_screen(self.transform.rect)
			surface.blit(self.current_sprite, screen_rect)


# ============================================================================
# GAME-SPECIFIC COMPONENTS
# ============================================================================

class PlayerController(Component):
	"""
	Controls player movement, sprite direction, and collision response.
	
	Key Design:
	- Small hitbox (32x32) for tight collision
	- Large sprite (48x72) for visibility
	- Sprite is centered on screen, hitbox moves in world
	"""
	
	def __init__(self):
		super().__init__()
		self.transform: Optional[Transform] = None
		self.collider: Optional[BoxCollider] = None
		self.speed = GameConfig.PLAYER_SPEED
		
		# Sprite management
		self.sprites: Dict[str, pygame.Surface] = {}
		self.current_sprite: Optional[pygame.Surface] = None
		self.direction = "front"
		
		# Screen position for drawing (player stays centered)
		self.screen_rect: Optional[pygame.Rect] = None

	def awake(self):
		# Get required components
		self.transform = self.game_object.get_component(Transform)
		self.collider = self.game_object.get_component(BoxCollider)
		
		if not self.transform or not self.collider:
			raise TypeError("Player needs Transform and BoxCollider components")

		# Load player sprites
		try:
			sprite_path = GameConfig.PLAYER_SPRITE_PATH
			direction_names = ["front", "back", "left", "right"]
			
			for direction in direction_names:
				path = f"{sprite_path}{direction}.png"
				img = pygame.image.load(path).convert_alpha()
				# Scale to visual size (bigger than hitbox)
				size = (GameConfig.PLAYER_SPRITE_WIDTH, GameConfig.PLAYER_SPRITE_HEIGHT)
				self.sprites[direction] = pygame.transform.scale(img, size)
			
			self.current_sprite = self.sprites["front"]
		
		except Exception as e:
			print(f"Error loading player sprites: {e}")
			# Fallback: solid color rectangles
			fallback_size = (
				GameConfig.PLAYER_SPRITE_WIDTH,
				GameConfig.PLAYER_SPRITE_HEIGHT
			)
			fallback_image = pygame.Surface(fallback_size)
			fallback_image.fill(GameConfig.PLAYER_COLOR)
			self.sprites = {key: fallback_image for key in ["front", "back", "left", "right"]}
			self.current_sprite = fallback_image
		
		# Calculate screen position (player sprite stays centered on screen)
		screen_size = (
			GameConfig.SCREEN_WIDTH // GameConfig.ZOOM_LEVEL,
			GameConfig.SCREEN_HEIGHT // GameConfig.ZOOM_LEVEL
		)
		
		screen_center_x = screen_size[0] // 2
		screen_center_y = screen_size[1] // 2
		
		self.screen_rect = self.current_sprite.get_rect()
		
		# Center sprite horizontally
		self.screen_rect.centerx = screen_center_x
		
		# Align sprite's bottom with hitbox's bottom
		# This makes it look like the character is "standing" on the hitbox
		self.screen_rect.bottom = screen_center_y + (GameConfig.PLAYER_HITBOX_SIZE // 2)

	def update(self):
		# Don't move during dialogue or transitions
		if self.scene.game.state != GameConfig.STATE_PLAYING:
			return
			
		# ===== INPUT HANDLING =====
		# Check player role - only host (shion) can use input directly
		# Join player (shione) uses position from host directly
		game = self.scene.game
		player_role = getattr(game, 'player_role', None)
		
		dx, dy = 0, 0
		
		# Only host (shion) can use keyboard input directly
		if player_role == 'shion':
			# Host player - use actual keyboard input
			keys = pygame.key.get_pressed()
			
			# Vertical movement
			if keys[pygame.K_w]:
				dy = -self.speed
				self.direction = "back"
			elif keys[pygame.K_s]:
				dy = self.speed
				self.direction = "front"
			
			# Horizontal movement
			if keys[pygame.K_a]:
				dx = -self.speed
				self.direction = "left"
			elif keys[pygame.K_d]:
				dx = self.speed
				self.direction = "right"
		
		# Join player (shione) - Use position from host directly
		elif player_role == 'shione' and game.network:
			# Get host position directly
			host_pos = game.other_player_pos
			current_pos = (self.transform.rect.centerx, self.transform.rect.centery)
			target_pos = (host_pos.get('x', current_pos[0]), host_pos.get('y', current_pos[1]))
			
			# Calculate direction based on position difference
			pos_diff_x = target_pos[0] - current_pos[0]
			pos_diff_y = target_pos[1] - current_pos[1]
			
			# Move towards host position
			if abs(pos_diff_x) > 1 or abs(pos_diff_y) > 1:
				# Calculate movement direction
				if abs(pos_diff_x) > abs(pos_diff_y):
					# Horizontal movement
					if pos_diff_x > 0:
						dx = min(self.speed, abs(pos_diff_x))
						self.direction = "right"
					else:
						dx = -min(self.speed, abs(pos_diff_x))
						self.direction = "left"
				else:
					# Vertical movement
					if pos_diff_y > 0:
						dy = min(self.speed, abs(pos_diff_y))
						self.direction = "front"
					else:
						dy = -min(self.speed, abs(pos_diff_y))
						self.direction = "back"
			else:
				# Close enough, snap to position
				self.transform.rect.centerx = target_pos[0]
				self.transform.rect.centery = target_pos[1]
				dx, dy = 0, 0

			# Force direction to match host direction exactly when provided
			host_dir = getattr(game, 'other_player_dir', None)
			if host_dir in ("front", "back", "left", "right"):
				self.direction = host_dir
		
		# If role is not set or network not available, no movement
		else:
			# No input - player cannot move
			pass
			
		# Update sprite to match direction
		self.current_sprite = self.sprites[self.direction]

		# ===== COLLISION HANDLING =====
		# We handle X and Y separately for smooth wall sliding
		
		# Move horizontally
		if dx != 0:
			self.transform.rect.x += dx
			self.collider.rect.centerx = self.transform.rect.centerx
			
			# Check collision with all solid objects
			for solid in self.scene.solid_objects:
				if self.collider.rect.colliderect(solid.rect):
					if dx > 0:  # Moving right → hit wall on right
						self.transform.rect.right = solid.rect.left
					if dx < 0:  # Moving left → hit wall on left
						self.transform.rect.left = solid.rect.right
					# Update collider after correction
					self.collider.rect.centerx = self.transform.rect.centerx

		# Move vertically
		if dy != 0:
			self.transform.rect.y += dy
			self.collider.rect.centery = self.transform.rect.centery
			
			# Check collision
			for solid in self.scene.solid_objects:
				if self.collider.rect.colliderect(solid.rect):
					if dy > 0:  # Moving down → hit wall below
						self.transform.rect.bottom = solid.rect.top
					if dy < 0:  # Moving up → hit wall above
						self.transform.rect.top = solid.rect.bottom
					# Update collider after correction
					self.collider.rect.centery = self.transform.rect.centery

	def draw(self, surface: pygame.Surface, camera: 'Camera'):
		"""
		Draw player sprite at fixed screen position.
		(Camera moves world around player, not player around screen)
		"""
		if self.current_sprite:
			surface.blit(self.current_sprite, self.screen_rect)


class Interactable(Component, pygame.sprite.Sprite):
	"""
	Generic interactable object (books, NPCs, items).
	When player presses E nearby, triggers dialogue based on object's name.
	"""
	
	def __init__(self, name: str):
		Component.__init__(self)
		pygame.sprite.Sprite.__init__(self)
		self.name = name
		self.rect: Optional[pygame.Rect] = None

	def awake(self):
		self.transform = self.game_object.get_component(Transform)
		if not self.transform:
			raise TypeError(f"GameObject '{self.game_object.name}' needs Transform for Interactable")
		
		self.rect = self.transform.rect.copy()
		self.scene.interactables.add(self)


class Teleport(Component, pygame.sprite.Sprite):
	"""
	Teleports player to a different map when interacted with.
	Used for doors between rooms, ladders, etc.
	"""
	
	def __init__(self, target_map: str, target_spawn_point: str):
		Component.__init__(self)
		pygame.sprite.Sprite.__init__(self)
		
		self.target_map = target_map  # Path to TMX file
		self.target_spawn_point = target_spawn_point  # Name of spawn point in that map
		
		self.rect: Optional[pygame.Rect] = None

	def awake(self):
		self.transform = self.game_object.get_component(Transform)
		if not self.transform:
			raise TypeError(f"GameObject '{self.game_object.name}' needs Transform for Teleport")
		
		self.rect = self.transform.rect.copy()
		self.scene.interactables.add(self)


# ============================================================================
# SCENE MANAGEMENT
# ============================================================================

class Scene:
	"""
	A game level/room - loads map, creates objects, manages collisions.
	Think of this as one "room" or "area" in your game.
	"""
	
	def __init__(self, game: 'Game', map_path: str):
		self.game = game
		self.map_path = map_path
		
		# Load and render the map
		self.tmx_data = self._load_map()
		self.map_surface = self._render_map()
		
		# Object management
		self.game_objects: List[GameObject] = []
		self.solid_objects = pygame.sprite.Group()  # Things you can't walk through
		self.interactables = pygame.sprite.Group()  # Things you can press E on
		
		# Track polygons (for yellow room track system)
		self.track_polygons: List[List[tuple]] = []
		
		# Scene loading state - track when scene is fully ready
		self.is_fully_loaded = False
		
		# Create all objects from the map file
		self._create_objects_from_map()
		
		# Verify scene is fully loaded
		self._verify_loading_complete()
	
	def add_game_object(self, game_object: GameObject):
		"""Add a new object to this scene."""
		self.game_objects.append(game_object)
		game_object.awake()
		return game_object

	def start(self):
		"""Initialize all objects in scene."""
		for go in self.game_objects:
			go.start()
			
	def update(self):
		"""Update all objects every frame."""
		for go in self.game_objects:
			go.update()

	def draw(self, surface: pygame.Surface, camera: 'Camera'):
		"""Draw map background, then all objects."""
		# Draw map tiles (camera offset moves the world)
		surface.blit(self.map_surface, (-camera.rect.x, -camera.rect.y))
		
		# Draw all game objects
		for go in self.game_objects:
			go.draw(surface, camera)

	def find_spawn_point(self, spawn_name: str) -> tuple:
		"""
		Find a spawn point object in the map by name.
		Returns (x, y) position, or (0, 0) if not found.
		
		Spawn points are defined in Tiled editor's "entry_point" layer.
		"""
		try:
			entry_layer = self.tmx_data.get_layer_by_name("entry_point")
			for obj in entry_layer:
				if obj.name == spawn_name:
					print(f"Found spawn point '{spawn_name}' at ({obj.x}, {obj.y})")
					return (obj.x, obj.y)
		except ValueError:
			print(f"Warning: 'entry_point' layer not found in {self.map_path}")
		
		# Fallback if spawn point not found
		print(f"Warning: Spawn point '{spawn_name}' not found. Using (0, 0)")
		return (0, 0)

	def _load_map(self):
		"""Load TMX map file created in Tiled editor."""
		try:
			return load_pygame(self.map_path)
		except FileNotFoundError:
			print(f"Error: Map file not found: {self.map_path}")
			pygame.quit()
			sys.exit()
	
	def _render_map(self) -> pygame.Surface:
		"""Convert TMX tile layers into a single surface for fast rendering."""
		map_width = self.tmx_data.width * self.tmx_data.tilewidth
		map_height = self.tmx_data.height * self.tmx_data.tileheight
		surface = pygame.Surface((map_width, map_height), pygame.SRCALPHA)
		surface.fill((20, 10, 30))  # White background
		
		# Draw all visible tile layers
		for layer in self.tmx_data.visible_layers:
			if hasattr(layer, 'data'):  # It's a tile layer
				for x, y, gid in layer:
					tile = self.tmx_data.get_tile_image_by_gid(gid)
					if tile:
						surface.blit(
							tile,
							(x * self.tmx_data.tilewidth, y * self.tmx_data.tileheight)
						)
		return surface
	
	def _create_objects_from_map(self) -> None:
		"""
		Read Tiled object layers and create GameObjects with appropriate components.
		Each layer type creates different kinds of objects.
		"""
		
		# ===== COLLISION LAYER =====
		# These are invisible walls
		try:
			for obj in self.tmx_data.get_layer_by_name("collision"):
				go = GameObject(self, name=f"Wall_{obj.id}")
				go.add_component(Transform(obj.x, obj.y, obj.width, obj.height))
				go.add_component(BoxCollider(is_solid=True))
				self.add_game_object(go)
		except ValueError:
			print("Warning: 'collision' layer not found in map")
		
		# (Door layer removed)
		
		# ===== INTERACT LAYER =====
		# Objects you can press E on (NPCs, items, etc.)
		try:
			for obj in self.tmx_data.get_layer_by_name("interact"):
				go = GameObject(self, name=obj.name)
				go.add_component(Transform(obj.x, obj.y, obj.width, obj.height))
				go.add_component(Interactable(name=obj.name))

				# Check if this object has a sprite
				sprite_folder = obj.properties.get('sprite_folder')
				sprite_image_path = obj.properties.get('sprite_image')
				
				if sprite_folder:
					# This is an NPC (has 4-directional sprites)
					go.add_component(BoxCollider(is_solid=True))  # NPCs are solid
					initial_dir = obj.properties.get('initial_direction', 'front')
					go.add_component(SpriteAnimator(sprite_folder, initial_dir))
				
				elif sprite_image_path:
					# This is a static object (single image)
					try:
						image = pygame.image.load(sprite_image_path).convert_alpha()
						size = (obj.width, obj.height)
						image = pygame.transform.scale(image, size)
						go.add_component(SpriteRenderer(image))
					except Exception as e:
						print(f"Error loading static sprite {sprite_image_path}: {e}")
				
				# If no sprite properties, object is invisible (collision-only)
				self.add_game_object(go)
				
		except ValueError:
			print("Warning: 'interact' layer not found in map")

		# ===== TELEPORT LAYER =====
		# Doors to other scenes
		try:
			for obj in self.tmx_data.get_layer_by_name("teleport"):
				go = GameObject(self, name=obj.name or f"Teleport_{obj.id}")
				go.add_component(Transform(obj.x, obj.y, obj.width, obj.height))
				
				# Read target map and spawn point from Tiled properties
				target_map = obj.properties.get('target_map')
				target_spawn = obj.properties.get('target_spawn_point')

				if not target_map or not target_spawn:
					print(f"Warning: Teleport {obj.id} missing required properties")
					continue
					
				go.add_component(Teleport(target_map, target_spawn))
				self.add_game_object(go)
		except ValueError:
			print("Warning: 'teleport' layer not found in map")
		
		# ===== TRACK LAYER =====
		# Safe paths the player must follow (e.g., yellow room track)
		try:
			for obj in self.tmx_data.get_layer_by_name("track"):
				if hasattr(obj, 'polygon'):  # Polygon object
					# Get polygon points relative to object position
					base_x = obj.x
					base_y = obj.y
					polygon_points = []
					for point in obj.polygon:
						# Polygon points are relative to the object's position
						polygon_points.append((base_x + point.x, base_y + point.y))
					# Expand polygon by 5 pixels
					polygon_points = self._expand_polygon(polygon_points, 5.0)
					self.track_polygons.append(polygon_points)
					print(f"Loaded track polygon with {len(polygon_points)} points (expanded by 5px)")
				elif hasattr(obj, 'width') and hasattr(obj, 'height'):  # Rectangle object
					# Convert rectangle to polygon (4 corners)
					polygon_points = [
						(obj.x, obj.y),
						(obj.x + obj.width, obj.y),
						(obj.x + obj.width, obj.y + obj.height),
						(obj.x, obj.y + obj.height)
					]
					# Expand polygon by 5 pixels
					polygon_points = self._expand_polygon(polygon_points, 5.0)
					self.track_polygons.append(polygon_points)
					print(f"Loaded track rectangle (expanded by 5px)")
		except ValueError:
			# No track layer - that's fine, not all maps have tracks
			pass
	
	def _expand_polygon(self, polygon: List[tuple], offset: float) -> List[tuple]:
		"""
		Expand a polygon outward by the specified offset distance.
		Returns a new list of polygon points.
		"""
		if len(polygon) < 3:
			return polygon
		
		import math
		expanded = []
		n = len(polygon)
		
		for i in range(n):
			# Get current, previous, and next points
			prev_idx = (i - 1) % n
			curr_idx = i
			next_idx = (i + 1) % n
			
			px, py = polygon[prev_idx]
			cx, cy = polygon[curr_idx]
			nx, ny = polygon[next_idx]
			
			# Calculate vectors from current to previous and next
			dx1 = cx - px
			dy1 = cy - py
			dx2 = nx - cx
			dy2 = ny - cy
			
			# Normalize vectors
			len1 = math.sqrt(dx1*dx1 + dy1*dy1)
			len2 = math.sqrt(dx2*dx2 + dy2*dy2)
			
			if len1 > 0:
				dx1 /= len1
				dy1 /= len1
			if len2 > 0:
				dx2 /= len2
				dy2 /= len2
			
			# Calculate perpendicular vectors (pointing outward)
			# Rotate 90 degrees counter-clockwise
			perp1_x = -dy1
			perp1_y = dx1
			perp2_x = -dy2
			perp2_y = dx2
			
			# Average the two perpendicular vectors to get the offset direction
			avg_x = (perp1_x + perp2_x) / 2.0
			avg_y = (perp1_y + perp2_y) / 2.0
			
			# Normalize the average vector
			avg_len = math.sqrt(avg_x*avg_x + avg_y*avg_y)
			if avg_len > 0:
				avg_x /= avg_len
				avg_y /= avg_len
			
			# Apply offset
			new_x = cx + avg_x * offset
			new_y = cy + avg_y * offset
			expanded.append((new_x, new_y))
		
		return expanded
	
	def _verify_loading_complete(self) -> None:
		"""
		Verify that the scene is fully loaded and ready for gameplay.
		This ensures all critical systems (like track polygons) are loaded.
		"""
		# Verify map data exists
		if not self.tmx_data:
			raise RuntimeError(f"Failed to load map data for {self.map_path}")
		
		# Verify map surface exists
		if not self.map_surface:
			raise RuntimeError(f"Failed to render map surface for {self.map_path}")
		
		# For yellow room, verify track polygons are loaded
		if "yellow" in self.map_path.lower():
			if not self.track_polygons:
				print(f"Warning: Yellow room {self.map_path} has no track polygons loaded!")
			else:
				print(f"[SCENE] Yellow room track system loaded: {len(self.track_polygons)} track polygons")
		
		# Mark scene as fully loaded
		self.is_fully_loaded = True
		print(f"[SCENE] Scene fully loaded and verified: {self.map_path}")
	
	def is_spawn_on_track(self, spawn_x: float, spawn_y: float) -> bool:
		"""
		Check if a spawn point is on a valid track (for yellow room).
		Returns True if on track or if map doesn't require tracks.
		"""
		# Only check tracks for yellow room
		if "yellow" not in self.map_path.lower():
			return True  # Other rooms don't require track checking
		
		# If no track polygons, warn but allow spawn (shouldn't happen if map is correct)
		if not self.track_polygons:
			print(f"Warning: Yellow room has no track polygons! Spawn may be invalid.")
			return True  # Allow spawn to prevent breaking game
		
		# Check if spawn point is inside any track polygon
		for polygon in self.track_polygons:
			if self._point_in_polygon(spawn_x, spawn_y, polygon):
				return True
		
		return False
	
	def _point_in_polygon(self, x: float, y: float, polygon: List[tuple]) -> bool:
		"""
		Check if a point (x, y) is inside a polygon using ray casting algorithm.
		Returns True if point is inside the polygon, False otherwise.
		"""
		n = len(polygon)
		inside = False
		
		if n < 3:
			return False  # Not a valid polygon
		
		p1x, p1y = polygon[0]
		for i in range(1, n + 1):
			p2x, p2y = polygon[i % n]
			if y > min(p1y, p2y):
				if y <= max(p1y, p2y):
					if x <= max(p1x, p2x):
						if p1y != p2y:
							xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
						else:
							xinters = p1x
						if p1x == p2x or x <= xinters:
							inside = not inside
			p1x, p1y = p2x, p2y
		
		return inside

	def create_player(self, x: int, y: int) -> GameObject:
		"""
		Factory method to create the player GameObject at a specific position.
		x, y should be the CENTER position where the player should spawn.
		Transform uses top-left, so we convert center to top-left.
		"""
		player_go = GameObject(self, name="Player")
		# Convert center position (x, y) to top-left for Transform
		# Transform expects top-left corner, but spawn points are center positions
		hitbox_size = GameConfig.PLAYER_HITBOX_SIZE
		top_left_x = x - (hitbox_size // 2)
		top_left_y = y - (hitbox_size // 2)
		
		player_go.add_component(Transform(
			top_left_x, top_left_y,
			hitbox_size,
			hitbox_size
		))
		# Verify the center matches the spawn point
		transform = player_go.get_component(Transform)
		if transform and transform.rect:
			actual_center_x = transform.rect.centerx
			actual_center_y = transform.rect.centery
			# Allow small floating point differences
			if abs(actual_center_x - x) > 1 or abs(actual_center_y - y) > 1:
				print(f"[SCENE] WARNING: Player center mismatch! Expected ({x}, {y}), got ({actual_center_x}, {actual_center_y})")
				# Force correct center position
				transform.rect.centerx = x
				transform.rect.centery = y
		
		player_go.add_component(BoxCollider(is_solid=False))  # Player is a trigger
		player_go.add_component(PlayerController())
		self.add_game_object(player_go)
		return player_go


# ============================================================================
# CAMERA SYSTEM
# ============================================================================

class Camera:
	"""
	Controls what part of the world is visible on screen.
	Follows the player smoothly through the world.
	"""
	
	def __init__(self, width: int, height: int):
		self.rect = pygame.Rect(0, 0, width, height)
	
	def update(self, target_center: tuple) -> None:
		"""Center camera on target position (usually the player)."""
		self.rect.center = target_center
	
	def world_to_screen(self, world_rect: pygame.Rect) -> pygame.Rect:
		"""Convert world coordinates to screen coordinates for rendering."""
		return world_rect.move(-self.rect.x, -self.rect.y)


# ============================================================================
# DIALOGUE SYSTEM
# ============================================================================

class DialogueChoice:
	"""
	Represents a single choice option in a choice dialog.
	
	Parameters:
	- text: The choice text displayed to the player
	- event: Optional event string to trigger when this choice is selected
	- goto_script: Optional script ID to jump to after selecting this choice
	- goto_line: Optional line index in goto_script to jump to (None = start of script)
	"""
	def __init__(
		self,
		text: str,
		event: Optional[str] = None,
		goto_script: Optional[str] = None,
		goto_line: Optional[int] = None
	):
		self.text = text
		self.event = event
		self.goto_script = goto_script
		self.goto_line = goto_line


class DialogueLine:
	"""
	One line of dialogue with all its metadata.
	
	Parameters:
	- speaker: Character name (None for narration)
	- text: The actual dialogue text
	- event: Optional event to trigger after this line
	- emotion: Changes text color (neutral/surprise/anger/sadness)
	- instant_shake: If True, text appears instantly and shakes
	- portrait_key: Filename (without extension) for character portrait
	- choices: Optional list of DialogueChoice objects for player choice
	"""
	
	def __init__(
		self, 
		speaker: Optional[str], 
		text: str, 
		event: Optional[str] = None, 
		emotion: str = "neutral", 
		instant_shake: bool = False, 
		portrait_key: Optional[str] = None,
		choices: Optional[List['DialogueChoice']] = None
	):
		# Remove trailing '!' if instant_shake is True (we'll add shake effect instead)
		self.speaker = speaker
		self.text = text.rstrip('!') if instant_shake else text
		self.event = event
		self.emotion = emotion
		self.instant_shake = instant_shake
		self.portrait_key = portrait_key  # e.g., "shion_neutral" or "shione_anger"
		self.choices = choices  # List of DialogueChoice objects, None means regular dialogue line


class DialogSystem:
	"""
	Manages dialogue with typewriter effect, emotions, portraits, and screen shake.
	
	Key Features:
	- Typewriter: Text appears character-by-character
	- Emotions: Different text colors based on mood
	- Portraits: Full-screen character images during dialogue
	- Shake: Text shakes for dramatic moments
	- Events: Trigger gameplay events from dialogue
	"""
	
	def __init__(self, game: 'Game'):
		self.game = game
		
		# ===== FONT SETUP =====
		DIALOG_FONT_PATH = GameConfig.DIALOG_FONT_PATH
		try:
			self.speaker_font = pygame.font.Font(
				DIALOG_FONT_PATH, 
				GameConfig.PROMPT_FONT_SIZE + 4
			)
			self.text_font = pygame.font.Font(
				DIALOG_FONT_PATH, 
				GameConfig.DIALOG_FONT_SIZE
			)
			print(f"Successfully loaded font: {DIALOG_FONT_PATH}")
		except Exception as e:
			print(f"Font loading error: {e}")
			# Fallback to default font
			self.speaker_font = pygame.font.Font(None, GameConfig.PROMPT_FONT_SIZE + 4)
			self.text_font = pygame.font.Font(None, GameConfig.DIALOG_FONT_SIZE)

		self.box_padding = 20
		self.line_spacing = 5
		self.prompt_text = self.speaker_font.render(
			"[E]", 
			True, 
			GameConfig.TEXT_COLOR_NEUTRAL
		)

		# ===== DIALOGUE SCRIPTS =====
		# Each script is a sequence of DialogueLines
		# Script ID matches the Interactable object's name
		self.scripts: Dict[str, List[DialogueLine]] = {
		 "intro room1": [
			DialogueLine(None, "ตื่นขึ้นมาอีกครั้งในห้องที่เธอไม่รู้จัก — ผนังขาวสะอาดเหมือนกระดาษเปล่า ไม่มีเสียงนาฬิกา ไม่มีหน้าต่าง มีเพียงเสียงเครื่องช่วยหายใจแผ่วเบา"),
			DialogueLine(None, "เธอรู้ทันที… นี่ไม่ใช่โลกของเธอ แต่ก็ไม่ใช่โลกของเกมนั้นด้วย"),
			DialogueLine("Shione", "เฮ้… ชิอน ได้ยินฉันไหม?", emotion="surprise", instant_shake=True, portrait_key="shione_neutral"), # <-- ใช้ key
			DialogueLine("Shion", "ใคร…? ฉันอยู่ที่ไหน... นี่คือเกมอีกใช่ไหม?", emotion="surprise", instant_shake=True, portrait_key="shion_neutral"), # <-- ใช้ key
			DialogueLine("Shione", "ไม่ใช่เกมนะ เธออยู่ในโรงพยาบาล ฉันชิโอเนะ จำได้ไหม?", portrait_key="shione_neutral"),
			DialogueLine("Shion", "โรงพยาบาล... จิตเวท?", emotion="sadness", portrait_key="shion_neutral"),
			DialogueLine("Shion", "(เสียงหัวเราะแผ่วแต่สั่น) งั้นเธอก็เป็น NPC เหมือนเดิมสินะ...", emotion="sadness", portrait_key="shion_neutral"),
			DialogueLine("Shione", "ไม่ใช่ NPC! ฉันเป็นคนจริง ๆ... ฉันพยายามจะช่วยเธออยู่นะ", emotion="anger", instant_shake=True, portrait_key="shione_neutral"), # <-- ใช้ key
			DialogueLine("Shion", "(เสียงเริ่มสั่น) เธอพูดแบบนี้อีกแล้ว... สุดท้ายฉันก็ต้อง ‘รีเซ็ต’ ใหม่อีก...", emotion="sadness", portrait_key="shion_neutral"),
			DialogueLine("Shione", "ถ้าเธอยังคิดว่าที่นี่คือเกม เธอจะไม่มีวันออกไปได้หรอกนะ", portrait_key="shione_neutral"),
			DialogueLine("Shion", "(พูดเบา ๆ) ไม่จริงหรอก มันเป็นเกมมาโดยตลอดและทั้งเธอแล้วก็ฉันก็ไม่ต่างกัน เป็นแค่ ตัวละคร", portrait_key="shion_neutral"),
			DialogueLine("Shione", "เราต้องหาทางออกจากที่นี่… ดูเหมือนที่นี่จะเป็นtutorial", portrait_key="shione_neutral"),
			DialogueLine("Shion", "ฉันมองไม่เห็น... ทุกอย่างมืดไปหมด", portrait_key="shion_neutral"), #<-- ควรมีรูป shion_sadness ไหม?
			DialogueLine("Shione", "ไม่เป็นไร ฉันจะเป็นตาให้เธอเอง เธอลองพยายามเดินไปสำรวจหนังสือในห้องก่อนนะ", portrait_key="shione_neutral"),
			DialogueLine("Shion", "มันอยู่ที่ไหนล่ะ", portrait_key="shion_neutral"),
		],
		"book1": [
			DialogueLine(None, "กลิ่นหอมบางของดอกไม้ปลิวออกมาจากหน้าหนังสือ — เหมือนลมหายใจของฤดูใบไม้ผลิที่แอบหลงเข้ามาในห้องสีขาว"),
			DialogueLine("Shion", "กลิ่นนี่... เหมือนแดนดิไลออน...", emotion="surprise", portrait_key="shion_neutral"), #<-- ควรมีรูป shion_surprise ไหม?
			DialogueLine("Shione", "(ยิ้มบาง ๆ) ใช่แล้ว มันคือดอกไม้แห่งความหวัง ฟังฉันอ่านเถอะ", portrait_key="shione_neutral"), #<-- ควรมีรูป shione_smile ไหม?
			DialogueLine("Shione", "“แดนดิไลออน... ดอกไม้ที่ไม่เคยร้องไห้ แม้ลมจะพัดแรงเพียงใด มันก็ยังเต้นรำอย่างอ่อนโยน”", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“เมื่อกลีบสีทองลอยขึ้นสู่ท้องฟ้า มันมิได้จากไป แต่มันกำลังเดินทางกลับบ้าน”", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“ผู้ที่หลับใหลในความมืด หากยังได้กลิ่นของแดนดิไลออน จงรู้ไว้เถิด — แสงแห่งความหวังยังไม่ดับสูญ”", portrait_key="shione_neutral"),
			DialogueLine("Shion", "(พึมพำ) ...กลับบ้านเหรอ?", emotion="sadness", portrait_key="shion_neutral"), #<-- shion_sadness?
			DialogueLine("Shione", "ใช่ มันหมายถึงเธอ... ที่ยังหาทางกลับไปหา ‘ตัวตนจริง ๆ’ ของตัวเองอยู่", portrait_key="shione_neutral"),
			DialogueLine("Shion", "แต่บ้านของฉันไม่มีแล้ว... ทุกอย่างถูกรีเซ็ตหมด...", emotion="sadness", portrait_key="shion_neutral"), #<-- shion_sadness?
			DialogueLine("Shione", "บ้านไม่ได้อยู่ในที่นั้นหรอก มันอยู่ตรงหัวใจที่ยังมีแสงสีเหลืองแบบนี้ต่างหาก", portrait_key="shione_neutral"),
			DialogueLine(None, "ทันใดนั้น กลีบดอกไม้สีเหลืองลอยออกมาจากหน้ากระดาษ มันลอยวนรอบตัวชิอนเหมือนฝุ่นละอองของความทรงจำ — อ่อนโยนแต่จริงแท้", event="play_dandelion_effect"),
			DialogueLine("Shion", "ฉันจำได้แล้ว... ตอนนั้นฉันแล้วอธิษฐานให้โลกหยุดหมุน...", emotion="surprise", portrait_key="shion_neutral"), #<-- shion_surprise?
			DialogueLine("Shione", "แล้วตอนนี้เธอก็ทำได้อีกครั้ง...โลกหยุดเพื่อให้เธอเริ่มใหม่ได้แล้วนะ", portrait_key="shione_neutral"),
			DialogueLine(None, "แสงสีเหลืองทองแผ่กระจายรอบห้อง ผนังขาวค่อย ๆ ละลายกลายเป็นทุ่งดอกไม้ไม่มีที่สิ้นสุด ลมอุ่นพัดเบา ๆ พร้อมเสียงหัวใจของชิอนที่เต้นชัดขึ้น — ครั้งแรกในรอบหลายปี"),
			DialogueLine("Shion", "(ยื่นมือออกไปข้างหน้า) ฉัน... มองเห็นมัน... แม้ว่าฉันยังหลับตาอยู่", emotion="surprise", portrait_key="shion_neutral"), #<-- shion_surprise?
			DialogueLine("Shione", "(ยิ้ม) นั่นเพราะเธอกำลังมองด้วยหัวใจแล้วล่ะ", portrait_key="shione_neutral"), #<-- shione_smile?
			DialogueLine(None, "และในวินาทีนั้น หนังสือในมือของชิโอเนะส่องแสงสีเหลืองแรงขึ้น — แปรเปลี่ยนเป็นประตูสู่ “ทุ่งแดนดิไลออนแห่งความทรงจำ” ที่รออยู่เบื้องหน้า..."),
		],
		"book2": [
			DialogueLine("Shion", "เล่มนี้เหมือนจะเปิดอยู่แล้วนะ", emotion="surprise", portrait_key="shion_neutral"), #<-- shion_surprise?
			DialogueLine("Shione", "ใช่มันเปิดอยู่", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“ทางเดินหินสีแดง คือเส้นทางที่ต้องเดินผ่านความเจ็บปวดของตัวเอง”", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“ทุกก้าวเต็มไปด้วยความโศกเศส้าและความกล้า ทุกหยดน้ำตาเป็นรากฐานของความเข้มแข็ง”", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“เจ้าจะต้องปิดกั้นอารมณ์ ฝืนยิ้มหรือเก็บน้ำตา เพราะนั่นคือสิ่งที่ทำให้เจ้าเป็นตัวเองอย่างแท้จริง”", portrait_key="shione_neutral"),
			DialogueLine("Shion", "(น้ำเสียงสั่น, น้ำตาไหล) ฉัน… ฉันไม่อยากฝืนอีกแล้ว… ฉันไม่อยากปิดกั้นความรู้สึก… ฉัน… ฉันยังไม่พร้อม…", emotion="sadness", portrait_key="shion_neutral"), #<-- shion_sadness?
			DialogueLine("Shione", "ชิอน… ฉันเข้าใจความรู้สึกของเธอ แต่ฉันเห็นด้วยกับมันนะ ถ้าเรายังยึดอารมณ์อยู่ เราก้าวต่อไปไม่ได้", emotion="neutral", portrait_key="shione_neutral"),
			DialogueLine("Shion", "(ตะโกน, โกรธและเศร้า) เธอหมายความว่าถ้าเธอต้องทิ้งฉัน เพื่อก้าวต่อ เธอก็จะทำหรอ!", emotion="anger", instant_shake=True, portrait_key="shion_neutral"),#<-- shion_anger?
			DialogueLine("Shione", "(เสียงแน่น, สายตาแข็ง) ฉันไม่อยากทิ้งเธอ… แต่ถ้ามันเพื่อความอยู่รอดของตัวเอง ฉันต้องการสติและความเข้มแข็ง ฉันไม่สามารถเดินไปพร้อมกับคนที่ยังจมอยู่กับความเศร้าได้", emotion="anger", portrait_key="shione_neutral"), #<-- shione_anger?
			DialogueLine("Shion", "(น้ำตาร่วง, สะอื้น) เธอพูดบ้าอะไรอยู่น่ะ เธอเป็นแค่ NPC นะ", emotion="anger", portrait_key="shion_neutral"), #<-- shion_sadness/anger?
			DialogueLine("Shione", "พอเถอะ ฉันไม่คุยเรื่องนี้แล้ว เธอคงเข้าใจ วิธีการขยับแล้วสินะ ไปกันต่อเถอะ", event="trigger_bed_tutorial", portrait_key="shione_neutral"),
		],
		"book3": [
			DialogueLine(None, "เสียงเปิดหนังสือดังขึ้นอีกครั้ง คราวนี้ ไม่มีกลิ่นดอกไม้... มีเพียงความเย็นของลมที่พัดผ่านหัวใจ"),
			DialogueLine("Shione", "ชิอน... เธอพร้อมไหม?", portrait_key="shione_neutral"),
			DialogueLine("Shion", "เสียงของลม... เหมือนมันเรียกฉันอยู่", portrait_key="shion_neutral"),
			DialogueLine("Shione", "อย่าตามเสียงนั้นไปนะ มันไม่ใช่ของจริง", emotion="anger", portrait_key="shione_neutral"), #<-- shione_anger?
			DialogueLine("Shion", "แต่... มันฟังดูเหมือนฉันเองในอีกที่หนึ่ง", portrait_key="shion_neutral"),
			DialogueLine(None, "เมื่อหน้าหนังสือเปิดออก ท้องฟ้าสีฟ้าเข้มแผ่กระจายเต็มห้อง ผนังขาวค่อย ๆ จางไป เหลือเพียงขอบฟ้าที่ไร้จุดสิ้นสุด"),
			DialogueLine("Shione", "“ใต้ท้องฟ้าที่ไม่มีที่สิ้นสุด ทุกเสียงล้วนถูกรับฟังโดยดวงตาที่มองไม่เห็น”", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“ที่นี่... ไม่มีความเจ็บปวด ไม่มีการลืม มีเพียงการเริ่มต้นซ้ำแล้วซ้ำเล่า จนกว่าความเศร้าจะหายไป”", portrait_key="shione_neutral"),
			DialogueLine("Shione", "“จงยกมือขึ้นสู่ท้องฟ้า — แล้วเจ้าจะหลุดพ้นจากความจริง เพราะบนนี้... ทุกสิ่งคืออิสระ”", portrait_key="shione_neutral"),
			DialogueLine("Shion", "ไม่มีความเจ็บปวด... ไม่มีการลืม...", emotion="surprise", portrait_key="shion_neutral"), #<-- shion_surprise?
			DialogueLine("Shione", "ชิอน อย่าเชื่อมัน นั่นมันดีเกินจริงไปไม่ใช่หรอ", emotion="anger", portrait_key="shione_neutral"), #<-- shione_anger?
			DialogueLine("Shion", "แต่มันอบอุ่นมาก... มันบอกว่าจะไม่ให้ฉันต้องตื่นอีกต่อไป...", emotion="sadness", portrait_key="shion_neutral"), #<-- shion_sadness?
			DialogueLine("Shione", "(เสียงเริ่มเข้ม) นั่นไม่ใช่อ้อมกอด มันคือกรงที่เธอมองไม่เห็นต่างหาก", emotion="anger", portrait_key="shione_neutral"), #<-- shione_anger?
			DialogueLine(None, "เสียงหัวเราะแผ่วเบาดังมาจากบนฟ้า — เสียงเดียวกับชิอนในความทรงจำ แสงสีฟ้าเริ่มรัดรอบข้อมือของเธอแน่นขึ้นเรื่อย ๆ เหมือนสายโซ่ใส", event="play_blue_effect"),
			DialogueLine("Shione", "(ตะโกน) ชิอน! ฟังฉัน! ถ้าเธอยื่นมือให้มัน เธอจะหายไปจากที่นี่ตลอดกาล", emotion="anger", instant_shake=True, portrait_key="shione_neutral"),#<-- shione_anger?
			DialogueLine("Shion", "(น้ำตาไหล) แล้วถ้าที่นี่มันคือความจริง... ทำไมฉันถึงต้องเจ็บปวดขนาดนี้ด้วยล่ะ...", emotion="sadness", portrait_key="shion_neutral"), #<-- shion_sadness?
			DialogueLine("Shione", "(เสียงสั่น) เพราะการเจ็บปวด... คือสิ่งเดียวที่พิสูจน์ได้ว่าเธอยัง ‘มีชีวิต’ อยู่", emotion="sadness", portrait_key="shione_neutral"), #<-- shione_sadness?
		],
		"bed": [
			DialogueLine("Shione", "ถ้าพร้อมไปต่อให้คุณนอนลงที่เตียง และจงจำไว้ว่า การกระทำไม่ว่าด้วยการคิดวิเคราะห์หรือความรู้สึก ไม่สามารถย้อนกลับได้", portrait_key="shione_neutral")
		],
		"flower": [DialogueLine(None, "จริงๆ ก็ยังไม่ได้ทำระบบ save แหละ แหะๆ โทษที เพราะงั้นเกมนี้ ไปต่อได้อย่างเดียวย้อนไม่ได้ อ่อ ปุ่มย้อนกลับก็ยังไม่ทำเพราะงั้นคิดดีๆ ก่อนทำนะคับ จาก เปิร์น")],
		"paper": [
			DialogueLine(None, "ดวงตาทั้ง 7 มี 1 ในนี้เป็นดวงตาของฆาตกร และเจ้าของมันกำลังจะมา ตอนนี้นายท่านอยู่ที่ประตูแล้ว บอกเขาว่าตาไหนเป็นฆาตกร 2 ตา พูดโกหก 3 ตา พูดจริง 2 ตาไม่ทราบ"),
			DialogueLine("Shione", " เราต้องรีบหาฆาตกรให้เจอนะ ไม่งั้นเราจะไม่รอด", portrait_key="shione_neutral"),
			DialogueLine("Shion", "ฆาตกรหรอ บอกฉันที ว่าที่นี่เกิดอะไรขึ้น", portrait_key="shion_neutral"),
		],
		"cyan": [DialogueLine(None, "ตาด้านขวาของฉันเป็นฆาตกร")],
		"purple": [DialogueLine(None, "ตาสีเหลืองเป็นฆาตกร")],
		"green": [DialogueLine(None, "ตาถัดจากฉันไปทางซ้าย 2 ดวง พูดความจริง")],
		"blue": [DialogueLine(None, "ตาตรงข้ามฉันเป็นฆาตกร")],
		"yellow": [DialogueLine(None, "ฉันไม่รู้ แต่สีเขียวดูเหมือนจะพูดความจริง")],
		"red": [DialogueLine(None, "ตาสีม่วงเป็นฆาตกร")],
		"brown": [DialogueLine(None, "ฉันไม่เชื่อตาสีน้ำเงิน")],
		"intro blue": [
			DialogueLine("Shione", "ที่นี่เหมือนความฝันเลย มีต้นไม้เหมือนก้อนเมฆ พื้นเหมือนท้องฟ้า แต่อย่าโดนมันหลอกนะ", portrait_key="shione_neutral"),
			DialogueLine("Shion", "เข้าใจแล้ว", portrait_key="shion_neutral"),
		],
		"bunny": [
			DialogueLine("Bunny", "พี่มาทำอะไรที่นี่หรอคะ หนูน่ะไม่อยากให้พี่ออกไปเลย", portrait_key="bunny"),
			DialogueLine("Shione", "ฉันว่าเราควรจะจัดการนะ", portrait_key="shione_neutral"),
			DialogueLine("Shione",
			"ฉันว่าเราควรจะจัดการนะ",
			choices=[
				DialogueChoice("ฆ่า", event="exit_game", goto_script=None),
				DialogueChoice("ไม่ฆ่า", event="exit_bunny", goto_script=None),
			],
			portrait_key="shione_neutral"),
		],
		"sheep": [
			DialogueLine("Sheep", "พ....พวกคุณมาทำอะไรที่นี่หรอค่ะ ช่วยฉันด้วย", portrait_key="sheep"),
			DialogueLine("Shione", "เราควรช่วยเขานะ", portrait_key="shione_neutral"),
			DialogueLine("Shione",
				"เราควรช่วยเขานะ",
				choices=[
				DialogueChoice("ช่วย", event="save_sheep", goto_script=None),
				DialogueChoice("ไม่ช่วย", event="exit_game", goto_script=None),
			],
			portrait_key="shione_neutral"),
		],
		"fish": [
			DialogueLine("Shione", "เงือกอยู่บนน้ำ มันน่าสงสัยไปแล้วรึเปล่า", portrait_key="shione_neutral"),
			DialogueLine("Shione", "เงือกอยู่บนน้ำ มันน่าสงสัยไปแล้วรึเปล่า",
			choices=[
				DialogueChoice("ฆ่า", event="exit_game", goto_script=None),
				DialogueChoice("ไม่ฆ่า", event="exit_fish", goto_script=None),
			],
			portrait_key="shione_neutral")],
		"intro yellow": [
			DialogueLine("Shione", "ห้องนี้เหมือนจะเป็นทางเดินดอกแดนดิไลออนนะ เดินตามที่ฉันบอกนะ", portrait_key="shione_neutral"),
			DialogueLine("Shion", "เข้าใจแล้ว", portrait_key="shion_neutral"),
		],
		"white": [
			DialogueLine("Shion", "ฉันมองเห็น", portrait_key="shion_neutral")],
		"closed_door": [DialogueLine(None, "ประตูนี้ปิดอยู่")],
		"room1_hall": [
			DialogueLine(None, "ชอบหนังสือเล่มไหนมากที่สุด?"),
			DialogueLine(
				None, 
				"ชอบหนังสือเล่มไหนมากที่สุด?",
				choices=[
					DialogueChoice("Red book", event="select_book1", goto_script=None),
					DialogueChoice("Blue book", event="select_book2", goto_script=None),
					DialogueChoice("Yellow book", event="select_book3", goto_script=None),
				],
				portrait_key="shione_neutral"
			)],
		"red_hall": [
			DialogueLine(None, "คุณจะทำลายดวงตาดวงไหน?"),
			DialogueLine(
				None,
				"คุณจะทำลายดวงตาดวงไหน?",
				choices=[
					DialogueChoice("น้ำตาล", event="exit_game", goto_script=None),
					DialogueChoice("แดง", event="exit_game", goto_script=None),
					DialogueChoice("เหลือง", event="exit_game", goto_script=None),
					DialogueChoice("ม่วง", event="select_purple_eye", goto_script=None),
					DialogueChoice("ฟ้า", event="exit_game", goto_script=None),
					DialogueChoice("น้ำเงิน", event="exit_game", goto_script=None),
					DialogueChoice("เขียว", event="exit_game", goto_script=None),
				],
				portrait_key="shione_neutral"
			)],
		"door_locked": [
			DialogueLine(None, "the door is lock")
		],
		"default": [DialogueLine(None, "An interesting object.")],
		}

		# ===== STATE MANAGEMENT =====
		self.is_active = False
		self.active_script: List[DialogueLine] = []
		self.current_line_index = 0
		self.current_line_data: Optional[DialogueLine] = None

		# ===== TYPEWRITER STATE =====
		self.text_speed = GameConfig.TEXT_SPEED
		self.text_timer = 0  # Accumulates milliseconds
		self.current_char_index = 0  # How many characters to show
		self.full_text_content = ""
		self.wrapped_lines: List[str] = []  # Text split into lines for display
		self.is_typing = False

		# ===== SHAKE STATE =====
		self.is_shaking = False
		self.shake_frames_left = 0
		self.SHAKE_DURATION_FRAMES = 8
		self.SHAKE_AMPLITUDE = 3

		# ===== PORTRAIT STATE =====
		self.current_portrait_surface: Optional[pygame.Surface] = None
		self.portrait_rect = pygame.Rect(0, 0, 0, 0)
		
		# ===== CHOICE STATE =====
		self.is_showing_choices = False
		self.current_choices: List[DialogueChoice] = []
		self.selected_choice_index = 0
		self.choice_animation_timer = 0  # For smooth animations

		# ===== UI RECTANGLES =====
		# Main dialogue box at bottom of screen
		self.dialog_box_rect = pygame.Rect(
			self.box_padding,
			GameConfig.SCREEN_HEIGHT - 150 - self.box_padding,
			GameConfig.SCREEN_WIDTH - (self.box_padding * 2),
			150
		)
		self.text_area_rect = self.dialog_box_rect.inflate(-40, -40)
		
		# Choice box positioning (centered on screen)
		self.choice_box_width = 600
		self.choice_box_height = 400
		self.choice_box_rect = pygame.Rect(
			(GameConfig.SCREEN_WIDTH - self.choice_box_width) // 2,
			(GameConfig.SCREEN_HEIGHT - self.choice_box_height) // 2,
			self.choice_box_width,
			self.choice_box_height
		)

		# Speaker name box above dialogue box
		self.speaker_box_rect = pygame.Rect(
			self.dialog_box_rect.x,
			self.dialog_box_rect.y - 50,
			200, 50
		)
		self.speaker_text_rect = self.speaker_box_rect.inflate(-20, -20)

	def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
		"""
		Split text into lines that fit within max_width.
		Handles Thai text properly.
		"""
		lines = []
		words = text.split(' ')
		current_line = ""
		
		for word in words:
			test_line = current_line + word + " "
			if font.size(test_line)[0] <= max_width:
				current_line = test_line
			else:
				if current_line:  # Don't add empty lines
					lines.append(current_line)
				current_line = word + " "
		
		if current_line:
			lines.append(current_line)
		
		return lines

	def start_conversation(self, script_id: str):
		"""Begin a new dialogue sequence."""
		if self.is_active:
			return  # Don't interrupt active dialogue
		
		# Load the requested script (or default if not found)
		self.active_script = self.scripts.get(script_id, self.scripts["default"])
		self.active_script_id = script_id  # Store script ID for sync
		self.is_active = True
		self.current_line_index = -1
		self._next_line_internal()

	def next_line(self) -> Optional[str]:
		"""
		Advance to next dialogue line (called when player presses E).
		Returns event string if this line triggers an event.
		Note: This should NOT be called when showing choices - use select_choice() instead.
		"""
		if not self.is_active:
			return None
		
		# Don't advance if showing choices
		if self.is_showing_choices:
			return None
		
		# Don't advance during shake effect
		if self.is_shaking:
			return None
		
		# If still typing, skip to end of current line
		if self.is_typing:
			self.is_typing = False
			self.current_char_index = len(self.full_text_content)
			return None
		
		# Get event before advancing (so it triggers at right time)
		event_to_fire = self.current_line_data.event if self.current_line_data else None
		
		# Check if this was the last line
		if self.current_line_index + 1 >= len(self.active_script):
			self.end_conversation()
		else:
			self._next_line_internal()
		
		return event_to_fire
	
	def move_choice_selection(self, direction: str) -> None:
		"""
		Move choice selection up/down.
		direction: 'up' (W) or 'down' (S), 'left' (A) or 'right' (D)
		"""
		if not self.is_showing_choices or not self.current_choices:
			return
		
		if direction == 'up' or direction == 'left':
			self.selected_choice_index = (self.selected_choice_index - 1) % len(self.current_choices)
		elif direction == 'down' or direction == 'right':
			self.selected_choice_index = (self.selected_choice_index + 1) % len(self.current_choices)
		
		self.choice_animation_timer = 0  # Reset animation
	
	def select_choice(self) -> Optional[str]:
		"""
		Select the currently highlighted choice.
		Returns the event string associated with the choice, or None.
		"""
		if not self.is_showing_choices or not self.current_choices:
			return None
		
		selected_choice = self.current_choices[self.selected_choice_index]
		
		# Handle goto_script if specified
		if selected_choice.goto_script:
			# Jump to a different script
			self.active_script = self.scripts.get(selected_choice.goto_script, self.scripts["default"])
			self.active_script_id = selected_choice.goto_script
			self.current_line_index = selected_choice.goto_line if selected_choice.goto_line is not None else -1
			self._next_line_internal()
		else:
			# Continue to next line in current script
			if self.current_line_index + 1 >= len(self.active_script):
				self.end_conversation()
			else:
				self._next_line_internal()
		
		# Clear choice state
		self.is_showing_choices = False
		self.current_choices = []
		
		# Return event for handling
		return selected_choice.event

	def _next_line_internal(self):
		"""
		Internal: Load next line and setup its display state.
		Handles typewriter, shake, portrait, and choice setup.
		"""
		self.current_line_index += 1
		self.current_line_data = self.active_script[self.current_line_index]

		# ===== CHECK IF THIS IS A CHOICE LINE =====
		if self.current_line_data.choices and len(self.current_line_data.choices) > 0:
			# This is a choice line - show choices instead of text
			self.is_showing_choices = True
			self.current_choices = self.current_line_data.choices
			self.selected_choice_index = 0
			self.choice_animation_timer = 0
			# Don't process as regular text
			return

		# ===== PREPARE TEXT (REGULAR DIALOGUE LINE) =====
		self.is_showing_choices = False
		self.current_choices = []
		self.full_text_content = self.current_line_data.text
		self.wrapped_lines = self._wrap_text(
			self.full_text_content,
			self.text_font,
			self.text_area_rect.width
		)
		
		# ===== RESET EFFECTS =====
		self.is_shaking = False
		self.shake_frames_left = 0

		# ===== LOAD PORTRAIT =====
		self.current_portrait_surface = None
		portrait_key = self.current_line_data.portrait_key
		
		if portrait_key:
			portrait_key = portrait_key.lower()
			if portrait_key in self.game.character_portraits:
				self.current_portrait_surface = self.game.character_portraits[portrait_key]
				# Center portrait on screen
				self.portrait_rect = self.current_portrait_surface.get_rect(
					center=(GameConfig.SCREEN_WIDTH // 2, GameConfig.SCREEN_HEIGHT // 2)
				)
			else:
				print(f"Warning: Portrait '{portrait_key}' not found")

		# ===== SETUP DISPLAY MODE =====
		# Remove typewriter delay: always show full text immediately
		self.current_char_index = len(self.full_text_content)
		self.is_typing = False
		# Keep shake effect only if explicitly requested
		if self.current_line_data.instant_shake:
			self.is_shaking = True
			self.shake_frames_left = self.SHAKE_DURATION_FRAMES
		else:
			self.is_shaking = False

	def end_conversation(self):
		"""Clean up and exit dialogue mode."""
		self.is_active = False
		self.active_script = []
		self.current_line_index = 0
		self.current_line_data = None

		# Reset all effects
		self.is_typing = False
		self.wrapped_lines = []
		self.full_text_content = ""
		self.current_char_index = 0
		self.text_timer = 0
		self.is_shaking = False
		self.shake_frames_left = 0
		self.current_portrait_surface = None
		
		# Reset choice state
		self.is_showing_choices = False
		self.current_choices = []
		self.selected_choice_index = 0
		self.choice_animation_timer = 0

	def update(self, dt_ms: int):
		"""
		Update dialogue effects (called every frame).
		dt_ms: Delta time in milliseconds since last frame.
		"""
		# ===== UPDATE CHOICE ANIMATION =====
		if self.is_showing_choices:
			self.choice_animation_timer += dt_ms
			return
		
		# ===== UPDATE SHAKE EFFECT =====
		if self.is_shaking:
			self.shake_frames_left -= 1
			if self.shake_frames_left <= 0:
				self.is_shaking = False
			return  # Don't do typewriter during shake

		# ===== UPDATE TYPEWRITER EFFECT (disabled: show full text instantly) =====
		if self.is_active:
			self.is_typing = False
			self.current_char_index = len(self.full_text_content)

	def draw(self, screen: pygame.Surface) -> None:
		"""
		Render the dialogue box, text, character portrait, or choice menu.
		"""
		if not self.is_active:
			return
		
		# ===== CHECK IF SHOWING CHOICES =====
		if self.is_showing_choices:
			self._draw_choices(screen)
			return
		
		# Copy reference to avoid mid-draw changes from other threads
		line_data = self.current_line_data
		if not line_data:
			return

		# ===== 1. DRAW CHARACTER PORTRAIT =====
		# Portraits are drawn full-screen behind dialogue box
		if self.current_portrait_surface:
			screen.blit(self.current_portrait_surface, self.portrait_rect)

		# ===== 2. DRAW DIALOGUE BOX =====
		pygame.draw.rect(screen, GameConfig.DIALOG_BG_COLOR, self.dialog_box_rect)
		pygame.draw.rect(screen, GameConfig.DIALOG_BORDER_COLOR, self.dialog_box_rect, 3)

		# ===== 3. DETERMINE TEXT COLOR =====
		# Priority: Character color > Emotion color > Default
		current_text_color = GameConfig.TEXT_COLOR_NEUTRAL
		speaker_name = line_data.speaker if line_data else None
		
		if speaker_name and speaker_name in GameConfig.CHARACTER_COLORS:
			# Use character-specific color
			current_text_color = GameConfig.CHARACTER_COLORS[speaker_name]
		elif line_data and line_data.emotion == "surprise":
			current_text_color = GameConfig.TEXT_COLOR_SURPRISE
		elif line_data and line_data.emotion == "anger":
			current_text_color = GameConfig.TEXT_COLOR_ANGER
		elif line_data and line_data.emotion == "sadness":
			current_text_color = GameConfig.TEXT_COLOR_SADNESS

		# ===== 4. DRAW SPEAKER NAME BOX =====
		if speaker_name:
			pygame.draw.rect(screen, GameConfig.DIALOG_BG_COLOR, self.speaker_box_rect)
			pygame.draw.rect(screen, GameConfig.DIALOG_BORDER_COLOR, self.speaker_box_rect, 3)
			speaker_surf = self.speaker_font.render(speaker_name, True, current_text_color)
			screen.blit(speaker_surf, self.speaker_text_rect)

		# ===== 5. DRAW TEXT (WITH EFFECTS) =====
		base_x = self.text_area_rect.x
		base_y = self.text_area_rect.y

		# Determine if we should obfuscate dialogue for Shion
		should_obfuscate = False
		try:
			role = getattr(self.game, 'player_role', None)
			speaker_lower = (speaker_name or "").lower()
			if role == 'shion' and speaker_lower not in ('shion', 'shione'):
				should_obfuscate = True
		except Exception:
			should_obfuscate = False

		def _obfuscate_text(s: str) -> str:
			# Replace non-whitespace characters with '*', preserve spaces for readability
			return ''.join(ch if ch.isspace() else '*' for ch in s)

		# --- SHAKE MODE: Draw all text with random offset ---
		if self.is_shaking:
			# Pre-render all lines
			total_height = 0
			rendered_lines = []
			for line_string in self.wrapped_lines:
				line_to_draw = _obfuscate_text(line_string) if should_obfuscate else line_string
				line_surface = self.text_font.render(line_to_draw, True, current_text_color)
				rendered_lines.append(line_surface)
				total_height += line_surface.get_height() + self.line_spacing
			if rendered_lines:
				total_height -= self.line_spacing  # Remove extra spacing after last line

			# Combine into single surface for efficient shaking
			if total_height > 0 and self.text_area_rect.width > 0:
				text_block_surface = pygame.Surface(
					(self.text_area_rect.width, total_height), 
					pygame.SRCALPHA
				)
				text_block_surface.fill((0, 0, 0, 0))
				
				current_y_on_block = 0
				for line_surface in rendered_lines:
					text_block_surface.blit(line_surface, (0, current_y_on_block))
					current_y_on_block += line_surface.get_height() + self.line_spacing

				# Apply shake offset (only on even frames for stutter effect)
				draw_x, draw_y = base_x, base_y
				if self.shake_frames_left > 0 and self.shake_frames_left % 2 == 0:
					draw_x += random.randint(-self.SHAKE_AMPLITUDE, self.SHAKE_AMPLITUDE)
					draw_y += random.randint(-self.SHAKE_AMPLITUDE, self.SHAKE_AMPLITUDE)
				
				screen.blit(text_block_surface, (draw_x, draw_y))

		# --- TYPEWRITER/NORMAL MODE: Draw character-by-character ---
		else:
			current_y = base_y
			chars_to_show_total = self.current_char_index
			
			for line_string in self.wrapped_lines:
				if chars_to_show_total <= 0:
					break
				
				# Calculate how many characters to show on this line
				chars_on_this_line = len(line_string)
				text_to_render = line_string[:min(chars_to_show_total, chars_on_this_line)]
				chars_to_show_total -= chars_on_this_line

				# Render and draw this line
				line_surface = self.text_font.render(_obfuscate_text(text_to_render) if should_obfuscate else text_to_render, True, current_text_color)
				screen.blit(line_surface, (base_x, current_y))
				current_y += line_surface.get_height() + self.line_spacing

		# ===== 6. DRAW [E] PROMPT =====
		# Only show when text is fully displayed and not shaking
		if not self.is_typing and not self.is_shaking:
			prompt_pos = (
				self.dialog_box_rect.right - self.prompt_text.get_width() - 15,
				self.dialog_box_rect.bottom - self.prompt_text.get_height() - 15
			)
			screen.blit(self.prompt_text, prompt_pos)
	
	def _draw_choices(self, screen: pygame.Surface) -> None:
		"""
		Draw beautiful choice menu UI with WASD navigation indicators.
		"""
		if not self.current_choices:
			return
		
		# ===== DRAW SEMI-TRANSPARENT BACKDROP =====
		backdrop = pygame.Surface((GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT), pygame.SRCALPHA)
		backdrop.fill((0, 0, 0, 180))  # Dark overlay with transparency
		screen.blit(backdrop, (0, 0))
		
		# ===== CALCULATE DYNAMIC BOX SIZE BASED ON NUMBER OF CHOICES =====
		choice_padding = 20
		choice_height = 70
		choice_spacing = 15
		top_padding = 60
		bottom_padding = 40  # For navigation hints
		
		# Calculate required height
		num_choices = len(self.current_choices)
		required_height = top_padding + (num_choices * (choice_height + choice_spacing)) - choice_spacing + bottom_padding
		
		# Use dynamic height or minimum size
		box_height = max(required_height, 400)
		box_width = 600  # Keep width constant
		
		# Calculate centered position
		box_x = (GameConfig.SCREEN_WIDTH - box_width) // 2
		box_y = (GameConfig.SCREEN_HEIGHT - box_height) // 2
		box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
		
		# ===== DRAW CHOICE BOX BACKGROUND =====
		# Main box with rounded corners effect (using gradient-like border)
		
		# Outer glow effect
		outer_rect = box_rect.inflate(10, 10)
		pygame.draw.rect(screen, (100, 150, 255), outer_rect, border_radius=15)
		
		# Main box
		pygame.draw.rect(screen, (20, 20, 30), box_rect, border_radius=10)
		pygame.draw.rect(screen, (80, 120, 200), box_rect, width=3, border_radius=10)
		
		# Inner highlight
		inner_rect = box_rect.inflate(-8, -8)
		pygame.draw.rect(screen, (40, 50, 70), inner_rect, border_radius=8)
		
		# ===== CALCULATE CHOICE ITEM POSITIONS =====
		start_y = box_rect.y + top_padding
		
		# Calculate pulse animation for selected item
		pulse_factor = abs(math.sin(self.choice_animation_timer / 200.0)) * 0.15 + 0.85
		
		# ===== DRAW EACH CHOICE =====
		for i, choice in enumerate(self.current_choices):
			choice_y = start_y + i * (choice_height + choice_spacing)
			choice_rect = pygame.Rect(
				box_rect.x + choice_padding,
				choice_y,
				box_rect.width - (choice_padding * 2),
				choice_height
			)
			
			is_selected = (i == self.selected_choice_index)
			
			# ===== CHOICE BOX BACKGROUND =====
			if is_selected:
				# Selected choice: brighter with animation
				selected_bg = (60 + int(30 * pulse_factor), 90 + int(30 * pulse_factor), 150 + int(50 * pulse_factor))
				pygame.draw.rect(screen, selected_bg, choice_rect, border_radius=8)
				# Glowing border for selected
				pygame.draw.rect(screen, (120, 180, 255), choice_rect, width=3, border_radius=8)
				# Arrow indicator
				arrow_x = choice_rect.x + 15
				arrow_y = choice_rect.centery
				pygame.draw.polygon(screen, (255, 255, 150), [
					(arrow_x, arrow_y - 8),
					(arrow_x + 12, arrow_y),
					(arrow_x, arrow_y + 8)
				])
			else:
				# Unselected choice: darker
				pygame.draw.rect(screen, (30, 35, 45), choice_rect, border_radius=8)
				pygame.draw.rect(screen, (60, 80, 100), choice_rect, width=2, border_radius=8)
			
			# ===== DRAW CHOICE TEXT =====
			text_color = (255, 255, 255) if is_selected else (200, 200, 200)
			text_x = choice_rect.x + (45 if is_selected else 25)
			text_y = choice_rect.centery - self.text_font.get_height() // 2
			
			# Wrap choice text if too long
			max_text_width = choice_rect.width - (text_x - choice_rect.x) - 20
			choice_lines = self._wrap_text(choice.text, self.text_font, max_text_width)
			
			current_text_y = text_y
			for line in choice_lines[:2]:  # Max 2 lines per choice
				text_surface = self.text_font.render(line, True, text_color)
				screen.blit(text_surface, (text_x, current_text_y))
				current_text_y += text_surface.get_height() + 3
		
		# ===== DRAW NAVIGATION HINTS =====
		hint_y = box_rect.bottom - 40
		hint_text = self.speaker_font.render("WASD: Navigate  |  E: Confirm", True, (150, 150, 150))
		hint_x = box_rect.centerx - hint_text.get_width() // 2
		screen.blit(hint_text, (hint_x, hint_y))


# ============================================================================
# INTERACTION PROMPT
# ============================================================================

class InteractionPrompt:
	"""
	Shows 'E' prompt above interactable objects when player is nearby.
	"""
	
	def __init__(self):
		self.font = pygame.font.Font(None, GameConfig.PROMPT_FONT_SIZE)
	
	def draw(self, surface: pygame.Surface, target_component: Component, camera: Camera) -> None:
		"""Draw the [E] prompt above the target object."""
		target_transform = target_component.game_object.get_component(Transform)
		if not target_transform:
			return
			
		# Create prompt text
		prompt_text = self.font.render("E", True, GameConfig.PROMPT_TEXT_COLOR)
		
		# Position above object (in world coordinates)
		prompt_rect = prompt_text.get_rect(
			centerx=target_transform.rect.centerx,
			bottom=target_transform.rect.top - 5
		)
		bg_rect = prompt_rect.inflate(10, 6)
		
		# Convert to screen coordinates
		screen_bg_rect = camera.world_to_screen(bg_rect)
		screen_prompt_rect = camera.world_to_screen(prompt_rect)
		
		# Draw background box and text
		pygame.draw.rect(surface, GameConfig.PROMPT_BG_COLOR, screen_bg_rect)
		pygame.draw.rect(surface, GameConfig.PROMPT_TEXT_COLOR, screen_bg_rect, 1)
		surface.blit(prompt_text, screen_prompt_rect)


# ============================================================================
# MAIN GAME CLASS
# ============================================================================

# class Game:
# 	"""
# 	Main game controller - manages game loop, scene transitions, and all systems.
# 	"""
	
# 	def __init__(self):
# 		pygame.init()

# 		# ===== DISPLAY SETUP =====
# 		# Main display (what player sees)
# 		self.screen = pygame.display.set_mode(
# 			(GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT)
# 		)
		
# 		# Game surface (rendered at lower resolution for pixel art)
# 		game_surface_size = (
# 			GameConfig.SCREEN_WIDTH // GameConfig.ZOOM_LEVEL,
# 			GameConfig.SCREEN_HEIGHT // GameConfig.ZOOM_LEVEL
# 		)
# 		self.game_surface = pygame.Surface(game_surface_size)
		
# 		pygame.display.set_caption("My Game")
# 		self.clock = pygame.time.Clock()

# 		# ===== FADE TRANSITION SETUP =====
# 		self.fade_surface = pygame.Surface((GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT))
# 		self.fade_surface.fill((0, 0, 0))
# 		self.fade_alpha = 255  # Start with black screen

# 		# ===== LOAD CHARACTER PORTRAITS =====
# 		self.character_portraits: Dict[str, pygame.Surface] = {}
# 		self._load_character_portraits()

# 		# ===== TELEPORT STATE =====
# 		# Stores destination when fading out
# 		self.teleport_target_map: Optional[str] = None
# 		self.teleport_target_spawn: Optional[str] = None

# 		# ===== GAME SYSTEMS =====
# 		self.dialog_system = DialogSystem(self)
# 		self.interaction_prompt = InteractionPrompt()
# 		self.camera = Camera(game_surface_size[0], game_surface_size[1])

# 		# ===== GAME STATE =====
# 		self.state = GameConfig.STATE_FADING_IN  # Start with fade-in effect
# 		self.current_interaction_target = None
# 		self.game_flags = set()  # For tracking story progress

# 		# ===== SCENE & PLAYER REFERENCES =====
# 		self.scene: Optional[Scene] = None
# 		self.player_go: Optional[GameObject] = None
# 		self.player_transform: Optional[Transform] = None
# 		self.player_collider: Optional[BoxCollider] = None

# 		# ===== LOAD STARTING SCENE =====
# 		self.load_scene(GameConfig.START_MAP_PATH, "initial_spawn")

# 		# ===== START OPENING CUTSCENE =====
# 		self.dialog_system.start_conversation("intro")
# 		self.state = GameConfig.STATE_DIALOGUE

# 	def _load_character_portraits(self):
# 		"""
# 		Load all character portrait images from asset folder.
# 		Filenames (without extension) become portrait keys.
# 		"""
# 		portrait_dir = GameConfig.PORTRAIT_ASSET_PATH
# 		print(f"Loading portraits from: {portrait_dir}")
		
# 		try:
# 			# Check if directory exists
# 			if not os.path.isdir(portrait_dir):
# 				print(f"Warning: Portrait directory not found: {portrait_dir}")
# 				return

# 			# Load all image files
# 			for filename in os.listdir(portrait_dir):
# 				if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
# 					# Use filename (without extension) as key, lowercase
# 					key = os.path.splitext(filename)[0].lower()
# 					path = os.path.join(portrait_dir, filename)
					
# 					try:
# 						image = pygame.image.load(path).convert_alpha()

# 						# ===== SCALE PORTRAIT IF CONFIGURED =====
# 						target_w = GameConfig.PORTRAIT_DISPLAY_WIDTH
# 						target_h = GameConfig.PORTRAIT_DISPLAY_HEIGHT
						
# 						if target_w and target_h:
# 							# Scale to exact dimensions
# 							image = pygame.transform.scale(image, (target_w, target_h))
# 						elif target_w:
# 							# Scale by width, maintain aspect ratio
# 							orig_w, orig_h = image.get_size()
# 							if orig_w > 0:
# 								ratio = target_w / orig_w
# 								new_h = int(orig_h * ratio)
# 								image = pygame.transform.scale(image, (target_w, new_h))
# 						elif target_h:
# 							# Scale by height, maintain aspect ratio
# 							orig_w, orig_h = image.get_size()
# 							if orig_h > 0:
# 								ratio = target_h / orig_h
# 								new_w = int(orig_w * ratio)
# 								image = pygame.transform.scale(image, (new_w, target_h))

# 						self.character_portraits[key] = image
# 						print(f"  Loaded portrait: {key}")
						
# 					except pygame.error as load_error:
# 						print(f"  Error loading image '{filename}': {load_error}")
# 					except ValueError as scale_error:
# 						print(f"  Error scaling image '{filename}': {scale_error}")

# 		except Exception as e:
# 			print(f"Error accessing portrait directory {portrait_dir}: {e}")

# 	def load_scene(self, map_path: str, spawn_point_name: str):
# 		"""
# 		Load a new scene and create player at spawn point.
# 		Called at game start and when teleporting between scenes.
# 		"""
# 		print(f"Loading scene: {map_path} at spawn point: '{spawn_point_name}'")

# 		# Create new scene
# 		self.scene = Scene(self, map_path)
		
# 		# Find spawn point and create player there
# 		spawn_pos = self.scene.find_spawn_point(spawn_point_name)
# 		self.player_go = self.scene.create_player(spawn_pos[0], spawn_pos[1])
		
# 		# Cache player component references for quick access
# 		self.player_transform = self.player_go.get_component(Transform)
# 		self.player_collider = self.player_go.get_component(BoxCollider)
		
# 		# Initialize all scene objects
# 		self.scene.start()
# 		self.current_interaction_target = None

# 	def handle_input(self) -> bool:
# 		"""
# 		Process all input events.
# 		Returns False if player wants to quit.
# 		"""
# 		for event in pygame.event.get():
# 			if event.type == pygame.QUIT:
# 				return False
			
# 			if event.type == pygame.KEYDOWN:
				
# 				# ===== E KEY: DIALOGUE & INTERACTION =====
# 				if event.key == pygame.K_e:
					
# 					# --- During dialogue: advance text ---
# 					if self.state == GameConfig.STATE_DIALOGUE:
# 						triggered_event = self.dialog_system.next_line()
						
# 						# Handle any event triggered by dialogue
# 						if triggered_event:
# 							self.handle_dialogue_event(triggered_event)
							
# 						# Check if dialogue ended
# 						if not self.dialog_system.is_active:
# 							if self.state == GameConfig.STATE_DIALOGUE:
# 								self.state = GameConfig.STATE_PLAYING

# 					# --- During gameplay: interact with objects ---
# 					elif self.state == GameConfig.STATE_PLAYING:
# 						if self.current_interaction_target:
# 							game_object = self.current_interaction_target.game_object

# 							# Priority 1: Teleport (scene transition)
# 							teleport_comp = game_object.get_component(Teleport)
# 							if teleport_comp:
# 								# Start fade out
# 								self.state = GameConfig.STATE_FADING_OUT
# 								self.fade_alpha = 0
# 								self.teleport_target_map = teleport_comp.target_map
# 								self.teleport_target_spawn = teleport_comp.target_spawn_point
# 								return True

# 							# Priority 2: Door toggle
# 							door_comp = game_object.get_component(Door)
# 							if door_comp:
# 								door_comp.toggle()
								
# 							# Priority 3: Generic interactable (start dialogue)
# 							interact_comp = game_object.get_component(Interactable)
# 							if interact_comp:
# 								# Dialogue script ID = object name
# 								self.dialog_system.start_conversation(interact_comp.name)
# 								if self.dialog_system.is_active:
# 									self.state = GameConfig.STATE_DIALOGUE
		
# 		return True
	
# 	def handle_dialogue_event(self, event: str):
# 		"""
# 		Handle custom events triggered by dialogue lines.
# 		Used to trigger gameplay changes from story moments.
# 		"""
# 		print(f"[Game Event Triggered]: {event}")
		
# 		if event == "trigger_bed_tutorial":
# 			# Chain to another dialogue immediately
# 			self.dialog_system.start_conversation("_tutorial_bed")
# 			self.state = GameConfig.STATE_DIALOGUE
			
# 		elif event == "play_dandelion_effect":
# 			# Placeholder for visual effect
# 			print("--- (Play yellow dandelion particle effect) ---")
			
# 		elif event == "play_blue_effect":
# 			# Placeholder for visual effect
# 			print("--- (Play blue sky visual effect) ---")
			
# 		# Add more events here as needed
# 		# elif event == "unlock_door":
# 		#     self.game_flags.add("door_unlocked")

# 	def update(self, dt_ms: int) -> None:
# 		"""
# 		Update game state every frame.
# 		dt_ms: Delta time in milliseconds (for frame-independent timing).
# 		"""
		
# 		# ===== STATE: FADING OUT (Before teleport) =====
# 		if self.state == GameConfig.STATE_FADING_OUT:
# 			self.fade_alpha += GameConfig.FADE_SPEED
# 			if self.fade_alpha >= 255:
# 				self.fade_alpha = 255
# 				# Screen is now black - do the actual teleport
# 				self.load_scene(self.teleport_target_map, self.teleport_target_spawn)
# 				self.state = GameConfig.STATE_FADING_IN
# 			return

# 		# ===== FADE IN/OUT VISUAL EFFECT =====
# 		if self.fade_alpha > 0:
# 			self.fade_alpha -= GameConfig.FADE_SPEED
# 			if self.fade_alpha <= 0:
# 				self.fade_alpha = 0
# 				# Fade-in complete
# 				if self.state == GameConfig.STATE_FADING_IN:
# 					self.state = GameConfig.STATE_PLAYING
# 					self.teleport_target_map = None

# 		# ===== UPDATE DIALOGUE SYSTEM =====
# 		# Typewriter effect needs to run even during dialogue state
# 		self.dialog_system.update(dt_ms)

# 		# ===== STATE: PLAYING (Normal gameplay) =====
# 		if self.state == GameConfig.STATE_PLAYING:
# 			if not self.scene or not self.player_transform:
# 				return

# 			# Update all game objects
# 			self.scene.update()
			
# 			# Update camera to follow player
# 			self.camera.update(self.player_transform.rect.center)
			
# 			# Check for nearby interactable objects
# 			collided = pygame.sprite.spritecollide(
# 				self.player_collider,
# 				self.scene.interactables,
# 				False  # Don't remove from group
# 			)
# 			self.current_interaction_target = collided[0] if collided else None

# 	def draw(self) -> None:
# 		"""Render the current frame."""
# 		if not self.scene:
# 			return
		
# 		# ===== 1. RENDER GAME WORLD =====
# 		# Draw to low-res surface for pixel art look
# 		self.game_surface.fill((0, 0, 0))
# 		self.scene.draw(self.game_surface, self.camera)
		
# 		# Draw interaction prompt if applicable
# 		if (self.current_interaction_target and 
# 			self.state == GameConfig.STATE_PLAYING):
# 			self.interaction_prompt.draw(
# 				self.game_surface,
# 				self.current_interaction_target,
# 				self.camera
# 			)
		
# 		# ===== 2. SCALE TO FULL SCREEN =====
# 		scaled_surface = pygame.transform.scale(
# 			self.game_surface,
# 			(GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT)
# 		)
# 		self.screen.blit(scaled_surface, (0, 0))
		
# 		# ===== 3. DRAW UI OVERLAY =====
# 		if self.dialog_system.is_active:
# 			self.dialog_system.draw(self.screen)
		
# 		# ===== 4. DRAW FADE OVERLAY =====
# 		if self.fade_alpha > 0:
# 			self.fade_surface.set_alpha(self.fade_alpha)
# 			self.screen.blit(self.fade_surface, (0, 0))

# 		# ===== 5. FLIP DISPLAY =====
# 		pygame.display.flip()

# 	def run(self) -> None:
# 		"""
# 		Main game loop.
# 		Runs continuously until player quits.
# 		"""
# 		running = True
# 		while running:
# 			# Get delta time (milliseconds since last frame)
# 			dt_ms = self.clock.tick(GameConfig.FPS)
			
# 			# Process input (returns False if quit)
# 			running = self.handle_input()
			
# 			# Update game state
# 			self.update(dt_ms)
			
# 			# Render frame
# 			self.draw()
			
# 		pygame.quit()
# 		sys.exit()


# # ============================================================================
# # ENTRY POINT
# # ============================================================================

# def main():
# 	"""Entry point for the game."""
# 	game = Game()
# 	game.run()


# if __name__ == "__main__":
# 	main()
