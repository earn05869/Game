from UI.Button import Button
from UI.Canvas import Canvas
from UI.Panel import Panel
from UI.Text import Text
from Core.Camera import Camera
import pygame

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# สร้าง Camera
camera = Camera(WIDTH, HEIGHT)

# สร้าง Canvas (ตามกล้อง)
canvas = Canvas(size=(WIDTH, HEIGHT), world_space=True)

# สร้าง Panel สีแดง
panel = Panel(position=(50,50), size=(200,100), color=(200,50,50))
canvas.add_child(panel)

# สร้าง Button
btn_panel = Panel(position=(0,0), size=(150,50), color=(100,100,200))
panel_w, panel_h = btn_panel.size
btn_text = Text("Click Me", font_size=24, color=(255,255,255), h_align="center", v_align="middle")
def on_click():
	print("Button clicked!")

button = Button(position=(300,50), size=(150,50), callback=on_click)
canvas.add_child(button)
button.add_child(btn_panel)
btn_panel.add_child(btn_text)

# สร้าง Text แยก
label = Text("Hello World", position=(500,50), font_size=32, color=(255,255,0))
canvas.add_child(label)

running = True
while running:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False
		button.handle_event(event)

	screen.fill((30,30,30))

	# วาด UI ตาม Camera
	canvas.draw(screen)

	pygame.display.flip()
	clock.tick(60)

pygame.quit()