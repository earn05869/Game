"""
Pygame Top-Down Adventure Game
================================

This is a clean, object-oriented implementation of a 2D top-down game with:
- Tiled map loading (TMX format)
- Player movement with collision detection
- Interactive objects (doors, items)
- Dialog system
- Camera following the player

Architecture:
-------------
1. GameConfig: Centralized configuration constants
2. GameObject Classes: Player, Wall, Door, Interactable
3. GameWorld: Manages all game objects and map
4. Camera: Handles viewport and coordinate transformations
5. DialogSystem: Manages dialog display
6. InputHandler: Processes user input
7. Game: Main game loop and state management
"""

import pygame
import sys
from pytmx.util_pygame import load_pygame
from typing import List, Optional, Dict


# ============================================================================
# CONFIGURATION
# ============================================================================

class GameConfig:
    """
    Centralized game configuration.
    
    All magic numbers and constants are defined here for easy modification.
    """
    # Display settings
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 60
    ZOOM_LEVEL = 2
    
    # Player settings
    PLAYER_SIZE = 32
    PLAYER_COLOR = (255, 0, 0)
    PLAYER_SPEED = 4
    
    # UI settings
    DIALOG_FONT_SIZE = 32
    PROMPT_FONT_SIZE = 24
    DIALOG_BG_COLOR = (0, 0, 0)
    DIALOG_BORDER_COLOR = (255, 255, 255)
    PROMPT_BG_COLOR = (0, 0, 0)
    PROMPT_TEXT_COLOR = (255, 255, 255)
    
    # Map settings
    MAP_PATH = "asset/room1/room1.tmx"
    
    # Game states
    STATE_PLAYING = "PLAYING"
    STATE_DIALOGUE = "DIALOGUE"


# ============================================================================
# GAME OBJECTS
# ============================================================================

class GameObject(pygame.sprite.Sprite):
    """
    Base class for all game objects.
    
    Provides common functionality for objects that exist in the game world
    with position and collision detection.
    """
    def __init__(self, x: int, y: int, width: int, height: int):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)


class Wall(GameObject):
    """
    Solid wall object that blocks player movement.
    
    These are typically loaded from the "collision" layer in the TMX map.
    """
    def __init__(self, x: int, y: int, width: int, height: int):
        super().__init__(x, y, width, height)


class Door(GameObject):
    """
    Interactive door object that can be opened/closed.
    
    Attributes:
        is_locked (bool): Whether the door blocks movement
        name (str): Identifier for the door
    
    The door acts as a solid object when locked and can be toggled
    by player interaction.
    """
    def __init__(self, x: int, y: int, width: int, height: int):
        super().__init__(x, y, width, height)
        self.is_locked = True
        self.name = "door"
    
    def toggle(self, solids_group: pygame.sprite.Group) -> None:
        """
        Toggle door between locked and unlocked states.
        
        Args:
            solids_group: The sprite group containing solid objects.
                         Door is added/removed from this group based on state.
        """
        self.is_locked = not self.is_locked
        if self.is_locked:
            solids_group.add(self)
        else:
            solids_group.remove(self)


class Interactable(GameObject):
    """
    Generic interactable object (books, flowers, etc.).
    
    Attributes:
        name (str): Unique identifier used to look up dialog text
    
    When the player presses the interact key near this object,
    it displays associated dialog text.
    """
    def __init__(self, x: int, y: int, width: int, height: int, name: str):
        super().__init__(x, y, width, height)
        self.name = name


class Player(pygame.sprite.Sprite):
    """
    The player character controlled by keyboard input.
    
    Attributes:
        world_x, world_y (float): Position in world coordinates
        world_rect (Rect): Collision rectangle in world space
        rect (Rect): Display rectangle in screen space (for rendering)
        speed (int): Movement speed in pixels per frame
    
    The player has both screen and world coordinates:
    - Screen coordinates (rect): Fixed position where player appears on screen
    - World coordinates (world_x, world_y, world_rect): Actual position in game world
    """
    def __init__(self, x: int, y: int, screen_size: tuple):
        super().__init__()
        self.image = pygame.Surface((GameConfig.PLAYER_SIZE, GameConfig.PLAYER_SIZE))
        self.image.fill(GameConfig.PLAYER_COLOR)
        
        # Screen position (fixed at center of screen)
        self.rect = self.image.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2))
        
        # World position (moves through the game world)
        self.world_x = x
        self.world_y = y
        self.world_rect = self.image.get_rect(center=(self.world_x, self.world_y))
        
        self.speed = GameConfig.PLAYER_SPEED
    
    def update(self, solids: pygame.sprite.Group) -> None:
        """
        Update player position based on keyboard input.
        
        Args:
            solids: Group of solid objects to check collision against
        
        Movement is handled separately for X and Y axes to allow
        sliding along walls (if blocked horizontally, can still move vertically).
        """
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        # Calculate desired movement
        if keys[pygame.K_a]:
            dx = -self.speed
        if keys[pygame.K_d]:
            dx = self.speed
        if keys[pygame.K_w]:
            dy = -self.speed
        if keys[pygame.K_s]:
            dy = self.speed
        
        # Apply horizontal movement with collision detection
        if dx != 0:
            self.world_x += dx
            self.world_rect.centerx = self.world_x
            for solid in solids:
                if self.world_rect.colliderect(solid.rect):
                    if dx > 0:  # Moving right
                        self.world_rect.right = solid.rect.left
                    if dx < 0:  # Moving left
                        self.world_rect.left = solid.rect.right
                    self.world_x = self.world_rect.centerx
        
        # Apply vertical movement with collision detection
        if dy != 0:
            self.world_y += dy
            self.world_rect.centery = self.world_y
            for solid in solids:
                if self.world_rect.colliderect(solid.rect):
                    if dy > 0:  # Moving down
                        self.world_rect.bottom = solid.rect.top
                    if dy < 0:  # Moving up
                        self.world_rect.top = solid.rect.bottom
                    self.world_y = self.world_rect.centery


# ============================================================================
# GAME WORLD
# ============================================================================

class GameWorld:
    """
    Manages the game map and all game objects.
    
    Attributes:
        tmx_data: Loaded TMX map data
        map_surface (Surface): Pre-rendered map image
        solid_objects (Group): All solid/collidable objects
        interactables (Group): All interactive objects (doors, items)
    
    This class is responsible for:
    - Loading the TMX map file
    - Rendering the map to a surface
    - Creating game objects from map layers
    - Providing access to game objects for collision/interaction
    """
    def __init__(self):
        self.tmx_data = self._load_map()
        self.map_surface = self._render_map()
        self.solid_objects = pygame.sprite.Group()
        self.interactables = pygame.sprite.Group()
        self._create_objects_from_map()
    
    def _load_map(self):
        """Load the TMX map file."""
        try:
            return load_pygame(GameConfig.MAP_PATH)
        except FileNotFoundError:
            print(f"Error: {GameConfig.MAP_PATH} not found.")
            pygame.quit()
            sys.exit()
    
    def _render_map(self) -> pygame.Surface:
        """
        Pre-render the entire map to a surface.
        
        Returns:
            Surface containing the complete rendered map
        
        This is done once at startup for performance. The map is then
        blitted to the screen each frame with camera offset.
        """
        map_width = self.tmx_data.width * self.tmx_data.tilewidth
        map_height = self.tmx_data.height * self.tmx_data.tileheight
        surface = pygame.Surface((map_width, map_height))
        
        for layer in self.tmx_data.visible_layers:
            if not isinstance(layer, pygame.sprite.Group):
                if hasattr(layer, 'data'):
                    for x, y, gid in layer:
                        tile = self.tmx_data.get_tile_image_by_gid(gid)
                        if tile:
                            surface.blit(tile, (x * self.tmx_data.tilewidth, 
                                              y * self.tmx_data.tileheight))
        return surface
    
    def _create_objects_from_map(self) -> None:
        """
        Create game objects from TMX object layers.
        
        Reads three layers from the map:
        - "collision": Creates Wall objects (solid boundaries)
        - "door": Creates Door objects (interactive, toggleable)
        - "interact": Creates Interactable objects (items, etc.)
        """
        # Load collision objects
        try:
            for obj in self.tmx_data.get_layer_by_name("collision"):
                self.solid_objects.add(Wall(obj.x, obj.y, obj.width, obj.height))
        except ValueError:
            print("Warning: 'collision' layer not found.")
        
        # Load doors
        try:
            for obj in self.tmx_data.get_layer_by_name("door"):
                door = Door(obj.x, obj.y, obj.width, obj.height)
                self.interactables.add(door)
                if door.is_locked:
                    self.solid_objects.add(door)
        except ValueError:
            print("Warning: 'door' layer not found.")
        
        # Load interactable objects
        try:
            for obj in self.tmx_data.get_layer_by_name("interact"):
                self.interactables.add(
                    Interactable(obj.x, obj.y, obj.width, obj.height, obj.name)
                )
        except ValueError:
            print("Warning: 'interact' layer not found.")


# ============================================================================
# CAMERA SYSTEM
# ============================================================================

class Camera:
    """
    Manages the viewport that follows the player.
    
    Attributes:
        rect (Rect): The camera's viewport rectangle in world coordinates
    
    The camera determines which part of the game world is visible on screen.
    It follows the player by centering on the player's world position.
    """
    def __init__(self, width: int, height: int):
        self.rect = pygame.Rect(0, 0, width, height)
    
    def update(self, target_x: int, target_y: int) -> None:
        """
        Center the camera on a target position.
        
        Args:
            target_x: X coordinate in world space
            target_y: Y coordinate in world space
        """
        self.rect.center = (target_x, target_y)
    
    def world_to_screen(self, world_rect: pygame.Rect) -> pygame.Rect:
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            world_rect: Rectangle in world coordinates
        
        Returns:
            Rectangle in screen coordinates (relative to camera)
        """
        return world_rect.move(-self.rect.x, -self.rect.y)


# ============================================================================
# DIALOG SYSTEM
# ============================================================================

class DialogSystem:
    """
    Manages dialog text display.
    
    Attributes:
        texts (dict): Maps object names to their dialog text
        font (Font): Font for rendering dialog text
    
    Displays dialog boxes at the bottom of the screen when triggered.
    """
    def __init__(self):
        self.texts = {
            "flower": "A lovely potted flower.",
            "book1": "It's a dusty old tome.",
            "book2": "A book about Pygame programming.",
            "book3": "This book's pages are blank."
        }
        self.font = pygame.font.Font(None, GameConfig.DIALOG_FONT_SIZE)
    
    def get_text(self, object_name: str) -> str:
        """
        Get dialog text for an object.
        
        Args:
            object_name: The name of the interactable object
        
        Returns:
            Dialog text, or a default message if not found
        """
        return self.texts.get(object_name, "An interesting object.")
    
    def draw(self, screen: pygame.Surface, text: str) -> None:
        """
        Draw a dialog box with text at the bottom of the screen.
        
        Args:
            screen: The main screen surface to draw on
            text: The text to display in the dialog box
        """
        # Create dialog box
        padding = 50
        box_height = 100
        dialog_bg = pygame.Rect(
            padding, 
            GameConfig.SCREEN_HEIGHT - box_height - padding,
            GameConfig.SCREEN_WIDTH - (padding * 2),
            box_height
        )
        
        # Draw box
        pygame.draw.rect(screen, GameConfig.DIALOG_BG_COLOR, dialog_bg)
        pygame.draw.rect(screen, GameConfig.DIALOG_BORDER_COLOR, dialog_bg, 3)
        
        # Render and center text
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=dialog_bg.center)
        screen.blit(text_surface, text_rect)


# ============================================================================
# INPUT HANDLER
# ============================================================================

class InputHandler:
    """
    Processes user input and triggers game actions.
    
    This class separates input handling from game logic, making it easier
    to change controls or add new input methods.
    """
    @staticmethod
    def handle_events(game_state: str, current_interaction_target: Optional[GameObject],
                     solid_objects: pygame.sprite.Group, 
                     dialog_system: 'DialogSystem') -> tuple:
        """
        Process pygame events and return resulting actions.
        
        Args:
            game_state: Current game state
            current_interaction_target: Object the player can currently interact with
            solid_objects: Group of solid objects (for door toggling)
            dialog_system: The dialog system instance for getting dialog text
        
        Returns:
            Tuple of (new_game_state, dialog_text)
        """
        dialog_text = ""
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT", ""
            
            if event.type == pygame.KEYDOWN:
                # Close dialog
                if game_state == GameConfig.STATE_DIALOGUE:
                    game_state = GameConfig.STATE_PLAYING
                
                # Handle interaction
                elif game_state == GameConfig.STATE_PLAYING and event.key == pygame.K_e:
                    if current_interaction_target:
                        if isinstance(current_interaction_target, Door):
                            current_interaction_target.toggle(solid_objects)
                        elif isinstance(current_interaction_target, Interactable):
                            dialog_text = dialog_system.get_text(
                                current_interaction_target.name
                            )
                            game_state = GameConfig.STATE_DIALOGUE
        
        return game_state, dialog_text


# ============================================================================
# INTERACTION PROMPT
# ============================================================================

class InteractionPrompt:
    """
    Displays the 'E' prompt above interactable objects.
    
    Shows visual feedback to the player indicating they can interact
    with a nearby object.
    """
    def __init__(self):
        self.font = pygame.font.Font(None, GameConfig.PROMPT_FONT_SIZE)
    
    def draw(self, surface: pygame.Surface, target: GameObject, camera: Camera) -> None:
        """
        Draw the interaction prompt above an object.
        
        Args:
            surface: Surface to draw on (game surface, before scaling)
            target: The interactable object to draw the prompt above
            camera: Camera for coordinate conversion
        """
        # Render prompt text
        prompt_text = self.font.render("E", True, GameConfig.PROMPT_TEXT_COLOR)
        
        # Position in world coordinates (above the object)
        prompt_rect = prompt_text.get_rect(
            centerx=target.rect.centerx,
            bottom=target.rect.top - 5
        )
        
        # Create background box
        bg_rect = prompt_rect.inflate(10, 6)
        
        # Convert to screen coordinates
        screen_bg_rect = camera.world_to_screen(bg_rect)
        screen_prompt_rect = camera.world_to_screen(prompt_rect)
        
        # Draw
        pygame.draw.rect(surface, GameConfig.PROMPT_BG_COLOR, screen_bg_rect)
        pygame.draw.rect(surface, GameConfig.PROMPT_TEXT_COLOR, screen_bg_rect, 1)
        surface.blit(prompt_text, screen_prompt_rect)


# ============================================================================
# MAIN GAME CLASS
# ============================================================================

class Game:
    """
    Main game controller that manages the game loop.
    
    Attributes:
        screen: Main display surface (full resolution)
        game_surface: Internal rendering surface (lower resolution, scaled up)
        clock: Controls frame rate
        world: The game world with map and objects
        player: The player character
        camera: Viewport camera
        dialog_system: Handles dialog display
        interaction_prompt: Shows 'E' prompt
        state: Current game state (PLAYING or DIALOGUE)
        current_dialog: Text currently shown in dialog box
        current_interaction_target: Object player can currently interact with
    
    This class ties all systems together and runs the main game loop.
    """
    
    # Class variable for dialog system (shared across methods)
    dialog_system = None
    
    def __init__(self):
        pygame.init()
        
        # Display setup
        self.screen = pygame.display.set_mode(
            (GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT)
        )
        game_surface_size = (
            GameConfig.SCREEN_WIDTH // GameConfig.ZOOM_LEVEL,
            GameConfig.SCREEN_HEIGHT // GameConfig.ZOOM_LEVEL
        )
        self.game_surface = pygame.Surface(game_surface_size)
        pygame.display.set_caption("My Game")
        self.clock = pygame.time.Clock()
        
        # Game systems
        self.world = GameWorld()
        self.player = Player(950, 650, game_surface_size)
        self.camera = Camera(game_surface_size[0], game_surface_size[1])
        self.dialog_system = DialogSystem()
        self.interaction_prompt = InteractionPrompt()
        
        # Helper sprite for collision detection with interactables
        self.player_world_sprite = pygame.sprite.Sprite()
        
        # Sprite group for rendering
        self.screen_sprites = pygame.sprite.Group(self.player)
        
        # Game state
        self.state = GameConfig.STATE_PLAYING
        self.current_dialog = ""
        self.current_interaction_target = None
    
    def handle_input(self) -> bool:
        """
        Process input events.
        
        Returns:
            False if the game should quit, True otherwise
        """
        new_state, dialog = InputHandler.handle_events(
            self.state,
            self.current_interaction_target,
            self.world.solid_objects,
            self.dialog_system
        )
        
        if new_state == "QUIT":
            return False
        
        self.state = new_state
        if dialog:
            self.current_dialog = dialog
        
        return True
    
    def update(self) -> None:
        """
        Update game state.
        
        - Updates player position if in PLAYING state
        - Updates camera to follow player
        - Checks for nearby interactable objects
        """
        # Update player
        if self.state == GameConfig.STATE_PLAYING:
            self.player.update(self.world.solid_objects)
        
        # Update player world sprite for collision detection
        self.player_world_sprite.rect = self.player.world_rect
        
        # Update camera
        self.camera.update(self.player.world_x, self.player.world_y)
        
        # Check for interactable objects near player
        collided = pygame.sprite.spritecollide(
            self.player_world_sprite,
            self.world.interactables,
            False
        )
        self.current_interaction_target = collided[0] if collided else None
    
    def draw(self) -> None:
        """
        Render the current game frame.
        
        Drawing order:
        1. Map (background)
        2. Player
        3. Interaction prompt (if applicable)
        4. Scale up game surface to screen
        5. Dialog box (if in DIALOGUE state)
        """
        # Clear screen
        self.game_surface.fill((0, 0, 0))
        
        # Draw map with camera offset
        self.game_surface.blit(
            self.world.map_surface,
            (-self.camera.rect.x, -self.camera.rect.y)
        )
        
        # Draw player
        self.screen_sprites.draw(self.game_surface)
        
        # Draw interaction prompt
        if (self.current_interaction_target and 
            self.state == GameConfig.STATE_PLAYING):
            self.interaction_prompt.draw(
                self.game_surface,
                self.current_interaction_target,
                self.camera
            )
        
        # Scale up to full screen
        scaled_surface = pygame.transform.scale(
            self.game_surface,
            (GameConfig.SCREEN_WIDTH, GameConfig.SCREEN_HEIGHT)
        )
        self.screen.blit(scaled_surface, (0, 0))
        
        # Draw dialog box if in dialog state
        if self.state == GameConfig.STATE_DIALOGUE:
            self.dialog_system.draw(self.screen, self.current_dialog)
        
        pygame.display.flip()
    
    def run(self) -> None:
        """
        Main game loop.
        
        Continuously:
        1. Handles input
        2. Updates game state
        3. Draws the frame
        4. Maintains target frame rate
        """
        running = True
        while running:
            running = self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(GameConfig.FPS)
        
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