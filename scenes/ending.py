import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel


class Ending(State):
    # 엔딩 화면: 최종보스 처치 후 스토리 마무리
    
    def __init__(self, game):
        super().__init__(game)
        self.font = get_font(18)
        self.small_font = get_font(14)
        self.title_font = get_font(24)
        
        # 엔딩 페이지들
        self.pages = [
            [
                "겨울이와 가을이가 Demon Lord를 물리쳤다.",
                "",
                "동그란 세상에서 네모의 모서리가",
                "마침내 그 의미를 찾았다.",
            ],
            [
                "네모는 이제 알았다.",
                "모서리는 약점이 아니라",
                "세상을 바꿀 수 있는 힘이었다.",
                "",
                "동그란 세상에 네모의 모서리가",
                "새로운 가능성을 열어주었다.",
            ],
            [
                "겨울이와 가을이의 여행은 끝났지만,",
                "그들의 모서리는 영원히 빛날 것이다.",
                "",
                "동그란 세상에서",
                "네모의 꿈이 이루어졌다.",
            ],
        ]
        
        self.page_index = 0
        self.fade_timer = 0.0
        self.fade_duration = 1.0
        self.is_fading = False
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._next_page()
            elif event.key == pygame.K_ESCAPE:
                # 타이틀로 돌아가기
                self._go_to_title()
    
    def _next_page(self):
        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
        else:
            # 마지막 페이지 후 타이틀로
            self._go_to_title()
    
    def _go_to_title(self):
        # 타이틀 화면으로 이동
        from .title import TitleScreen
        self.game.state_stack.clear()
        self.game.push_state(TitleScreen(self.game))
    
    def update(self, delta_time):
        # 페이드 효과 처리
        if self.is_fading:
            self.fade_timer += delta_time
            if self.fade_timer >= self.fade_duration:
                self.is_fading = False
                self.fade_timer = 0.0
    
    def render(self, surface):
        # 배경을 어둡게
        surface.fill((5, 8, 12))
        
        # 페이드 효과
        if self.is_fading:
            alpha = int(255 * (self.fade_timer / self.fade_duration))
            fade_surface = pygame.Surface((self.game.width, self.game.height))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(alpha)
            surface.blit(fade_surface, (0, 0))
        
        # 메인 패널
        panel_width = self.game.width - 80
        panel_height = 200
        panel_x = (self.game.width - panel_width) // 2
        panel_y = (self.game.height - panel_height) // 2
        
        panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        draw_panel(surface, panel)
        
        # 제목
        title = self.title_font.render("THE END", True, THEME["text"])
        title_rect = title.get_rect(centerx=panel.centerx, y=panel.y + 20)
        surface.blit(title, title_rect)
        
        # 스토리 텍스트
        lines = self.pages[self.page_index]
        y = panel.y + 60
        for line in lines:
            if line:  # 빈 줄이 아닌 경우만
                text_surface = self.font.render(line, True, THEME["text"])
                text_rect = text_surface.get_rect(centerx=panel.centerx, y=y)
                surface.blit(text_surface, text_rect)
            y += 30
        
        # 하단 안내
        hint_rect = pygame.Rect(panel.x, panel.bottom + 20, panel.width, 30)
        draw_panel(surface, hint_rect, shadow=False)
        
        if self.page_index < len(self.pages) - 1:
            hint_text = "Enter/Space: 다음"
        else:
            hint_text = "Enter/Space: 타이틀로 돌아가기  ESC: 타이틀로"
        
        hint_surface = self.small_font.render(hint_text, True, THEME["text"])
        hint_rect_text = hint_surface.get_rect(centerx=hint_rect.centerx, centery=hint_rect.centery)
        surface.blit(hint_surface, hint_rect_text)
