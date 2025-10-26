from UI.UIElement import UIElement

class Canvas(UIElement):
    def __init__(self, size=(800,600), world_space=True):
        super().__init__(position=(0,0), size=size, world_space=world_space)