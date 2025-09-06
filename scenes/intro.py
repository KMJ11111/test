import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel, draw_text_panel


class Intro(State):
    # 첫 시작 스토리 소개 화면임

    def __init__(self, game):
        super().__init__(game)
        self.font = get_font(18)
        self.small_font = get_font(14)

        # 페이지별 스토리 텍스트
        self.pages = [
            [
                "동그란 세상.",
                "모든 것이 둥글게 흐르는 곳.",
                "그곳에 네모가 태어났음.",
            ],
            [
                "네모는 스스로 물었음.",
                '"왜 나는 네모일까?"',
                "답을 찾기 위해 길을 떠났음.",
            ],
            [
                "동그란 바람, 동그란 길, 동그란 사람들.",
                "하지만 네모의 마음은 모서리를 잃지 않았음.",
                "이 여행은 그 모서리의 의미를 찾는 여정임.",
            ],
        ]
        self.page_index = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._next_page()
            elif event.key == pygame.K_ESCAPE:
                # 스킵
                self._finish()

    def _next_page(self):
        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
        else:
            self._finish()

    def _finish(self):
        # 오버월드로 전환
        from .overworld import Overworld
        self.game.state_stack.clear()
        self.game.push_state(Overworld(self.game))

    def update(self, delta_time):
        # 별도 업데이트 필요 없음
        pass

    def render(self, surface):
        surface.fill((10, 12, 16))
        panel = pygame.Rect(40, self.game.height // 2 - 90, self.game.width - 80, 180)
        draw_panel(surface, panel)
        # 단일 창: 내부에 텍스트만 직접 그리기(이중창 방지)
        lines = self.pages[self.page_index]
        y = panel.y + 22
        for line in lines:
            surf = self.font.render(line, True, THEME["text"])
            surface.blit(surf, (panel.x + 22, y))
            y += surf.get_height() + 6

        # 하단 안내
        hint_rect = pygame.Rect(panel.x, panel.bottom + 10, panel.width, 26)
        draw_panel(surface, hint_rect, shadow=False)
        hint = "Enter/Space: 다음  ESC: 스킵"
        hint_surf = self.small_font.render(hint, True, THEME["text"])
        surface.blit(hint_surf, (hint_rect.x + 10, hint_rect.y + 5))


