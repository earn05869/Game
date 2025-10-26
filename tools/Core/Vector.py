class Vector:
	def __init__(self, x: float=0, y: float=0):
		self.x = x
		self.y = y

	def add(self, other: "Vector") -> "Vector":
		return Vector(self.x + other.x, self.y + other.y)

	def addTuple(self, other: tuple) -> "Vector":
		return Vector(self.x + other[0], self.y + other[1])

	def sub(self, other: "Vector") -> "Vector":
		return Vector(self.x - other.x, self.y - other.y)

	def subTuple(self, other: tuple) -> "Vector":
		return Vector(self.x - other[0], self.y - other[1])

	def to_tuple(self) -> tuple:
		return (self.x, self.y)