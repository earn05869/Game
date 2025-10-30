# ============================================================================
# MAIN GAME CLASS
# ============================================================================
from simple_2d_game import *
class Game:
	"""
	Main game controller - manages game loop, scene transitions, and all systems.
	"""
	
	def __init__(self):
		pygame.init()

		# ===== DISPLAY SETUP =====
		# Main display (what player sees)
		self.screen = pygame.display.set_mode(
			(GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT)
		)
		
		# Game surface (rendered at lower resolution for pixel art)
		game_surface_size = (
			GameConfig.SCREEN_WIDTH // GameConfig.ZOOM_LEVEL,
			GameConfig.SCREEN_HEIGHT // GameConfig.ZOOM_LEVEL
		)
		self.game_surface = pygame.Surface(game_surface_size)
		
		pygame.display.set_caption("My Game")
		self.clock = pygame.time.Clock()

		# ===== FADE TRANSITION SETUP =====
		self.fade_surface = pygame.Surface((GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT))
		self.fade_surface.fill((0, 0, 0))
		self.fade_alpha = 255  # Start with black screen

		# ===== LOAD CHARACTER PORTRAITS =====
		self.character_portraits: Dict[str, pygame.Surface] = {}
		self._load_character_portraits()

		# ===== TELEPORT STATE =====
		# Stores destination when fading out
		self.teleport_target_map: Optional[str] = None
		self.teleport_target_spawn: Optional[str] = None

		# ===== GAME SYSTEMS =====
		self.dialog_system = DialogSystem(self)
		self.interaction_prompt = InteractionPrompt()
		self.camera = Camera(game_surface_size[0], game_surface_size[1])

		# ===== GAME STATE =====
		self.state = GameConfig.STATE_FADING_IN  # Start with fade-in effect
		self.current_interaction_target = None
		self.game_flags = set()  # For tracking story progress

		# ===== SCENE & PLAYER REFERENCES =====
		self.scene: Optional[Scene] = None
		self.player_go: Optional[GameObject] = None
		self.player_transform: Optional[Transform] = None
		self.player_collider: Optional[BoxCollider] = None

		# ===== LOAD STARTING SCENE =====
		self.load_scene(GameConfig.START_MAP_PATH, "initial_spawn")

		# ===== START OPENING CUTSCENE =====
		self.dialog_system.start_conversation("intro")
		self.state = GameConfig.STATE_DIALOGUE

	def _load_character_portraits(self):
		"""
		Load all character portrait images from asset folder.
		Filenames (without extension) become portrait keys.
		"""
		portrait_dir = GameConfig.PORTRAIT_ASSET_PATH
		print(f"Loading portraits from: {portrait_dir}")
		
		try:
			# Check if directory exists
			if not os.path.isdir(portrait_dir):
				print(f"Warning: Portrait directory not found: {portrait_dir}")
				return

			# Load all image files
			for filename in os.listdir(portrait_dir):
				if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
					# Use filename (without extension) as key, lowercase
					key = os.path.splitext(filename)[0].lower()
					path = os.path.join(portrait_dir, filename)
					
					try:
						image = pygame.image.load(path).convert_alpha()

						# ===== SCALE PORTRAIT IF CONFIGURED =====
						target_w = GameConfig.PORTRAIT_DISPLAY_WIDTH
						target_h = GameConfig.PORTRAIT_DISPLAY_HEIGHT
						
						if target_w and target_h:
							# Scale to exact dimensions
							image = pygame.transform.scale(image, (target_w, target_h))
						elif target_w:
							# Scale by width, maintain aspect ratio
							orig_w, orig_h = image.get_size()
							if orig_w > 0:
								ratio = target_w / orig_w
								new_h = int(orig_h * ratio)
								image = pygame.transform.scale(image, (target_w, new_h))
						elif target_h:
							# Scale by height, maintain aspect ratio
							orig_w, orig_h = image.get_size()
							if orig_h > 0:
								ratio = target_h / orig_h
								new_w = int(orig_w * ratio)
								image = pygame.transform.scale(image, (new_w, target_h))

						self.character_portraits[key] = image
						print(f"  Loaded portrait: {key}")
						
					except pygame.error as load_error:
						print(f"  Error loading image '{filename}': {load_error}")
					except ValueError as scale_error:
						print(f"  Error scaling image '{filename}': {scale_error}")

		except Exception as e:
			print(f"Error accessing portrait directory {portrait_dir}: {e}")

	def load_scene(self, map_path: str, spawn_point_name: str):
		"""
		Load a new scene and create player at spawn point.
		Called at game start and when teleporting between scenes.
		"""
		print(f"Loading scene: {map_path} at spawn point: '{spawn_point_name}'")

		# Create new scene
		self.scene = Scene(self, map_path)
		
		# Find spawn point and create player there
		spawn_pos = self.scene.find_spawn_point(spawn_point_name)
		self.player_go = self.scene.create_player(spawn_pos[0], spawn_pos[1])
		
		# Cache player component references for quick access
		self.player_transform = self.player_go.get_component(Transform)
		self.player_collider = self.player_go.get_component(BoxCollider)
		
		# Initialize all scene objects
		self.scene.start()
		self.current_interaction_target = None

	def handle_input(self) -> bool:
		"""
		Process all input events.
		Returns False if player wants to quit.
		"""
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return False
			
			if event.type == pygame.KEYDOWN:
				
				# ===== E KEY: DIALOGUE & INTERACTION =====
				if event.key == pygame.K_e:
					
					# --- During dialogue: advance text ---
					if self.state == GameConfig.STATE_DIALOGUE:
						triggered_event = self.dialog_system.next_line()
						
						# Handle any event triggered by dialogue
						if triggered_event:
							self.handle_dialogue_event(triggered_event)
							
						# Check if dialogue ended
						if not self.dialog_system.is_active:
							if self.state == GameConfig.STATE_DIALOGUE:
								self.state = GameConfig.STATE_PLAYING

					# --- During gameplay: interact with objects ---
					elif self.state == GameConfig.STATE_PLAYING:
						if self.current_interaction_target:
							game_object = self.current_interaction_target.game_object

							# Priority 1: Teleport (scene transition)
							teleport_comp = game_object.get_component(Teleport)
							if teleport_comp:
								# Start fade out
								self.state = GameConfig.STATE_FADING_OUT
								self.fade_alpha = 0
								self.teleport_target_map = teleport_comp.target_map
								self.teleport_target_spawn = teleport_comp.target_spawn_point
								return True

							# Priority 2: Door toggle
							door_comp = game_object.get_component(Door)
							if door_comp:
								door_comp.toggle()
								
							# Priority 3: Generic interactable (start dialogue)
							interact_comp = game_object.get_component(Interactable)
							if interact_comp:
								# Dialogue script ID = object name
								self.dialog_system.start_conversation(interact_comp.name)
								if self.dialog_system.is_active:
									self.state = GameConfig.STATE_DIALOGUE
		
		return True
	
	def handle_dialogue_event(self, event: str):
		"""
		Handle custom events triggered by dialogue lines.
		Used to trigger gameplay changes from story moments.
		"""
		print(f"[Game Event Triggered]: {event}")
		
		if event == "trigger_bed_tutorial":
			# Chain to another dialogue immediately
			self.dialog_system.start_conversation("_tutorial_bed")
			self.state = GameConfig.STATE_DIALOGUE
			
		elif event == "play_dandelion_effect":
			# Placeholder for visual effect
			print("--- (Play yellow dandelion particle effect) ---")
			
		elif event == "play_blue_effect":
			# Placeholder for visual effect
			print("--- (Play blue sky visual effect) ---")
			
		# Add more events here as needed
		# elif event == "unlock_door":
		#     self.game_flags.add("door_unlocked")

	def update(self, dt_ms: int) -> None:
		"""
		Update game state every frame.
		dt_ms: Delta time in milliseconds (for frame-independent timing).
		"""
		
		# ===== STATE: FADING OUT (Before teleport) =====
		if self.state == GameConfig.STATE_FADING_OUT:
			self.fade_alpha += GameConfig.FADE_SPEED
			if self.fade_alpha >= 255:
				self.fade_alpha = 255
				# Screen is now black - do the actual teleport
				self.load_scene(self.teleport_target_map, self.teleport_target_spawn)
				self.state = GameConfig.STATE_FADING_IN
			return

		# ===== FADE IN/OUT VISUAL EFFECT =====
		if self.fade_alpha > 0:
			self.fade_alpha -= GameConfig.FADE_SPEED
			if self.fade_alpha <= 0:
				self.fade_alpha = 0
				# Fade-in complete
				if self.state == GameConfig.STATE_FADING_IN:
					self.state = GameConfig.STATE_PLAYING
					self.teleport_target_map = None

		# ===== UPDATE DIALOGUE SYSTEM =====
		# Typewriter effect needs to run even during dialogue state
		self.dialog_system.update(dt_ms)

		# ===== STATE: PLAYING (Normal gameplay) =====
		if self.state == GameConfig.STATE_PLAYING:
			if not self.scene or not self.player_transform:
				return

			# Update all game objects
			self.scene.update()
			
			# Update camera to follow player
			self.camera.update(self.player_transform.rect.center)
			
			# Check for nearby interactable objects
			collided = pygame.sprite.spritecollide(
				self.player_collider,
				self.scene.interactables,
				False  # Don't remove from group
			)
			self.current_interaction_target = collided[0] if collided else None

	def draw(self) -> None:
		"""Render the current frame."""
		if not self.scene:
			return
		
		# ===== 1. RENDER GAME WORLD =====
		# Draw to low-res surface for pixel art look
		self.game_surface.fill((0, 0, 0))
		self.scene.draw(self.game_surface, self.camera)
		
		# Draw interaction prompt if applicable
		if (self.current_interaction_target and 
			self.state == GameConfig.STATE_PLAYING):
			self.interaction_prompt.draw(
				self.game_surface,
				self.current_interaction_target,
				self.camera
			)
		
		# ===== 2. SCALE TO FULL SCREEN =====
		scaled_surface = pygame.transform.scale(
			self.game_surface,
			(GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT)
		)
		self.screen.blit(scaled_surface, (0, 0))
		
		# ===== 3. DRAW UI OVERLAY =====
		if self.dialog_system.is_active:
			self.dialog_system.draw(self.screen)
		
		# ===== 4. DRAW FADE OVERLAY =====
		if self.fade_alpha > 0:
			self.fade_surface.set_alpha(self.fade_alpha)
			self.screen.blit(self.fade_surface, (0, 0))

		# ===== 5. FLIP DISPLAY =====
		pygame.display.flip()

	def run(self) -> None:
		"""
		Main game loop.
		Runs continuously until player quits.
		"""
		running = True
		while running:
			# Get delta time (milliseconds since last frame)
			dt_ms = self.clock.tick(GameConfig.FPS)
			
			# Process input (returns False if quit)
			running = self.handle_input()
			
			# Update game state
			self.update(dt_ms)
			
			# Render frame
			self.draw()
			
		pygame.quit()
		sys.exit()


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
	"""Entry point for the game."""
	game = Game()
	game.run()


if __name__ == "__main__":
    main()