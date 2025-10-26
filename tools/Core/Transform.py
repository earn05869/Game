from Core.Vector import Vector

class Transform:
	def __init__(self, position: Vector = Vector()):
		self.position = position
		
	def translate(self, offset: Vector):
		self.position = self.position.add(offset)

	def translateX(self, x: float):
		self.position = self.position.add(Vector(x, 0))
  
	def translateY(self, y: float):
		self.position = self.position.add(Vector(0, y))

	def set_positionXY(self, x: float, y: float):
		self.position = Vector(x, y)
  
	def get_position(self) -> Vector:
		return self.position

	def to_tuple(self) -> tuple:
		return (self.position.x, self.position.y)