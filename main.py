import pygame
import sys
import socket
import threading
from pytmx.util_pygame import load_pygame
from typing import Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

class GameConfig:
    """Centralized game configuration."""
    # Display settings
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 60
    ZOOM_LEVEL = 2
    
    # Player settings
    PLAYER_SIZE = 32
    P1_COLOR = (255, 0, 0)  # Red for Player 1 (Server)
    P2_COLOR = (0, 0, 255)  # Blue for Player 2 (Client)
    PLAYER_SPEED = 4
    
    # UI settings
    FONT_LARGE = ('Consolas', 50)
    FONT_MEDIUM = ('Consolas', 30)
    FONT_SMALL = ('Consolas', 20)
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLACK = (0, 0, 0)
    COLOR_GREY = (100, 100, 100)
    COLOR_LIGHT_GREY = (170, 170, 170)
    
    # Dialog settings
    DIALOG_FONT_SIZE = 32
    PROMPT_FONT_SIZE = 24
    
    # Map settings
    MAP_PATH = "asset/room1/room1.tmx"
    
    # Network settings
    NETWORK_PORT = 12345

    # Game states
    STATE_MENU = "MENU"
    STATE_WAITING_FOR_CLIENT = "WAITING"
    STATE_GETTING_SERVER_IP = "GETTING_IP"
    STATE_CONNECTING = "CONNECTING"
    STATE_CONNECTED = "CONNECTED"
    STATE_GAMEPLAY = "GAMEPLAY"
    STATE_DIALOGUE = "DIALOGUE"
    STATE_QUIT = "QUIT"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_local_ip():
    """Finds the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# ============================================================================
# GAME OBJECTS (Slightly Modified Player)
# ============================================================================

class GameObject(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)

class Wall(GameObject):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)

class Interactable(GameObject):
    def __init__(self, x, y, width, height, name):
        super().__init__(x, y, width, height)
        self.name = name

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, color, screen_size):
        super().__init__()
        self.image = pygame.Surface((GameConfig.PLAYER_SIZE, GameConfig.PLAYER_SIZE))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2))
        
        self.world_x = float(x)
        self.world_y = float(y)
        self.world_rect = self.image.get_rect(center=(self.world_x, self.world_y))
        
        self.speed = GameConfig.PLAYER_SPEED
        self.velocity = {'x': 0.0, 'y': 0.0}

    def update(self, solids: pygame.sprite.Group):
        """Update player position based on its velocity, with collision."""
        # Horizontal movement
        self.world_x += self.velocity['x']
        self.world_rect.centerx = round(self.world_x)
        for solid in solids:
            if self.world_rect.colliderect(solid.rect):
                if self.velocity['x'] > 0: self.world_rect.right = solid.rect.left
                if self.velocity['x'] < 0: self.world_rect.left = solid.rect.right
                self.world_x = self.world_rect.centerx
        
        # Vertical movement
        self.world_y += self.velocity['y']
        self.world_rect.centery = round(self.world_y)
        for solid in solids:
            if self.world_rect.colliderect(solid.rect):
                if self.velocity['y'] > 0: self.world_rect.bottom = solid.rect.top
                if self.velocity['y'] < 0: self.world_rect.top = solid.rect.bottom
                self.world_y = self.world_rect.centery

# ============================================================================
# GAME WORLD (Unchanged)
# ============================================================================

class GameWorld:
    def __init__(self):
        self.tmx_data = load_pygame(GameConfig.MAP_PATH)
        self.map_surface = self._render_map()
        self.solid_objects = pygame.sprite.Group()
        self.interactables = pygame.sprite.Group()
        self._create_objects_from_map()

    def _render_map(self) -> pygame.Surface:
        map_width = self.tmx_data.width * self.tmx_data.tilewidth
        map_height = self.tmx_data.height * self.tmx_data.tileheight
        surface = pygame.Surface((map_width, map_height))
        for layer in self.tmx_data.visible_layers:
            if hasattr(layer, 'data'):
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        surface.blit(tile, (x * self.tmx_data.tilewidth, y * self.tmx_data.tileheight))
        return surface

    def _create_objects_from_map(self) -> None:
        if self.tmx_data.get_layer_by_name("collision"):
            for obj in self.tmx_data.get_layer_by_name("collision"):
                self.solid_objects.add(Wall(obj.x, obj.y, obj.width, obj.height))
        if self.tmx_data.get_layer_by_name("interact"):
            for obj in self.tmx_data.get_layer_by_name("interact"):
                self.interactables.add(Interactable(obj.x, obj.y, obj.width, obj.height, obj.name))

# ============================================================================
# CAMERA (Unchanged)
# ============================================================================

class Camera:
    def __init__(self, width, height):
        self.rect = pygame.Rect(0, 0, width, height)
    
    def update(self, target_x, target_y):
        self.rect.center = (target_x, target_y)

# ============================================================================
# MAIN GAME CLASS (Heavily Modified for Networking)
# ============================================================================

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        
        # Display
        self.screen = pygame.display.set_mode((GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT))
        self.game_surface_size = (GameConfig.SCREEN_WIDTH // GameConfig.ZOOM_LEVEL, GameConfig.SCREEN_HEIGHT // GameConfig.ZOOM_LEVEL)
        self.game_surface = pygame.Surface(self.game_surface_size)
        pygame.display.set_caption("Top-Down Adventure (Multiplayer)")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_large = pygame.font.SysFont(*GameConfig.FONT_LARGE)
        self.font_medium = pygame.font.SysFont(*GameConfig.FONT_MEDIUM)
        self.font_small = pygame.font.SysFont(*GameConfig.FONT_SMALL)
        
        # Game State
        self.state = GameConfig.STATE_MENU
        self.running = True

        # Networking
        self.network_socket: Optional[socket.socket] = None
        self.player_role: Optional[str] = None # 'server' or 'client'
        self.server_ip_display: Optional[str] = None
        self.connection_status = ""
        self.ip_input_text = ""
        self.ip_input_active = False

        # UI Elements
        self.btn_create_server = pygame.Rect(490, 250, 300, 60)
        self.btn_connect_server = pygame.Rect(490, 330, 300, 60)
        self.input_box_ip = pygame.Rect(480, 330, 240, 50)
        self.btn_connect_ip = pygame.Rect(730, 330, 120, 50)
        self.btn_play = pygame.Rect(540, 400, 200, 60)
        
        # Game components (initialized later)
        self.world: Optional[GameWorld] = None
        self.p1: Optional[Player] = None
        self.p2: Optional[Player] = None
        self.camera: Optional[Camera] = None
        self.local_player: Optional[Player] = None

    def setup_gameplay(self):
        """Initializes all components needed for the gameplay state."""
        self.world = GameWorld()
        self.p1 = Player(950, 650, GameConfig.P1_COLOR, self.game_surface_size)
        self.p2 = Player(1050, 650, GameConfig.P2_COLOR, self.game_surface_size)
        self.camera = Camera(*self.game_surface_size)
        self.local_player = self.p1 if self.player_role == 'server' else self.p2
        
        # Set up sprite group for rendering
        self.player_sprites = pygame.sprite.Group(self.p1, self.p2)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # --- UI Input Handling ---
            if self.state == GameConfig.STATE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.btn_create_server.collidepoint(event.pos):
                        self.player_role = 'server'
                        self.server_ip_display = get_local_ip()
                        self.state = GameConfig.STATE_WAITING_FOR_CLIENT
                        threading.Thread(target=self.start_server, daemon=True).start()
                    elif self.btn_connect_server.collidepoint(event.pos):
                        self.state = GameConfig.STATE_GETTING_SERVER_IP
                        self.ip_input_active = True
            
            elif self.state == GameConfig.STATE_GETTING_SERVER_IP:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.ip_input_active = self.input_box_ip.collidepoint(event.pos)
                    if self.btn_connect_ip.collidepoint(event.pos) and len(self.ip_input_text) > 0:
                        self.player_role = 'client'
                        self.state = GameConfig.STATE_CONNECTING
                        threading.Thread(target=self.start_client, args=(self.ip_input_text,), daemon=True).start()
                if event.type == pygame.KEYDOWN and self.ip_input_active:
                    if event.key == pygame.K_BACKSPACE:
                        self.ip_input_text = self.ip_input_text[:-1]
                    else:
                        self.ip_input_text += event.unicode

            elif self.state == GameConfig.STATE_CONNECTED:
                 if event.type == pygame.MOUSEBUTTONDOWN and self.btn_play.collidepoint(event.pos):
                    if self.player_role == 'server':
                       self.network_socket.send("START".encode())
                    self.setup_gameplay()
                    self.state = GameConfig.STATE_GAMEPLAY
                    threading.Thread(target=self.handle_communication, daemon=True).start()

            # --- Gameplay Input Handling ---
            elif self.state == GameConfig.STATE_GAMEPLAY:
                if self.player_role == 'client':
                    # Send key presses to server
                    if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                        if event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
                            action = "DOWN" if event.type == pygame.KEYDOWN else "UP"
                            key_name = pygame.key.name(event.key).upper()
                            self.network_socket.send(f"{key_name}:{action}".encode())

    def update(self):
        if self.state != GameConfig.STATE_GAMEPLAY:
            return # Don't update game world if not in gameplay

        # --- Server-side Logic ---
        if self.player_role == 'server':
            # P1 (Server's player) movement from local keyboard
            keys = pygame.key.get_pressed()
            self.p1.velocity['x'] = (keys[pygame.K_d] - keys[pygame.K_a]) * self.p1.speed
            self.p1.velocity['y'] = (keys[pygame.K_s] - keys[pygame.K_w]) * self.p1.speed
            
            # Update both players based on their velocities
            self.p1.update(self.world.solid_objects)
            self.p2.update(self.world.solid_objects)

            # Send authoritative state to client
            try:
                state_data = f"{self.p1.world_x},{self.p1.world_y},{self.p2.world_x},{self.p2.world_y}"
                self.network_socket.send(state_data.encode())
            except:
                print("Client disconnected.")
                self.running = False

        # Camera always follows the local player
        if self.local_player and self.camera:
            self.camera.update(self.local_player.world_x, self.local_player.world_y)

    def draw(self):
        self.screen.fill(GameConfig.COLOR_BLACK)
        
        if self.state in (GameConfig.STATE_GAMEPLAY, GameConfig.STATE_DIALOGUE):
            self.draw_gameplay()
        else:
            self.draw_ui()
            
        pygame.display.flip()

    def draw_gameplay(self):
        self.game_surface.fill(GameConfig.COLOR_BLACK)
        
        # Draw map with camera offset
        self.game_surface.blit(self.world.map_surface, (-self.camera.rect.x, -self.camera.rect.y))
        
        # Draw players relative to camera
        for player in self.player_sprites:
            screen_rect = player.world_rect.move(-self.camera.rect.x, -self.camera.rect.y)
            self.game_surface.blit(player.image, screen_rect)
            
        # Scale up to full screen
        scaled_surface = pygame.transform.scale(self.game_surface, self.screen.get_size())
        self.screen.blit(scaled_surface, (0, 0))

    def draw_ui(self):
        if self.state == GameConfig.STATE_MENU:
            self.draw_text("Multiplayer Adventure", self.font_large, 640, 150, center=True)
            self.draw_button(self.btn_create_server, "Create Server", self.font_medium)
            self.draw_button(self.btn_connect_server, "Connect to Server", self.font_medium)

        elif self.state == GameConfig.STATE_WAITING_FOR_CLIENT:
            self.draw_text("Waiting for Client...", self.font_large, 640, 280, center=True)
            if self.server_ip_display:
                self.draw_text(f"Your IP is: {self.server_ip_display}", self.font_medium, 640, 350, center=True)

        elif self.state == GameConfig.STATE_GETTING_SERVER_IP:
            self.draw_text("Enter Server IP", self.font_large, 640, 200, center=True)
            pygame.draw.rect(self.screen, GameConfig.COLOR_LIGHT_GREY, self.input_box_ip)
            self.draw_text(self.ip_input_text, self.font_medium, self.input_box_ip.x + 10, self.input_box_ip.centery)
            self.draw_button(self.btn_connect_ip, "Connect", self.font_medium)
            self.draw_text(self.connection_status, self.font_small, 640, 450, center=True)
        
        elif self.state == GameConfig.STATE_CONNECTING:
             self.draw_text(self.connection_status, self.font_medium, 640, 350, center=True)

        elif self.state == GameConfig.STATE_CONNECTED:
            self.draw_text("Connection Successful!", self.font_large, 640, 300, center=True)
            self.draw_button(self.btn_play, "PLAY", self.font_large)

    def draw_text(self, text, font, x, y, center=False):
        text_surface = font.render(text, True, GameConfig.COLOR_WHITE)
        text_rect = text_surface.get_rect()
        if center: text_rect.center = (x, y)
        else: text_rect.midleft = (x, y)
        self.screen.blit(text_surface, text_rect)

    def draw_button(self, rect, text, font):
        pygame.draw.rect(self.screen, GameConfig.COLOR_GREY, rect, border_radius=10)
        self.draw_text(text, font, rect.centerx, rect.centery, center=True)

    def run(self):
        while self.running:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(GameConfig.FPS)
        
        if self.network_socket:
            self.network_socket.close()
        pygame.quit()
        sys.exit()

    # --- Networking Methods ---
    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(('0.0.0.0', GameConfig.NETWORK_PORT))
            server.listen(1)
            print("Server is waiting for a connection...")
            client_sock, addr = server.accept()
            self.network_socket = client_sock
            print(f"Connected with {addr}")
            self.state = GameConfig.STATE_CONNECTED
        except Exception as e:
            print(f"Server error: {e}")
            self.state = GameConfig.STATE_MENU

    def start_client(self, server_ip):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.connection_status = f"Connecting to {server_ip}..."
            client.connect((server_ip, GameConfig.NETWORK_PORT))
            self.network_socket = client
            print("Successfully connected to the server.")
            self.state = GameConfig.STATE_CONNECTED
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connection_status = f"Failed to connect to {server_ip}"
            pygame.time.wait(2000)
            self.state = GameConfig.STATE_GETTING_SERVER_IP
    
    def handle_communication(self):
        while self.running:
            try:
                data = self.network_socket.recv(1024).decode()
                if not data: break

                if self.player_role == 'server':
                    key, action = data.split(':')
                    speed = self.p2.speed
                    if action == 'DOWN':
                        if key == 'W': self.p2.velocity['y'] = -speed
                        elif key == 'S': self.p2.velocity['y'] = speed
                        elif key == 'A': self.p2.velocity['x'] = -speed
                        elif key == 'D': self.p2.velocity['x'] = speed
                    elif action == 'UP':
                        if key in ('W', 'S'): self.p2.velocity['y'] = 0
                        if key in ('A', 'D'): self.p2.velocity['x'] = 0

                elif self.player_role == 'client':
                    if data == "START":
                        self.setup_gameplay()
                        self.state = GameConfig.STATE_GAMEPLAY
                        continue # Skip the rest of the loop for this message
                        
                    p1x, p1y, p2x, p2y = map(float, data.split(','))
                    if self.p1 and self.p2:
                       self.p1.world_x, self.p1.world_y = p1x, p1y
                       self.p2.world_x, self.p2.world_y = p2x, p2y
                       self.p1.world_rect.center = (p1x, p1y)
                       self.p2.world_rect.center = (p2x, p2y)

            except Exception as e:
                print(f"Communication error: {e}")
                self.running = False
        
        print("Communication thread ended.")

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    game = Game()
    game.run()