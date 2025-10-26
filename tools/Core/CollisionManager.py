from Core.Collider import Collider

class CollisionManager:
	def __init__(self):
		self.colliders: list[Collider] = []

	def add_collider(self, collider):
		print("add")
		self.colliders.append(collider)

	def remove_collider(self, collider):
		if collider in self.colliders:
			self.colliders.remove(collider)

	def update(self):
		# update all colliders
		for col in self.colliders:
			col.update()

		# check collisions
		self._check_collisions()

	def _check_collisions(self):
		checked_pairs = set()
		for i, col_a in enumerate(self.colliders):
			for j, col_b in enumerate(self.colliders):
				if i >= j:
					continue
				pair = (col_a, col_b)
				if pair in checked_pairs:
					continue
				checked_pairs.add(pair)

				if col_a.rect.colliderect(col_b.rect):
					# Trigger ทั้งสอง
					if col_a.is_trigger or col_b.is_trigger:
						col_a.on_collision_enter(col_b)
						col_b.on_collision_enter(col_a)
					else:
						# Solid collision: block movement
						self._resolve_solid_collision(col_a, col_b)
	  
	def _resolve_solid_collision(self, a: Collider, b: Collider):
		# ตรวจการชนและแก้ position อย่างง่าย
		dx = (a.rect.centerx - b.rect.centerx)
		dy = (a.rect.centery - b.rect.centery)
		if abs(dx) > abs(dy):
			if dx > 0:
				a.game_object.transform.translateX(abs(b.rect.right - a.rect.left))
			else:
				a.game_object.transform.translateX(-(abs(a.rect.right - b.rect.left)))
		else:
			if dy > 0:
				a.game_object.transform.translateY(abs(b.rect.bottom - a.rect.top))
			else:
				a.game_object.transform.translateY(-(abs(a.rect.bottom - b.rect.top)))
		# เรียก callback
		a.on_collision_enter(b)
		b.on_collision_enter(a)

	def draw(self, screen):
		for line in self.colliders:
			line.draw(screen)