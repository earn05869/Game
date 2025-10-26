import gc
import psutil
import pygame
from Core.Scene import Scene
from Core.SceneManager import SceneManager
from Core.Camera import Camera
from Core.GameObject import GameObject
from Core.InputHandler import InputHandle as Inp
from Core.Vector import Vector
from Core.CollisionManager import CollisionManager
from Core.Collider import BoxCollider

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# create scene and camera
camera = Camera(WIDTH, HEIGHT)
scene = Scene("TestScene", camera=camera, zoom=2.0)
scene_manage = SceneManager()
# create player
player = GameObject("Player", position=(1880,1290))
box = GameObject("Box", position=(2000,1290))

scene.game_objects.add(player)
scene.game_objects.add(box)

scene.render_map("./room1/room1.tmx")
scene_manage.load_scene(scene)

collision = CollisionManager()
player.add_collision(collision, BoxCollider(player))
player.collider.set_debug(True)
box.add_collision(collision, BoxCollider(box))

spd = 5

def debug_memory():
		"""แสดงข้อมูล memory และจำนวน surface ทั้งหมด"""
		process = psutil.Process()
		mem = process.memory_info().rss / (1024 * 1024)  # MB
		surfaces = [o for o in gc.get_objects() if isinstance(o, pygame.Surface)]

		print(f"[DEBUG] Memory usage: {mem:.2f} MB | Surfaces: {len(surfaces)} ")

running = True
while running:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

	# handle input
	Inp.update()
	if Inp.is_key_pressed(pygame.K_w): player.transform.translateY(-spd)
	if Inp.is_key_pressed(pygame.K_s): player.transform.translateY(spd)
	if Inp.is_key_pressed(pygame.K_a): player.transform.translateX(-spd)
	if Inp.is_key_pressed(pygame.K_d): player.transform.translateX(spd)
	# update
	scene.update()
	camera.follow(player)
	collision.update()
	# debug_memory()
	# draw
	screen.fill((33,33,33))
	scene.draw(screen)
	collision.draw(screen)
	pygame.display.flip()

pygame.quit()