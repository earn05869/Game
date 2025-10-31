from Script.Engine.ResourceManager import ResourceManager
from enum import Enum

# ===== DISPLAY SETTINGS =====
SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 720
FPS = 60
ZOOM_LEVEL = 2

# ===== PLAYER ======
MAX_PLAYER=2
PLAYER_SPRITE_WIDTH = 48
PLAYER_SPRITE_HEIGHT = 72
PLAYER_SPRITE_SHEET = {
	"back": "../asset/shion/back.png",
	"front": "../asset/shion/front.png",
	"left": "../asset/shion/left.png",
	"right": "../asset/shion/right.png"
}

class PLAYER_ROLE(Enum):
	Shion: 1
	Shione: 2

#  ===== GAME STATE =====

class STATE(Enum):
	HOME = 1
	CONNECT = 2
	PLAYING = 3
	GAMEOVER = 4
	QUIT = 5
 
GAME_STATE = STATE.HOME
def UPDATE_STATE(new_state):
	global GAME_STATE
	GAME_STATE = new_state
 
def GET_STATE():
	return GAME_STATE

# Map Path
class MAP_STATE(Enum):
	HOME = 1
	ROOM1 = 2
	HALL = 3
	RED = 4
	YELLOW = 5
	BLUE = 6

HOMEBG = "./asset/Images/homeBG.png"
CHAR_LOGO = "./asset/Images/character.png"
LOGO = "./asset/Images/logo.png"

MAP_ROOM1 = "./asset/room1/room1.tmx"
MAP_HALL = "./asset/hall/hall.tmx"
MAP_RED = "./asset/red/red.tmx"
MAP_YELLOW = "./asset/yellow/yellow.tmx"
MAP_BLUE = "./asset/blue/blue.tmx"

FONT = "./asset/font/NotoSansThaiLooped-VariableFont_wdth,wght.ttf"