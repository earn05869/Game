# main.py
from Script.Game import Game
from GameConfig import UPDATE_STATE, STATE

if __name__ == "__main__":
	UPDATE_STATE(STATE.HOME)
	game = Game()
	game.run()
