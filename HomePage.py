import pygame
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
		self.buttons = []
		self._create_buttons()
		
		# Mouse tracking
		self.mouse_pos = (0, 0)
		
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
			GameConfig.SCREEN_WIDTH // 2 - 150,
			GameConfig.SCREEN_HEIGHT // 2 - 50,
			300, 100
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
			GameConfig.SCREEN_WIDTH // 2 - 150,
			GameConfig.SCREEN_HEIGHT // 2 + 100,
			300, 100
		)
		self.buttons.append({
			'rect': join_rect,
			'text': 'Join',
			'color': (33, 35, 59),
			'hover_color': (50, 52, 80),
			'action': 'join'
		})
	
	def handle_input(self, event) -> str:
		"""
		Process input events.
		Returns: 'host', 'join', or None
		"""
		if event.type == pygame.MOUSEMOTION:
			self.mouse_pos = event.pos
		
		if event.type == pygame.MOUSEBUTTONDOWN:
			if event.button == 1:  # Left click
				return self._check_button_click(event.pos)
		
		return None
	
	def _check_button_click(self, pos) -> str:
		"""Check if a button was clicked."""
		for button in self.buttons:
			if button['rect'].collidepoint(pos):
				return button['action']
		return None
	
	def draw(self, screen: pygame.Surface):
		"""Draw the home screen."""
		# Draw background
		screen.blit(self.bg, (0, 0))
		
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
