# ============================================================================
# MAIN GAME CLASS
# ============================================================================
from simple_2d_game import *
from HomePage import HomePage
from network import NetworkClient
import threading
import subprocess
import sys
import time
import socket

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

		# ===== SHION DARK OVERLAY =====
		# Use per-pixel alpha so we can cut a transparent hole around the player
		self.shion_dark_surface = pygame.Surface((GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT), pygame.SRCALPHA)

		# ===== LOAD CHARACTER PORTRAITS =====
		self.character_portraits: Dict[str, pygame.Surface] = {}
		self._load_character_portraits()

		# ===== TELEPORT STATE =====
		# Stores destination when fading out
		self.teleport_target_map: Optional[str] = None
		self.teleport_target_spawn: Optional[str] = None
		
		# ===== PENDING TELEPORT STATE =====
		# Stores teleport info when dialog is shown first
		self.pending_teleport_map: Optional[str] = None
		self.pending_teleport_spawn: Optional[str] = None

		# ===== GAME SYSTEMS =====
		self.dialog_system = DialogSystem(self)
		self.interaction_prompt = InteractionPrompt()
		self.camera = Camera(game_surface_size[0], game_surface_size[1])

		# ===== SCENE-ENTRY DIALOGUE =====
		# Map path -> intro script id (only listed maps will trigger)
		def _norm(p: Optional[str]) -> str:
			try:
				return os.path.normpath(p) if p else ""
			except Exception:
				return p or ""
		self.map_intro_scripts: Dict[str, str] = {
			_norm("asset/yellow/yellow.tmx"): "intro yellow",
			_norm("asset/blue/blue.tmx"): "intro blue",
		}
		self.pending_intro_script: Optional[str] = None

		# ===== GAME STATE =====
		self.state = GameConfig.STATE_HOME  # Start with home screen
		self.current_interaction_target = None
		self.game_flags = set()  # For tracking story progress
		
		# ===== ROOM TRACKING =====
		self.visited_rooms = set()  # Track which rooms have been visited
		
		# ===== END SCREEN STATE =====
		self.end_screen_text_index = 0  # Current text in end sequence
		self.end_screen_texts = [
			"Resolution",
			"This Game is a demo game.",
			"Created by \n67050066 Jidapa Chindaprasert\n67050128 Thitima Nawpraya"
		]
		self.end_screen_fade_alpha = 0  # Text fade alpha (0 = invisible, 255 = visible)
		self.end_screen_fade_direction = 1  # 1 = fading in, -1 = fading out
		self.end_screen_timer = 0  # Timer for each text display duration
		self.end_screen_text_duration = 2500  # Milliseconds to show each text before fading out

		# ===== HOME PAGE =====
		self.home_page = HomePage()

		# ===== NETWORK & MULTIPLAYER =====
		self.network = None
		self.player_id = None
		self.player_role = None  # 'shion' or 'shione'
		self.other_player_pos = {'x': 0, 'y': 0}  # Other player's position
		self.other_player_sprite = None  # Other player's visual representation
		self.game_started = False  # Prevent starting game multiple times
		# Broadcast inactive dialogue state for a few frames after close (host reliability)
		self.dialog_end_broadcast_frames = 0
		# Other player's facing direction (from host)
		self.other_player_dir = 'front'
		
		# Queue for key events to send to join player
		self.pending_key_events = []

		# ===== SCENE & PLAYER REFERENCES =====
		self.scene: Optional[Scene] = None
		self.player_go: Optional[GameObject] = None
		self.player_transform: Optional[Transform] = None
		self.player_collider: Optional[BoxCollider] = None

		# ===== LOCAL SERVER PROCESS (HOST ONLY) =====
		self.server_process: Optional[subprocess.Popen] = None

	def _connect_to_server(self, server_host=None, return_to_state=None):
		"""
		Connect to multiplayer server.
		return_to_state: If connection fails, return to this state (default: HOME or JOIN_INPUT based on current state)
		"""
		print("[GAME] Connecting to server...")
		previous_state = self.state  # Save state before connecting
		self.state = GameConfig.STATE_CONNECTING
		
		# Use provided server host, or fall back to config/environment variable
		if server_host is None:
			server_host = GameConfig.SERVER_HOST
		
		# Create network client
		print(f"[GAME] Connecting to {server_host}:{GameConfig.SERVER_PORT}")
		self.network = NetworkClient(server_host, GameConfig.SERVER_PORT)
		
		# Connect (retry briefly to allow local server startup)
		connected = False
		for _ in range(15):  # ~3s total at 0.2s interval
			if self.network.connect():
				connected = True
				break
			time.sleep(0.2)

		if connected:
			self.player_id = self.network.player_id
			print(f"[GAME] Connected as Player {self.player_id}")
			self.state = GameConfig.STATE_WAITING
			
			# Set callbacks
			self.network.set_position_callback(self._on_position_update)
			self.network.set_ready_callback(self._on_server_ready)
			self.network.set_key_event_callback(self._on_key_event)
			
			return True
		else:
			print("[GAME] Failed to connect to server")
			# Restore to previous state or specified return state
			if return_to_state:
				self.state = return_to_state
			elif previous_state == GameConfig.STATE_JOIN_INPUT:
				self.state = GameConfig.STATE_JOIN_INPUT
			else:
				self.state = GameConfig.STATE_HOME
			return False

	def _start_local_server(self):
		"""Start local server.py in a background process (host only)."""
		if self.server_process and self.server_process.poll() is None:
			# Already running
			return
		try:
			server_path = os.path.join(os.path.dirname(__file__), 'server.py')
			print(f"[GAME] Starting local server: {server_path}")
			self.server_process = subprocess.Popen([sys.executable, server_path], cwd=os.path.dirname(server_path))
		except Exception as e:
			print(f"[GAME] Failed to start local server: {e}")
	
	def _get_local_ip(self):
		"""Get local IP address."""
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("8.8.8.8", 80))
			ip = s.getsockname()[0]
			s.close()
			return ip
		except Exception:
			return "localhost"
	
	def _on_server_ready(self):
		"""Called when server sends ready signal (both players connected)."""
		# This callback is called from network thread
		# The actual game start will be handled in update() loop
		print("[GAME] Received ready signal from server")
	
	def _on_position_update(self, message: dict):
		"""Called when we receive position update from other player."""
		pid = message.get('player_id')
		pos = message.get('position', {})
		
		if pid and pid != self.player_id:
			self.other_player_pos = pos
			# Save direction if provided
			if 'dir' in pos:
				self.other_player_dir = pos['dir']
	
	def _on_key_event(self, event_data: dict):
		"""Called when we receive key event from host (for join player)."""
		# Queue key events to process on the main thread in update() to avoid race conditions
		if self.player_role == 'shione':
			self.pending_key_events.append(event_data)
	
	def _start_game(self):
		"""Start the game from home screen."""
		# Prevent multiple starts
		if self.game_started:
			return
		
		self.game_started = True
		
		# Load starting scene
		self.load_scene(GameConfig.START_MAP_PATH, "initial_spawn")
		
		# Start opening cutscene
		self.dialog_system.start_conversation("intro room1")
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
		Ensures map is completely loaded before starting game logic.
		"""
		print(f"[GAME] Loading scene: {map_path} at spawn point: '{spawn_point_name}'")

		# Create new scene (this loads map, renders it, creates objects, and verifies loading)
		self.scene = Scene(self, map_path)
		
		# CRITICAL: Verify scene is fully loaded before proceeding
		if not self.scene.is_fully_loaded:
			raise RuntimeError(f"Scene {map_path} failed to load completely!")
		print(f"[GAME] Scene loading verified - ready for gameplay")
		
		# Find spawn point
		spawn_pos = self.scene.find_spawn_point(spawn_point_name)
		
		# CRITICAL: For yellow room, verify spawn point is on track before creating player
		if "yellow" in map_path.lower():
			if not self.scene.is_spawn_on_track(spawn_pos[0], spawn_pos[1]):
				print(f"[GAME] WARNING: Spawn point '{spawn_point_name}' at ({spawn_pos[0]}, {spawn_pos[1]}) is NOT on track!")
				print(f"[GAME] This may cause immediate exit_game. Checking track polygons...")
				print(f"[GAME] Track polygons loaded: {len(self.scene.track_polygons)}")
				# Try to find a nearby track position (fallback)
				# For now, just warn - spawn point should be correct in map editor
			else:
				print(f"[GAME] Spawn point '{spawn_point_name}' verified on track")
		
		# Create player at verified spawn point
		# CRITICAL: Store spawn position to verify after creation
		expected_spawn_x = spawn_pos[0]
		expected_spawn_y = spawn_pos[1]
		print(f"[GAME] Creating player at spawn position: ({expected_spawn_x}, {expected_spawn_y})")
		
		self.player_go = self.scene.create_player(expected_spawn_x, expected_spawn_y)
		
		# Cache player component references for quick access
		self.player_transform = self.player_go.get_component(Transform)
		self.player_collider = self.player_go.get_component(BoxCollider)
		
		# CRITICAL: Verify player was created at correct position BEFORE scene.start()
		if self.player_transform:
			actual_x = self.player_transform.rect.centerx
			actual_y = self.player_transform.rect.centery
			print(f"[GAME] Player created at position: ({actual_x}, {actual_y})")
			# For point objects, x,y should be the position directly
			# Transform uses centerx/centery, so we need to check if they match
			if abs(actual_x - expected_spawn_x) > 5 or abs(actual_y - expected_spawn_y) > 5:
				print(f"[GAME] ERROR: Player position mismatch! Expected ({expected_spawn_x}, {expected_spawn_y}), got ({actual_x}, {actual_y})")
				# Force set to correct position
				self.player_transform.rect.centerx = expected_spawn_x
				self.player_transform.rect.centery = expected_spawn_y
				print(f"[GAME] Corrected player position to spawn point")
			else:
				print(f"[GAME] Player position matches spawn point ✓")
		
		# Initialize all scene objects (after player is created and verified)
		self.scene.start()
		self.current_interaction_target = None
		
		# CRITICAL: Verify player position again after scene.start() to ensure it wasn't moved
		if self.player_transform:
			final_x = self.player_transform.rect.centerx
			final_y = self.player_transform.rect.centery
			if abs(final_x - expected_spawn_x) > 5 or abs(final_y - expected_spawn_y) > 5:
				print(f"[GAME] WARNING: Player position changed after scene.start()! Resetting to spawn.")
				self.player_transform.rect.centerx = expected_spawn_x
				self.player_transform.rect.centery = expected_spawn_y
				# Update collider too
				if self.player_collider:
					self.player_collider.rect.centerx = expected_spawn_x
					self.player_collider.rect.centery = expected_spawn_y
		
		# CRITICAL: Verify player is fully spawned and initialized
		self._verify_player_spawned()
		
		# Store spawn position for later verification
		self.last_spawn_position = (expected_spawn_x, expected_spawn_y)
		
		# Flag to track if intro dialog has been shown for this scene
		# This prevents track checking during intro dialog
		self.intro_dialog_shown = False

		# ===== TRACK ROOM VISITS =====
		# Track when player enters yellow, blue, or red rooms
		if "yellow" in map_path.lower():
			self.visited_rooms.add("yellow")
			print(f"[GAME] Visited yellow room. Total rooms: {len(self.visited_rooms)}")
		elif "blue" in map_path.lower():
			self.visited_rooms.add("blue")
			print(f"[GAME] Visited blue room. Total rooms: {len(self.visited_rooms)}")
		elif "red" in map_path.lower():
			self.visited_rooms.add("red")
			print(f"[GAME] Visited red room. Total rooms: {len(self.visited_rooms)}")

		# ===== SETUP PENDING INTRO (HOST ONLY) =====
		# Only trigger if this map has an intro and it hasn't been shown yet
		if self.player_role == 'shion':
			try:
				norm_map = os.path.normpath(map_path)
			except Exception:
				norm_map = map_path
			intro_script = self.map_intro_scripts.get(norm_map)
			if intro_script:
				flag_key = f"intro_shown:{norm_map}"
				if flag_key not in self.game_flags:
					self.pending_intro_script = intro_script

	def _verify_player_spawned(self) -> None:
		"""
		Verify that the player is fully spawned, initialized, and ready.
		This ensures player components exist and are properly set up before gameplay/dialog.
		"""
		if not self.player_go:
			raise RuntimeError("Player GameObject not created!")
		
		if not self.player_transform:
			raise RuntimeError("Player Transform component not found!")
		
		if not self.player_collider:
			raise RuntimeError("Player BoxCollider component not found!")
		
		# Verify player has valid position
		if not hasattr(self.player_transform, 'rect'):
			raise RuntimeError("Player Transform missing rect attribute!")
		
		if self.player_transform.rect is None:
			raise RuntimeError("Player Transform rect is None!")
		
		# CRITICAL: Verify player position is valid (not 0,0 unless that's intentional)
		player_x = self.player_transform.rect.centerx
		player_y = self.player_transform.rect.centery
		if player_x == 0 and player_y == 0:
			print(f"[GAME] WARNING: Player is at (0, 0) - this might indicate spawn point not found!")
		
		# For yellow room, verify player spawn position is on track
		if self.scene and "yellow" in self.scene.map_path.lower():
			if not self.scene.is_spawn_on_track(player_x, player_y):
				print(f"[GAME] ERROR: Player spawned at ({player_x}, {player_y}) is NOT on track!")
				print(f"[GAME] Track polygons available: {len(self.scene.track_polygons)}")
				print(f"[GAME] This will cause immediate exit_game!")
				# Try to find a valid track position nearby
				if self.scene.track_polygons:
					# Find first track polygon center as fallback
					for polygon in self.scene.track_polygons:
						if len(polygon) > 0:
							# Calculate polygon center
							px = sum(p[0] for p in polygon) / len(polygon)
							py = sum(p[1] for p in polygon) / len(polygon)
							print(f"[GAME] Attempting to move player to track center: ({px}, {py})")
							self.player_transform.rect.centerx = px
							self.player_transform.rect.centery = py
							self.player_collider.rect.centerx = px
							self.player_collider.rect.centery = py
							print(f"[GAME] Player moved to track position")
							break
				else:
					print(f"[GAME] No track polygons available - cannot fix position")
			else:
				print(f"[GAME] Player spawn verified on track at ({player_x}, {player_y}) ✓")
		
		# Verify PlayerController exists (for movement)
		player_controller = self.player_go.get_component(PlayerController)
		if not player_controller:
			raise RuntimeError("Player missing PlayerController component!")
		
		# Final position verification
		final_x = self.player_transform.rect.centerx
		final_y = self.player_transform.rect.centery
		print(f"[GAME] Player spawn verified - final position: ({final_x}, {final_y})")

	def handle_input(self) -> bool:
		"""
		Process all input events.
		Returns False if player wants to quit.
		"""
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return False
			
			# ===== HANDLE HOME PAGE INPUT =====
			if self.state == GameConfig.STATE_HOME:
				result = self.home_page.handle_input(event, GameConfig.STATE_HOME)
				if result == 'host':
					# Host: Set role as 'shion' and connect to server
					self.player_role = 'shion'
					print(f"[GAME] Role set to: {self.player_role}")
					# Try starting local server for host
					self._start_local_server()
					if self._connect_to_server():
						# Connection successful, will wait for other player
						pass
				elif result == 'join':
					# Switch to IP input page
					self.state = GameConfig.STATE_JOIN_INPUT
				continue
			
			# ===== HANDLE JOIN IP INPUT PAGE =====
			if self.state == GameConfig.STATE_JOIN_INPUT:
				result = self.home_page.handle_input(event, GameConfig.STATE_JOIN_INPUT)
				if result == 'connect':
					# Join: Set role as 'shione' and connect to server
					self.player_role = 'shione'
					print(f"[GAME] Role set to: {self.player_role}")
					# Get server IP from HomePage
					server_ip = self.home_page.get_server_ip()
					print(f"[GAME] Attempting to connect to server at {server_ip}")
					# Connect with return state set to JOIN_INPUT in case of failure
					connection_success = self._connect_to_server(server_ip, return_to_state=GameConfig.STATE_JOIN_INPUT)
					if connection_success:
						# Connection successful, should be in WAITING state now
						print(f"[GAME] Connection successful! Current state: {self.state}")
					else:
						# Connection failed, should already be back at JOIN_INPUT state
						print(f"[GAME] Connection failed. Current state: {self.state}")
				continue
			
			# ===== BLOCK INPUT DURING END SCREEN =====
			if self.state == GameConfig.STATE_END_SCREEN:
				continue  # Don't process input during end sequence
			
			# ===== BLOCK INPUT FOR JOIN PLAYER =====
			# IMPORTANT: Join player (shione) cannot use any input
			# They must use input from host (shion) through network
			# Only allow QUIT event for joining player
			if self.player_role == 'shione' and self.state != GameConfig.STATE_HOME:
				continue
			
			if event.type == pygame.KEYDOWN:
				
				# ===== WASD KEYS: CHOICE NAVIGATION (in dialogue mode) =====
				if self.state == GameConfig.STATE_DIALOGUE and self.dialog_system.is_showing_choices:
					# Host: Send key event to server
					if self.player_role == 'shion' and self.network and self.network.is_connected():
						key_name = self._key_to_name(event.key)
						if key_name:
							self.network.send_input_event({'type': 'KEYDOWN', 'key': key_name})
					
					if event.key == pygame.K_w or event.key == pygame.K_UP:
						self.dialog_system.move_choice_selection('up')
						continue
					elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
						self.dialog_system.move_choice_selection('down')
						continue
					elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
						self.dialog_system.move_choice_selection('left')
						continue
					elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
						self.dialog_system.move_choice_selection('right')
						continue
				
				# ===== E KEY: DIALOGUE & INTERACTION =====
				if event.key == pygame.K_e:
					
					# Host: Send key event to server immediately BEFORE processing
					# This ensures join player advances dialogue at the same time
					if self.player_role == 'shion' and self.network and self.network.is_connected():
						key_name = self._key_to_name(event.key)
						if key_name:
							self.network.send_input_event({'type': 'KEYDOWN', 'key': key_name})
					
					# --- During dialogue: handle choices or advance text ---
					if self.state == GameConfig.STATE_DIALOGUE:
						# Check if showing choices
						if self.dialog_system.is_showing_choices:
							# E key confirms choice
							triggered_event = self.dialog_system.select_choice()
							if triggered_event:
								self.handle_dialogue_event(triggered_event)
						# Check if dialogue ended after choice
						if not self.dialog_system.is_active:
							if self.state == GameConfig.STATE_DIALOGUE:
								# Check if there's a pending teleport (from teleport with dialog)
								if self.pending_teleport_map and self.pending_teleport_spawn:
									# Teleport automatically after dialog ends
									self.state = GameConfig.STATE_FADING_OUT
									self.fade_alpha = 0
									self.teleport_target_map = self.pending_teleport_map
									self.teleport_target_spawn = self.pending_teleport_spawn
									# Send teleport data to server for join player
									if self.network and self.network.is_connected() and self.player_role == 'shion':
										self.network.send_teleport(self.teleport_target_map, self.teleport_target_spawn)
									# Clear pending teleport
									self.pending_teleport_map = None
									self.pending_teleport_spawn = None
								else:
									# Normal dialog end: return to gameplay
									self.state = GameConfig.STATE_PLAYING
									# Mark intro dialog as shown (if it was an intro)
									self.intro_dialog_shown = True
								# Notify join player that dialogue ended
								if self.network and self.network.is_connected() and self.player_role == 'shion':
									dialog_state = {
										'is_active': False,
										'script_id': None,
										'line_index': -1,
										'is_typing': False
									}
									self.network.send_dialogue_state(dialog_state)
									self.dialog_end_broadcast_frames = 30
						else:
							# Regular dialogue: advance text
							triggered_event = self.dialog_system.next_line()
							
							# Handle any event triggered by dialogue
							if triggered_event:
								self.handle_dialogue_event(triggered_event)
							
							# Check if dialogue ended
							if not self.dialog_system.is_active:
								if self.state == GameConfig.STATE_DIALOGUE:
									# Check if there's a pending teleport (from teleport with dialog)
									if self.pending_teleport_map and self.pending_teleport_spawn:
										# Teleport automatically after dialog ends
										self.state = GameConfig.STATE_FADING_OUT
										self.fade_alpha = 0
										self.teleport_target_map = self.pending_teleport_map
										self.teleport_target_spawn = self.pending_teleport_spawn
										# Send teleport data to server for join player
										if self.network and self.network.is_connected() and self.player_role == 'shion':
											self.network.send_teleport(self.teleport_target_map, self.teleport_target_spawn)
										# Clear pending teleport
										self.pending_teleport_map = None
										self.pending_teleport_spawn = None
									else:
										# Normal dialog end: return to gameplay
										self.state = GameConfig.STATE_PLAYING
										# Mark intro dialog as shown (if it was an intro)
										self.intro_dialog_shown = True
									# Notify join player that dialogue ended
									if self.network and self.network.is_connected() and self.player_role == 'shion':
										dialog_state = {
											'is_active': False,
											'script_id': None,
											'line_index': -1,
											'is_typing': False
										}
										self.network.send_dialogue_state(dialog_state)
										# Keep sending inactive state for a short window in case of packet loss
										self.dialog_end_broadcast_frames = 30  # ~0.5s at 60 FPS

					# --- During gameplay: interact with objects ---
					elif self.state == GameConfig.STATE_PLAYING:
						if self.current_interaction_target:
							game_object = self.current_interaction_target.game_object

							# Priority 1: Teleport (scene transition)
							teleport_comp = game_object.get_component(Teleport)
							if teleport_comp:
								# Check if dialog script exists for this teleport object
								script_id = game_object.name
								if script_id in self.dialog_system.scripts:
									# Dialog exists: show dialog first, then teleport after
									self.dialog_system.start_conversation(script_id)
									if self.dialog_system.is_active:
										# Store teleport info for after dialog ends
										self.pending_teleport_map = teleport_comp.target_map
										self.pending_teleport_spawn = teleport_comp.target_spawn_point
										self.state = GameConfig.STATE_DIALOGUE
								else:
									# No dialog: teleport immediately
									self.state = GameConfig.STATE_FADING_OUT
									self.fade_alpha = 0
									self.teleport_target_map = teleport_comp.target_map
									self.teleport_target_spawn = teleport_comp.target_spawn_point
									# Send teleport data to server for join player
									if self.network and self.network.is_connected() and self.player_role == 'shion':
										self.network.send_teleport(self.teleport_target_map, self.teleport_target_spawn)
								return True

							# Next: Generic interactable (start dialogue)
							interact_comp = game_object.get_component(Interactable)
							if interact_comp:
								# Special handling for "end" object
								if interact_comp.name == "end":
									# Check if all three rooms have been visited
									if len(self.visited_rooms) >= 3 and "yellow" in self.visited_rooms and "blue" in self.visited_rooms and "red" in self.visited_rooms:
										# All rooms visited - trigger end sequence
										self.state = GameConfig.STATE_END_SCREEN
										self.end_screen_text_index = 0
										self.end_screen_fade_alpha = 0
										self.end_screen_fade_direction = 1
										self.end_screen_timer = 0
										self.fade_alpha = 255  # Start with black screen
										# Send end screen state to join player
										if self.network and self.network.is_connected() and self.player_role == 'shion':
											end_screen_state = {
												'active': True,
												'text_index': 0,
												'fade_alpha': 0,
												'fade_direction': 1,
												'timer': 0
											}
											self.network.send_end_screen_state(end_screen_state)
									else:
										# Not all rooms visited - show locked door dialog
										self.dialog_system.start_conversation("door_locked")
										if self.dialog_system.is_active:
											self.state = GameConfig.STATE_DIALOGUE
								else:
									# Regular interactable
									self.dialog_system.start_conversation(interact_comp.name)
									if self.dialog_system.is_active:
										self.state = GameConfig.STATE_DIALOGUE
		
		return True
	
	def _key_to_name(self, key_code):
		"""Convert pygame key code to string name."""
		key_map = {
			pygame.K_w: 'w',
			pygame.K_a: 'a',
			pygame.K_s: 's',
			pygame.K_d: 'd',
			pygame.K_e: 'e',
			pygame.K_UP: 'w',
			pygame.K_LEFT: 'a',
			pygame.K_DOWN: 's',
			pygame.K_RIGHT: 'd',
		}
		return key_map.get(key_code)
	
	def _process_received_key_event(self, event_data: dict):
		"""Process received key event from host (for join player)."""
		if event_data.get('type') == 'KEYDOWN':
			key_name = event_data.get('key')
			
			# Handle WASD for choice navigation (join player)
			if self.state == GameConfig.STATE_DIALOGUE and self.dialog_system.is_showing_choices:
				if key_name in ('w', 's', 'a', 'd'):
					dir_map = {'w': 'up', 's': 'down', 'a': 'left', 'd': 'right'}
					self.dialog_system.move_choice_selection(dir_map[key_name])
					return
			
			if key_name == 'e':
				# Process E key event from host - must be synchronized
				# --- During dialogue: handle choices or advance text ---
				if self.state == GameConfig.STATE_DIALOGUE:
					# Check if showing choices
					if self.dialog_system.is_showing_choices:
						# E key confirms choice
						triggered_event = self.dialog_system.select_choice()
						if triggered_event:
							self.handle_dialogue_event(triggered_event)
						# Check if dialogue ended after choice
						if not self.dialog_system.is_active:
							if self.state == GameConfig.STATE_DIALOGUE:
								# Check if there's a pending teleport (from teleport with dialog)
								if self.pending_teleport_map and self.pending_teleport_spawn:
									# Teleport automatically after dialog ends
									self.state = GameConfig.STATE_FADING_OUT
									self.fade_alpha = 0
									self.teleport_target_map = self.pending_teleport_map
									self.teleport_target_spawn = self.pending_teleport_spawn
									# Clear pending teleport
									self.pending_teleport_map = None
									self.pending_teleport_spawn = None
								else:
									# Normal dialog end: return to gameplay
									self.state = GameConfig.STATE_PLAYING
									# Mark intro dialog as shown (for join player)
									self.intro_dialog_shown = True
					else:
						# Advance dialogue immediately when host presses E
						triggered_event = self.dialog_system.next_line()
						
						# Handle any event triggered by dialogue
						if triggered_event:
							self.handle_dialogue_event(triggered_event)
						
						# Check if dialogue ended
						if not self.dialog_system.is_active:
							if self.state == GameConfig.STATE_DIALOGUE:
								# Check if there's a pending teleport (from teleport with dialog)
								if self.pending_teleport_map and self.pending_teleport_spawn:
									# Teleport automatically after dialog ends
									self.state = GameConfig.STATE_FADING_OUT
									self.fade_alpha = 0
									self.teleport_target_map = self.pending_teleport_map
									self.teleport_target_spawn = self.pending_teleport_spawn
									# Clear pending teleport
									self.pending_teleport_map = None
									self.pending_teleport_spawn = None
								else:
									# Normal dialog end: return to gameplay
									self.state = GameConfig.STATE_PLAYING
									# Mark intro dialog as shown (for join player)
									self.intro_dialog_shown = True

				# --- During gameplay: interact with objects ---
				elif self.state == GameConfig.STATE_PLAYING:
					if self.current_interaction_target:
						game_object = self.current_interaction_target.game_object

						# Priority 1: Teleport (scene transition)
						teleport_comp = game_object.get_component(Teleport)
						if teleport_comp:
							# Join player doesn't initiate teleports - they follow host
							# But if this happens, it means they're in sync, so allow it
							# (Host handles teleport initiation)
							pass

						# Next: Generic interactable (start dialogue)
						interact_comp = game_object.get_component(Interactable)
						if interact_comp:
							# Special handling for "end" object (join player follows host)
							if interact_comp.name == "end":
								# Join player doesn't initiate end sequence - follows host
								pass
							else:
								# Regular interactable
								self.dialog_system.start_conversation(interact_comp.name)
								if self.dialog_system.is_active:
									self.state = GameConfig.STATE_DIALOGUE
	
	def handle_dialogue_event(self, event: str):
		"""
		Handle custom events triggered by dialogue lines.
		Used to trigger gameplay changes from story moments.
		"""
		print(f"[Game Event Triggered]: {event}")
		
		if event == "select_book1":
			self.game_flags.add("select_book1")
		elif event == "select_book2":
			self.game_flags.add("select_book2")
		elif event == "select_book3":
			self.game_flags.add("select_book3")
		elif event == "select_brown_eye":
			print("select_brown_eye")
		# elif event == "select_red_eye":
		# 	kill_end()
		# elif event == "select_yellow_eye":
		# 	kill_end()
		elif event == "select_purple_eye":
			self.game_flags.add("select_purple_eye")
		# elif event == "select_cyan_eye":
		# 	kill_end()
		# elif event == "select_blue_eye":
		# 	kill_end()
		# elif event == "select_greee_eye":
		# 	kill_end()
		elif event == "play_dandelion_effect":
			# Placeholder for visual effect
			print("--- (Play yellow dandelion particle effect) ---")
			
		elif event == "play_blue_effect":
			# Placeholder for visual effect
			print("--- (Play blue sky visual effect) ---")
		elif event == "exit_game":
			# Exit game for both players
			print("[GAME] Exit game event triggered - sending command to server")
			if self.network and self.network.is_connected():
				self.network.send_exit_game()
			# Set flag to exit on next update
			self.should_exit = True
			
		# Add more events here as needed
		# elif event == "unlock_door":
		#     self.game_flags.add("door_unlocked")
	
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

	def update(self, dt_ms: int) -> None:
		"""
		Update game state every frame.
		dt_ms: Delta time in milliseconds (for frame-independent timing).
		"""
		
		# ===== CHECK FOR EXIT GAME COMMAND =====
		# Check if we received exit game command from server (for join player)
		if self.network and self.network.is_connected():
			if hasattr(self.network, 'received_exit_game') and self.network.received_exit_game:
				print("[GAME] Received exit game command from server - exiting")
				self.should_exit = True
				self.network.received_exit_game = False  # Reset flag
		
		# Check if exit was requested locally (from dialogue event)
		if hasattr(self, 'should_exit') and self.should_exit:
			# Exit gracefully
			print("[GAME] Exiting game...")
			if self.network:
				self.network.disconnect()
			# Signal to main loop to exit
			sys.exit(0)
		
		# ===== STATE: HOME (Do nothing, just wait for button clicks) =====
		if self.state == GameConfig.STATE_HOME:
			return
		
		# ===== STATE: JOIN_INPUT (Do nothing, just wait for input) =====
		if self.state == GameConfig.STATE_JOIN_INPUT:
			return
		
		# ===== STATE: WAITING =====
		# Check if server is ready and start game
		if self.state == GameConfig.STATE_WAITING:
			if self.network and self.network.is_ready():
				print("[GAME] Server ready! Starting game...")
				self._start_game()
			return
		
		# ===== PROCESS RECEIVED TELEPORT DATA (JOIN PLAYER) =====
		# Handle received teleport data from host (MUST be before state checks to ensure sync)
		# This allows teleport to work even during dialogue or other states
		if self.player_role == 'shione' and self.network and self.network.is_connected():
			teleport_data = self.network.get_received_teleport_data()
			if teleport_data and teleport_data.get('target_map') and teleport_data.get('target_spawn'):
				# Always allow teleport, even if we're in dialogue (teleport takes priority)
				self.state = GameConfig.STATE_FADING_OUT
				self.fade_alpha = 0
				self.teleport_target_map = teleport_data.get('target_map')
				self.teleport_target_spawn = teleport_data.get('target_spawn')
				# Clear any pending teleport that might have been set
				self.pending_teleport_map = None
				self.pending_teleport_spawn = None
				# End dialogue if active (teleporting takes priority)
				if self.dialog_system.is_active:
					self.dialog_system.is_active = False
		
		# ===== PROCESS RECEIVED END SCREEN STATE (JOIN PLAYER) =====
		# Handle received end screen state from host (MUST be before state checks to ensure sync)
		# Continuously sync during end screen state
		if self.player_role == 'shione' and self.network and self.network.is_connected():
			end_screen_state = self.network.get_received_end_screen_state()
			if end_screen_state and end_screen_state.get('active'):
				# Sync end screen state for join player (continuous sync during end screen)
				if self.state != GameConfig.STATE_END_SCREEN:
					# First time entering end screen
					self.fade_alpha = 255  # Start with black screen
				self.state = GameConfig.STATE_END_SCREEN
				self.end_screen_text_index = end_screen_state.get('text_index', self.end_screen_text_index)
				self.end_screen_fade_alpha = end_screen_state.get('fade_alpha', self.end_screen_fade_alpha)
				self.end_screen_fade_direction = end_screen_state.get('fade_direction', self.end_screen_fade_direction)
				self.end_screen_timer = end_screen_state.get('timer', self.end_screen_timer)
		
		# ===== STATE: FADING OUT (Before teleport) =====
		if self.state == GameConfig.STATE_FADING_OUT:
			self.fade_alpha += GameConfig.FADE_SPEED
			if self.fade_alpha >= 255:
				self.fade_alpha = 255
				# Screen is now black - do the actual teleport
				self.load_scene(self.teleport_target_map, self.teleport_target_spawn)
				self.state = GameConfig.STATE_FADING_IN
			return

		# ===== PROCESS QUEUED KEY EVENTS (JOIN PLAYER) =====
		# Handle received key events on the main thread to avoid race conditions
		# Note: Teleport check must happen before this to ensure proper sync
		if self.player_role == 'shione' and self.pending_key_events:
			try:
				for ev in list(self.pending_key_events):
					self._process_received_key_event(ev)
			finally:
				self.pending_key_events.clear()

		# ===== FADE IN/OUT VISUAL EFFECT =====
		# Don't process regular fade during end screen (end screen handles its own fade)
		if self.state != GameConfig.STATE_END_SCREEN and self.fade_alpha > 0:
			self.fade_alpha -= GameConfig.FADE_SPEED
			if self.fade_alpha <= 0:
				self.fade_alpha = 0
				# Fade-in complete
				if self.state == GameConfig.STATE_FADING_IN:
					self.teleport_target_map = None
					
					# CRITICAL: Verify player is fully spawned before starting intro dialog
					# This ensures player exists, is positioned, and ready before any dialog
					if self.player_go and self.player_transform:
						try:
							self._verify_player_spawned()
							print(f"[GAME] Player verified before intro dialog - position: ({self.player_transform.rect.centerx}, {self.player_transform.rect.centery})")
						except Exception as e:
							print(f"[GAME] ERROR: Player verification failed: {e}")
							# Don't start dialog if player isn't ready
							print(f"[GAME] Skipping intro dialog until player is ready")
							# Enter playing state without dialog as fallback
							self.state = GameConfig.STATE_PLAYING
							self.intro_dialog_shown = True
							return
					
					# After fade-in and player verification, start pending intro if any (HOST ONLY)
					# IMPORTANT: Start intro dialog BEFORE entering PLAYING state
					# This prevents track checking from triggering during dialog
					if self.player_role == 'shion' and self.pending_intro_script:
						print(f"[GAME] Starting intro dialog '{self.pending_intro_script}' - player is ready")
						self.dialog_system.start_conversation(self.pending_intro_script)
						if self.dialog_system.is_active:
							self.state = GameConfig.STATE_DIALOGUE
							self.intro_dialog_shown = False  # Will be set to True when dialog ends
							# Mark flag so it only plays once per map
							try:
								current_map = self.scene.map_path if self.scene else None
								if current_map:
									norm_map = os.path.normpath(current_map)
									self.game_flags.add(f"intro_shown:{norm_map}")
							except Exception:
								pass
						# Clear pending
						self.pending_intro_script = None
					else:
						# No intro dialog - safe to enter playing state
						self.state = GameConfig.STATE_PLAYING
						self.intro_dialog_shown = True

		# ===== UPDATE DIALOGUE SYSTEM =====
		# Typewriter effect needs to run even during dialogue state
		self.dialog_system.update(dt_ms)
		
		# Sync dialogue state between host and join
		if self.network and self.network.is_connected():
			if self.player_role == 'shion':
				# Host: Send end screen state to join player when in end screen
				if self.state == GameConfig.STATE_END_SCREEN:
					end_screen_state = {
						'active': True,
						'text_index': self.end_screen_text_index,
						'fade_alpha': self.end_screen_fade_alpha,
						'fade_direction': self.end_screen_fade_direction,
						'timer': self.end_screen_timer
					}
					self.network.send_end_screen_state(end_screen_state)
				# Host: Send dialogue state to join player every frame when active
				# Only send if state changed to reduce lag
				elif self.dialog_system.is_active:
					dialog_state = {
						'is_active': True,
						'script_id': getattr(self.dialog_system, 'active_script_id', None),
						'line_index': getattr(self.dialog_system, 'current_line_index', -1),
						'is_typing': getattr(self.dialog_system, 'is_typing', False)
					}
					self.network.send_dialogue_state(dialog_state)
				# After dialogue closes, continue sending inactive state briefly for reliability
				elif self.dialog_end_broadcast_frames > 0:
					dialog_state = {
						'is_active': False,
						'script_id': None,
						'line_index': -1,
						'is_typing': False
					}
					self.network.send_dialogue_state(dialog_state)
					self.dialog_end_broadcast_frames -= 1
			elif self.player_role == 'shione':
				# Join: Sync dialogue state from host
				received_state = self.network.get_received_dialogue_state()
				if received_state:
					# Sync dialogue active state first
					if received_state.get('is_active') != self.dialog_system.is_active:
						if received_state.get('is_active'):
							# Start dialogue
							script_id = received_state.get('script_id')
							if script_id and not self.dialog_system.is_active:
								self.dialog_system.start_conversation(script_id)
								self.state = GameConfig.STATE_DIALOGUE
						else:
							# End dialogue
							if self.dialog_system.is_active:
								self.dialog_system.is_active = False
								if self.state == GameConfig.STATE_DIALOGUE:
									self.state = GameConfig.STATE_PLAYING
									# Mark intro dialog as shown (for join player, synced from host)
									self.intro_dialog_shown = True
					
					# Check if script_id changed (e.g., from goto_script in choice)
					# Do this AFTER checking active state to ensure dialogue is active
					if received_state.get('is_active') and self.dialog_system.is_active:
						received_script_id = received_state.get('script_id')
						current_script_id = getattr(self.dialog_system, 'active_script_id', None)
						if received_script_id and received_script_id != current_script_id:
							# Script changed - reload it (this happens when goto_script is used)
							self.dialog_system.active_script = self.dialog_system.scripts.get(received_script_id, self.dialog_system.scripts["default"])
							self.dialog_system.active_script_id = received_script_id
							# Set line index to one before target (since _next_line_internal increments it)
							target_line = received_state.get('line_index', -1)
							self.dialog_system.current_line_index = target_line - 1
							# Load the current line (this will increment to target_line and load it)
							self.dialog_system._next_line_internal()
					
					# Sync line index if dialogue is active and in same script (only as backup)
					# Key events handle real-time sync, this just catches up if missed
					# Don't sync if we're in different states to prevent lag/leading
					if received_state.get('is_active') and self.dialog_system.is_active and self.state == GameConfig.STATE_DIALOGUE:
						received_script_id = received_state.get('script_id')
						current_script_id = getattr(self.dialog_system, 'active_script_id', None)
						# Only sync line if we're in the same script
						if received_script_id == current_script_id:
							target_line = received_state.get('line_index', -1)
							current_line = getattr(self.dialog_system, 'current_line_index', -1)
							# Only sync if we're significantly behind (more than 2 lines to reduce leading)
							# This handles network lag but key events should handle real-time sync
							if target_line > current_line + 2:
								# Advance to catch up (but don't skip too many lines)
								skip_count = min(target_line - current_line - 2, 2)  # Max 2 lines catch up
								for _ in range(skip_count):
									if self.dialog_system.is_active and self.state == GameConfig.STATE_DIALOGUE:
										self.dialog_system.next_line()
									else:
										break

		# ===== STATE: PLAYING (Normal gameplay) =====
		if self.state == GameConfig.STATE_PLAYING:
			if not self.scene or not self.player_transform:
				return

			# Update all game objects
			self.scene.update()
			
			# Send position to server (host only sends position)
			# Join player receives position from host and follows it directly
			if self.network and self.network.is_connected():
				# Host sends position, join receives it and follows
				if self.player_role == 'shion':
					# Include facing direction from PlayerController
					pc = self.player_go.get_component(PlayerController)
					dir_val = getattr(pc, 'direction', None) if pc else None
					self.network.send_position(
						self.player_transform.rect.centerx,
						self.player_transform.rect.centery,
						dir_val
					)
				# Join player doesn't send position - they use host's position
				# CRITICAL: Only sync position if scene is fully ready and intro dialog shown
				elif self.player_role == 'shione':
					# Only sync position if scene is ready and intro dialog has been shown
					# This prevents overriding spawn position before scene is fully loaded
					if (self.scene and self.scene.is_fully_loaded and 
						getattr(self, 'intro_dialog_shown', False)):
						# Follow host's latest position so local collisions/teleports match
						try:
							hx = int(self.other_player_pos.get('x', self.player_transform.rect.centerx))
							hy = int(self.other_player_pos.get('y', self.player_transform.rect.centery))
							
							# CRITICAL: Verify host position is valid before applying
							# If host hasn't loaded scene yet, position might be (0,0) or invalid
							if hx != 0 or hy != 0:  # Avoid using (0,0) which might be uninitialized
								# Only update if we have a valid spawn position to compare
								if hasattr(self, 'last_spawn_position'):
									spawn_x, spawn_y = self.last_spawn_position
									# If host position is very different from spawn, wait for valid position
									if abs(hx - spawn_x) < 5000 and abs(hy - spawn_y) < 5000:
										self.player_transform.rect.centerx = hx
										self.player_transform.rect.centery = hy
								else:
									# No spawn position stored, use host position directly
									self.player_transform.rect.centerx = hx
									self.player_transform.rect.centery = hy
						except Exception as e:
							print(f"[GAME] Error syncing join player position: {e}")
							# Don't update position on error
							pass
					else:
						# Scene not ready or intro not shown - keep spawn position
						# Don't sync from host yet
						pass
			
			# Update camera to follow player
			self.camera.update(self.player_transform.rect.center)
			
			# Check for nearby interactable objects
			collided = pygame.sprite.spritecollide(
				self.player_collider,
				self.scene.interactables,
				False  # Don't remove from group
			)
			self.current_interaction_target = collided[0] if collided else None
			
			# ===== TRACK SYSTEM (Yellow Room) =====
			# Check if player is on track (only for yellow room)
			# CRITICAL: Only check track if:
			# 1. Scene is fully loaded
			# 2. Intro dialog has been shown (prevents false triggers during spawn)
			# 3. Track polygons exist
			if (self.scene and self.scene.is_fully_loaded and 
				self.scene.map_path and "yellow" in self.scene.map_path.lower() and
				getattr(self, 'intro_dialog_shown', True) and  # Default True for rooms without intro
				self.scene.track_polygons):
				player_x = self.player_transform.rect.centerx
				player_y = self.player_transform.rect.centery
				
				# Check if player is inside any track polygon
				is_on_track = False
				for polygon in self.scene.track_polygons:
					if self._point_in_polygon(player_x, player_y, polygon):
						is_on_track = True
						break
				
				# If player is not on track, trigger exit game
				if not is_on_track:
					print("[GAME] Player left the track! Triggering exit game...")
					self.handle_dialogue_event("exit_game")
		
		# ===== STATE: END_SCREEN (End credits sequence) =====
		if self.state == GameConfig.STATE_END_SCREEN:
			# First fade out the screen to black
			if self.fade_alpha < 255:
				self.fade_alpha += GameConfig.FADE_SPEED * 2  # Faster fade to black
				if self.fade_alpha >= 255:
					self.fade_alpha = 255
			else:
				# Screen is black, handle text fade in/out
				fade_speed = 4  # Fade speed for text
				
				# Update text fade alpha
				if self.end_screen_fade_direction == 1:
					# Fading in
					self.end_screen_fade_alpha += fade_speed
					if self.end_screen_fade_alpha >= 255:
						self.end_screen_fade_alpha = 255
						# Wait a bit before starting fade out
						if self.end_screen_timer < self.end_screen_text_duration:
							self.end_screen_timer += dt_ms
						else:
							# Start fading out
							self.end_screen_fade_direction = -1
							self.end_screen_timer = 0
				else:
					# Fading out
					self.end_screen_fade_alpha -= fade_speed
					if self.end_screen_fade_alpha <= 0:
						self.end_screen_fade_alpha = 0
						# Move to next text
						self.end_screen_text_index += 1
						if self.end_screen_text_index >= len(self.end_screen_texts):
							# All texts shown - exit game
							print("[GAME] End sequence complete - exiting game...")
							if self.network:
								self.network.disconnect()
							sys.exit(0)
						else:
							# Reset for next text
							self.end_screen_fade_direction = 1
							self.end_screen_timer = 0
			return

	def draw(self) -> None:
		"""Render the current frame."""
		
		# ===== STATE: HOME =====
		if self.state == GameConfig.STATE_HOME:
			self.home_page.draw(self.screen, GameConfig.STATE_HOME)
			pygame.display.flip()
			return
		
		# ===== STATE: JOIN_INPUT =====
		if self.state == GameConfig.STATE_JOIN_INPUT:
			self.home_page.draw(self.screen, GameConfig.STATE_JOIN_INPUT)
			pygame.display.flip()
			return
		
		# ===== STATE: CONNECTING =====
		if self.state == GameConfig.STATE_CONNECTING:
			self.screen.fill((20, 10, 30))
			font = pygame.font.Font(None, 48)
			text = font.render("Connecting to server...", True, (255, 255, 255))
			text_rect = text.get_rect(center=(GameConfig.SCREEN_WIDTH//2, GameConfig.SCREEN_HEIGHT//2))
			self.screen.blit(text, text_rect)
			pygame.display.flip()
			return
		
		# ===== STATE: WAITING =====
		if self.state == GameConfig.STATE_WAITING:
			self.screen.fill((20, 10, 30))
			font = pygame.font.Font(None, 48)
			role_font = pygame.font.Font(None, 36)
			info_font = pygame.font.Font(None, 32)
			
			# Show role if set
			if self.player_role:
				role_text = role_font.render(f"Role: {self.player_role.upper()}", True, (200, 200, 255))
				role_rect = role_text.get_rect(center=(GameConfig.SCREEN_WIDTH//2, GameConfig.SCREEN_HEIGHT//2 - 120))
				self.screen.blit(role_text, role_rect)
			
			player_text = font.render(f"You are Player {self.player_id}", True, (255, 255, 255))
			wait_text = font.render("Waiting for other player...", True, (200, 200, 200))
			
			player_rect = player_text.get_rect(center=(GameConfig.SCREEN_WIDTH//2, GameConfig.SCREEN_HEIGHT//2 - 40))
			wait_rect = wait_text.get_rect(center=(GameConfig.SCREEN_WIDTH//2, GameConfig.SCREEN_HEIGHT//2 + 20))
			
			self.screen.blit(player_text, player_rect)
			self.screen.blit(wait_text, wait_rect)
			
			# Show server IP for Host player
			if self.player_role == 'shion':
				server_ip = self._get_local_ip()
				ip_info_text = f"Server IP: {server_ip}"
				ip_info_surface = info_font.render(ip_info_text, True, (200, 255, 200))
				ip_info_rect = ip_info_surface.get_rect(center=(GameConfig.SCREEN_WIDTH//2, GameConfig.SCREEN_HEIGHT//2 + 80))
				self.screen.blit(ip_info_surface, ip_info_rect)
				
				# Hint text
				hint_text = "Tell this IP to the other player"
				hint_surface = role_font.render(hint_text, True, (150, 200, 150))
				hint_rect = hint_surface.get_rect(center=(GameConfig.SCREEN_WIDTH//2, GameConfig.SCREEN_HEIGHT//2 + 120))
				self.screen.blit(hint_surface, hint_rect)
			
			pygame.display.flip()
			return
		
		# ===== STATE: END_SCREEN (End credits sequence) =====
		if self.state == GameConfig.STATE_END_SCREEN:
			# Fill screen with black
			self.screen.fill((0, 0, 0))
			
			# Only show text if screen is fully black
			if self.fade_alpha >= 255 and self.end_screen_text_index < len(self.end_screen_texts):
				# Get current text
				current_text = self.end_screen_texts[self.end_screen_text_index]
				
				# Render text (handle multi-line with \n)
				font = pygame.font.Font(None, 64)
				
				# Split text by newlines
				lines = current_text.split('\n')
				
				# Render each line
				line_surfaces = []
				total_height = 0
				for line in lines:
					line_surface = font.render(line, True, (255, 255, 255))
					line_surfaces.append(line_surface)
					total_height += line_surface.get_height() + 10  # 10px spacing between lines
				
				# Calculate starting y position (centered)
				start_y = (GameConfig.SCREEN_HEIGHT // 2) - (total_height // 2)
				
				# Draw each line
				current_y = start_y
				for line_surface in line_surfaces:
					line_rect = line_surface.get_rect(center=(GameConfig.SCREEN_WIDTH//2, current_y))
					# Apply fade alpha to text
					line_surface.set_alpha(self.end_screen_fade_alpha)
					self.screen.blit(line_surface, line_rect)
					current_y += line_surface.get_height() + 10  # Move to next line with spacing
			
			pygame.display.flip()
			return
		
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
		
		# ===== 3. DRAW SHION DARK OVERLAY =====
		# Only the host (shion) sees a darker map view during gameplay/dialogue
		# Exception: Hide overlay when "white" dialogue is active in yellow room
		should_hide_overlay = False
		if self.scene and self.scene.map_path and "yellow" in self.scene.map_path.lower():
			if self.state == GameConfig.STATE_DIALOGUE and self.dialog_system.is_active:
				active_script_id = getattr(self.dialog_system, 'active_script_id', None)
				if active_script_id == "white":
					should_hide_overlay = True
		
		if self.player_role == 'shion' and self.state in (GameConfig.STATE_PLAYING, GameConfig.STATE_DIALOGUE) and not should_hide_overlay:
			# Rebuild overlay each frame: dark fill + transparent circle at player
			alpha_value = 240  # user-tuned darkness
			self.shion_dark_surface.fill((0, 0, 0, alpha_value))
			# Player is rendered centered on screen in this project; cut a hole there
			player_screen_center = (GameConfig.SCREEN_WIDTH // 2, GameConfig.SCREEN_HEIGHT // 2 - 20)
			spot_radius = 80
			pygame.draw.circle(self.shion_dark_surface, (0, 0, 0, 0), player_screen_center, spot_radius)
			self.screen.blit(self.shion_dark_surface, (0, 0))
		
		# ===== 4. DRAW FADE OVERLAY =====
		if self.fade_alpha > 0:
			self.fade_surface.set_alpha(self.fade_alpha)
			self.screen.blit(self.fade_surface, (0, 0))

		# ===== 4.5 DRAW DIALOG OVERLAY (TOPMOST) =====
		if self.dialog_system.is_active:
			self.dialog_system.draw(self.screen)

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
		# Stop local server if we started one
		try:
			if self.server_process and self.server_process.poll() is None:
				print("[GAME] Terminating local server...")
				self.server_process.terminate()
				# Give it a moment to exit
				for _ in range(10):
					if self.server_process.poll() is not None:
						break
					time.sleep(0.1)
				if self.server_process.poll() is None:
					self.server_process.kill()
		except Exception:
			pass
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