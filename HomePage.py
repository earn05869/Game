import pygame
import socket
from simple_2d_game import GameConfig


class HomePage:
	"""
	Home screen with Host and Join buttons.
	Simple pygame-based UI that works with the existing game system.
	"""
	
	def __init__(self):
		# Load images
		self.bg = None
		self.char_logo = None
		self.logo = None
		self._load_images()
		
		# Button setup
		self.font = pygame.font.Font(None, 48)
		self.button_font = pygame.font.Font(None, 32)
		self.input_font = pygame.font.Font(None, 36)
		self.buttons = []
		self._create_buttons()
		
		# Mouse tracking
		self.mouse_pos = (0, 0)
		
		# IP input field (for Join player)
		self.ip_input_text = ""
		self.ip_input_active = False
		self.ip_input_rect = pygame.Rect(
			GameConfig.SCREEN_WIDTH // 2 - 200,
			GameConfig.SCREEN_HEIGHT // 2,
			400, 50
		)
		
		# Connect button (for Join IP input page)
		self.connect_button_rect = pygame.Rect(
			GameConfig.SCREEN_WIDTH // 2 - 150,
			GameConfig.SCREEN_HEIGHT // 2 + 80,
			300, 60
		)
		self.connect_button_hover = False
		
		# Get default IP (localhost)
		self.server_ip = "localhost"
		
	def _load_images(self):
		"""Load all images for the home screen."""
		try:
			self.bg = pygame.image.load(GameConfig.HOMEBG).convert()
		except Exception as e:
			print(f"Warning: Could not load background: {e}")
			self.bg = pygame.Surface((GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT))
			self.bg.fill((20, 10, 30))
		
		try:
			self.char_logo = pygame.image.load(GameConfig.CHAR_LOGO).convert_alpha()
			# Scale down logo
			size = self.char_logo.get_size()
			self.char_logo = pygame.transform.scale(self.char_logo, (size[0]//2, size[1]//2))
		except Exception as e:
			print(f"Warning: Could not load character logo: {e}")
			self.char_logo = None
			
		try:
			self.logo = pygame.image.load(GameConfig.LOGO).convert_alpha()
			# Scale down logo
			size = self.logo.get_size()
			self.logo = pygame.transform.scale(self.logo, (size[0]//2, size[1]//2))
		except Exception as e:
			print(f"Warning: Could not load logo: {e}")
			self.logo = None
	
	def _create_buttons(self):
		"""Create Host and Join buttons."""
		# Host button
		host_rect = pygame.Rect(
			GameConfig.SCREEN_WIDTH // 4 - 200,
			GameConfig.SCREEN_HEIGHT // 2 - 50,
			400, 80
		)
		self.buttons.append({
			'rect': host_rect,
			'text': 'Host',
			'color': (33, 35, 59),
			'hover_color': (50, 52, 80),
			'action': 'host'
		})
		
		# Join button
		join_rect = pygame.Rect(
			GameConfig.SCREEN_WIDTH // 4 - 200,
			GameConfig.SCREEN_HEIGHT // 2 + 100,
			400, 80
		)
		self.buttons.append({
			'rect': join_rect,
			'text': 'Join',
			'color': (33, 35, 59),
			'hover_color': (50, 52, 80),
			'action': 'join'
		})
	
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
	
	def handle_input(self, event, state: str = "HOME") -> str:
		"""
		Process input events.
		state: Current game state ("HOME" or "JOIN_INPUT")
		Returns: 'host', 'join', 'connect', 'back', or None
		"""
		if event.type == pygame.MOUSEMOTION:
			self.mouse_pos = event.pos
			if state == "JOIN_INPUT":
				self.connect_button_hover = self.connect_button_rect.collidepoint(event.pos)
		
		if event.type == pygame.MOUSEBUTTONDOWN:
			if event.button == 1:  # Left click
				if state == "JOIN_INPUT":
					# Check if clicking on IP input field
					if self.ip_input_rect.collidepoint(event.pos):
						self.ip_input_active = True
					# Check Connect button
					elif self.connect_button_rect.collidepoint(event.pos):
						self.server_ip = self.ip_input_text if self.ip_input_text else "localhost"
						return 'connect'
					else:
						self.ip_input_active = False
				else:  # HOME state
					# Check if clicking on IP input field
					if self.ip_input_rect.collidepoint(event.pos):
						self.ip_input_active = True
					else:
						self.ip_input_active = False
						# Check buttons
						result = self._check_button_click(event.pos)
						if result:
							return result
		
		# Handle keyboard input for IP field (both states)
		if event.type == pygame.KEYDOWN and self.ip_input_active:
			if event.key == pygame.K_BACKSPACE:
				self.ip_input_text = self.ip_input_text[:-1]
			elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
				if state == "JOIN_INPUT":
					# Connect on Enter key
					self.server_ip = self.ip_input_text if self.ip_input_text else "localhost"
					return 'connect'
			elif event.unicode and event.unicode.isprintable():
				# Only allow numbers, dots, and common characters for IP
				char = event.unicode
				if char.isdigit() or char == '.' or char == ':':
					if len(self.ip_input_text) < 20:  # Limit length
						self.ip_input_text += char
		
		return None
	
	def _check_button_click(self, pos) -> str:
		"""Check if a button was clicked."""
		for button in self.buttons:
			if button['rect'].collidepoint(pos):
				action = button['action']
				if action == 'join':
					# Don't connect immediately, just return 'join' to switch to input page
					# Reset IP input for fresh entry
					self.ip_input_text = ""
					self.ip_input_active = False
				return action
		return None
	
	def get_server_ip(self) -> str:
		"""Get the server IP address to connect to."""
		return self.server_ip
	
	def draw(self, screen: pygame.Surface, state: str = "HOME"):
		"""Draw the screen based on state."""
		# Draw background
		screen.blit(self.bg, (0, 0))
		
		if state == "JOIN_INPUT":
			self._draw_join_input_page(screen)
		else:
			self._draw_home_page(screen)
	
	def _draw_home_page(self, screen: pygame.Surface):
		"""Draw the home page."""
		# Draw logos
		if self.char_logo:
			char_x = GameConfig.SCREEN_WIDTH - GameConfig.SCREEN_WIDTH // 2.5
			char_y = (GameConfig.SCREEN_HEIGHT - self.char_logo.get_height()) // 2
			screen.blit(self.char_logo, (char_x, char_y))
		
		if self.logo:
			logo_x = -50
			logo_y = 0
			screen.blit(self.logo, (logo_x, logo_y))
		
		# Draw buttons
		for button in self.buttons:
			is_hover = button['rect'].collidepoint(self.mouse_pos)
			color = button['hover_color'] if is_hover else button['color']
			
			# Draw button background
			pygame.draw.rect(screen, color, button['rect'])
			pygame.draw.rect(screen, (255, 255, 255), button['rect'], 3)
			
			# Draw button text
			text_surface = self.button_font.render(button['text'], True, (255, 255, 255))
			text_rect = text_surface.get_rect(center=button['rect'].center)
			screen.blit(text_surface, text_rect)
		
		# Show Host's IP address (for reference)
		local_ip = self._get_local_ip()
		info_text = f"Your IP: {local_ip} (for Host)"
		info_surface = self.button_font.render(info_text, True, (200, 200, 255))
		info_rect = info_surface.get_rect()
		info_rect.topleft = (GameConfig.SCREEN_WIDTH // 4 - 200, GameConfig.SCREEN_HEIGHT // 2 - 150)
		screen.blit(info_surface, info_rect)
	
	def _draw_join_input_page(self, screen: pygame.Surface):
		"""Draw the Join IP input page."""
		# Title
		title_text = "Enter Server IP"
		title_surface = self.font.render(title_text, True, (255, 255, 255))
		title_rect = title_surface.get_rect()
		title_rect.centerx = GameConfig.SCREEN_WIDTH // 2
		title_rect.top = GameConfig.SCREEN_HEIGHT // 2 - 150
		screen.blit(title_surface, title_rect)
		
		# Draw IP input field
		input_bg_color = (40, 40, 60) if not self.ip_input_active else (60, 60, 90)
		input_border_color = (100, 150, 255) if self.ip_input_active else (200, 200, 200)
		pygame.draw.rect(screen, input_bg_color, self.ip_input_rect)
		pygame.draw.rect(screen, input_border_color, self.ip_input_rect, 3)
		
		# Draw label (above the input field)
		label_text = "Server IP:"
		label_surface = self.button_font.render(label_text, True, (255, 255, 255))
		label_rect = label_surface.get_rect()
		label_rect.centerx = self.ip_input_rect.centerx
		label_rect.bottom = self.ip_input_rect.top - 8
		screen.blit(label_surface, label_rect)
		
		# Draw input text
		display_text = self.ip_input_text if self.ip_input_text else "localhost (or enter IP)"
		if not self.ip_input_active and not self.ip_input_text:
			display_text = "localhost (or enter IP)"
			text_color = (150, 150, 150)  # Gray for placeholder
		else:
			display_text = self.ip_input_text if self.ip_input_text else ""
			text_color = (255, 255, 255)
		
		# Show cursor when active
		if self.ip_input_active:
			cursor = "|" if int(pygame.time.get_ticks() / 500) % 2 == 0 else ""
			display_text = self.ip_input_text + cursor
		
		text_surface = self.input_font.render(display_text, True, text_color)
		# Clip text to fit in box
		if text_surface.get_width() > self.ip_input_rect.width - 10:
			# Show only last part of text that fits
			text_surface = self.input_font.render(display_text[-(len(display_text)//2):], True, text_color)
		text_rect = text_surface.get_rect(midleft=(self.ip_input_rect.left + 5, self.ip_input_rect.centery))
		screen.blit(text_surface, text_rect)
		
		# Draw Connect button
		connect_color = (50, 52, 80) if self.connect_button_hover else (33, 35, 59)
		pygame.draw.rect(screen, connect_color, self.connect_button_rect)
		pygame.draw.rect(screen, (255, 255, 255), self.connect_button_rect, 3)
		
		connect_text = "Connect"
		connect_surface = self.button_font.render(connect_text, True, (255, 255, 255))
		connect_text_rect = connect_surface.get_rect(center=self.connect_button_rect.center)
		screen.blit(connect_surface, connect_text_rect)
		
		# Hint text
		hint_text = "Press Enter or click Connect to join"
		hint_surface = self.button_font.render(hint_text, True, (150, 150, 150))
		hint_rect = hint_surface.get_rect()
		hint_rect.centerx = GameConfig.SCREEN_WIDTH // 2
		hint_rect.top = self.connect_button_rect.bottom + 20
		screen.blit(hint_surface, hint_rect)
