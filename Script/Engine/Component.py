class Component:
	def __init__(self):
		self.components: dict = {}
	
	def add_component(self, cp: "Component"):
		if (self.components[type(cp)]):
			print("Add", type(cp))
			self.components[type(cp)] = cp

	def remove_component(self, cp: "Component"):
		if (self.components[type(cp)]):
			print("Remove", type(cp))
			self.components.pop(type(cp))

	def get_component(self, cp: "Component"):
		if (self.components[type(cp)]):
			print("Get", type(cp))
			return self.components[type(cp)]
