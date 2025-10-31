from Script.Engine.SceneManager import SceneManager as SM
from Script.Engine.Scene import Scene
from scene.HomePage import HomeScene
from Script.Engine.Camera import Camera
from GameConfig import *

class SceneManager(SM): 
	def __init__(self, camera: Camera):
		super().__init__()
		self.camera = camera
		self.state = GET_STATE()
	
	def change_state(self, state: STATE):pass
		# scene = None
		# ResourceManager.clear()
		# match (state) :
		# 	case STATE.HOME:
		# 		scene = HomeScene(self.camera)
		# 	case STATE.CONNECT:
		# 		scene = HomeScene(self.camera)
		# 	case STATE.QUIT:
		# 		print("[QUIT GAME]")
		# 	case _: print("Not have", state)
		# self.change_scene(scene)
  
	def update(self):
		if self.state != GET_STATE():
			self.change_state(GET_STATE())
			self.state = GET_STATE()
		super().update()
		