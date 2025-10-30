from Engine.Component import Component
from Engine.GameObject import GameObject
from Engine.SceneManager import SceneManager
import pygame

class Collider(Component):
    def __init__(self, own: GameObject, offset: tuple=(0,0), istrigger: bool=False):
        super().__init__()
        self.own = own
        self.offset = offset
        self.istrigger = istrigger
        self.rect = own.transfrom.copy()
        self.previous_hits = set()  # เก็บ Object ที่ชนเมื่อ update รอบก่อน

    def update(self):
        # ปรับตำแหน่ง rect ตาม GameObject + offset
        self.rect.topleft = (self.own.transfrom.x + self.offset[0], 
                             self.own.transfrom.y + self.offset[1])
        
        if not SceneManager._instance:
            return
        
        obj_list = SceneManager._instance.current_scene.obj
        rect_list = [o.get_component(Collider).rect for o in obj_list if o != self.own]
        
        hits_indices = self.rect.collidelistall(rect_list)
        current_hits = set(obj_list[i] for i in hits_indices)

        # Enter
        for obj in current_hits - self.previous_hits:
            self.check_collision_enter(obj)
        
        # Stay
        for obj in current_hits & self.previous_hits:
            self.check_collision_stay(obj)
        
        # Exit
        for obj in self.previous_hits - current_hits:
            self.check_collision_exit(obj)
        
        # เก็บ state รอบนี้
        self.previous_hits = current_hits

    def check_collision_enter(self, other: GameObject):
        other_collider = other.get_component(Collider)
        if other_collider and other_collider.istrigger:
            return False
        if hasattr(self.own, "on_collision_enter") and callable(self.own.on_collision_enter):
            self.own.on_collision_enter(other)
            return True
        return False

    def check_collision_stay(self, other: GameObject):
        if hasattr(self.own, "on_collision_stay") and callable(self.own.on_collision_stay):
            self.own.on_collision_stay(other)
            return True
        return False

    def check_collision_exit(self, other: GameObject):
        if hasattr(self.own, "on_collision_exit") and callable(self.own.on_collision_exit):
            self.own.on_collision_exit(other)
            return True
        return False
