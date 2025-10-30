
class ShareMemory:
	_instance = None
	def __init__(self):
		if ShareMemory._instance:
			ShareMemory._instance = self
		self.init()
		self.shared_data = {}

	def init(self):
		self.shared_data["connected_players"] = 0
		self.shared_data["player_pos"] = {"x": 200, "y": 200}
		# self.shared_data["Interact"] = None
		# self.shared_data["Lock"] = None
		# self.Shared_data["Kill"] = 0

	def reset(self):
		self.init()

	@staticmethod
	def get() -> "ShareMemory":
		return ShareMemory._instance