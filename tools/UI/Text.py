import pygame
from UI.UIElement import UIElement

class Text(UIElement):
    def __init__(
        self,
        text,
        position=(0,0),
        font_size=24,
        color=(255,255,255),
        world_space=True,
        h_align="left",   # "left", "center", "right"
        v_align="top"     # "top", "middle", "bottom"
    ):
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.color = color
        self.h_align = h_align
        self.v_align = v_align

        # ใช้ขนาดข้อความจริง
        self.size = self.font.size(text)

        super().__init__(position=position, size=self.size, world_space=world_space, image=None)

    def compute_position(self):
        """คำนวณตำแหน่งจริงของ Text ตาม parent และ alignment"""
        # ถ้ามี parent ให้ใช้ parent position + size
        if self.parent:
            parent_pos = self.parent.global_position()
            parent_size = self.parent.size
        else:
            parent_pos = (0, 0)
            parent_size = self.size  # fallback ใช้ขนาดข้อความเอง

        x, y = self.position  # offset ของตัวเองจาก alignment

        # horizontal alignment
        if self.h_align == "left":
            x = parent_pos[0] + x
        elif self.h_align == "center":
            x = parent_pos[0] + parent_size[0] // 2 - self.size[0] // 2 + x
        elif self.h_align == "right":
            x = parent_pos[0] + parent_size[0] - self.size[0] + x

        # vertical alignment
        if self.v_align == "top":
            y = parent_pos[1] + y
        elif self.v_align == "middle":
            y = parent_pos[1] + parent_size[1] // 2 - self.size[1] // 2 + y
        elif self.v_align == "bottom":
            y = parent_pos[1] + parent_size[1] - self.size[1] + y

        return (x, y)

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        # สร้าง surface ของข้อความ
        text_surf = self.font.render(self.text, True, self.color)
        pos = self.compute_position()

        # วาดข้อความ
        surface.blit(text_surf, pos)

        # วาด children
        for child in self.children:
            child.draw(surface)
