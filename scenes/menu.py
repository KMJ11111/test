import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel


class Menu(State):
    # 메뉴 및 설정 화면임(ESC로 닫을 수 있음)
    
    def __init__(self, game):
        super().__init__(game)
        self.font = get_font(16)
        self.items = ["캐릭터", "상점", "퀘스트", "설정", "세이브", "로드", "닫기"]
        self.index = 0
        
        # 설정 관련 변수임
        self.volume = 100
        self.show_fps = True
        self.fullscreen = False
        
        # 설정 모드 여부임
        self.is_settings_mode = False
        self.settings_index = 0
        self.settings_items = ["볼륨", "FPS 표시", "전체화면", "돌아가기"]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.is_settings_mode:
                self._handle_settings_events(event)
            else:
                self._handle_menu_events(event)

    def _handle_menu_events(self, event):
        # 메뉴 동작: ↑/↓ 이동, Enter 선택, ESC 닫기
        if event.key in (pygame.K_UP, pygame.K_w):
            self.index = (self.index - 1) % len(self.items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + 1) % len(self.items)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate()
        elif event.key == pygame.K_m:
            # M 키로 메뉴 닫기
            self.game.pop_state()

    def _handle_settings_events(self, event):
        # 설정 동작: ↑/↓ 항목 선택, ←/→ 값 변경, Enter/ESC 돌아가기
        if event.key in (pygame.K_UP, pygame.K_w):
            self.settings_index = (self.settings_index - 1) % len(self.settings_items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.settings_index = (self.settings_index + 1) % len(self.settings_items)
        elif event.key == pygame.K_LEFT:
            self._decrease_setting()
        elif event.key == pygame.K_RIGHT:
            self._increase_setting()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.settings_index == 3:  # 돌아가기
                self.is_settings_mode = False
        elif event.key == pygame.K_m:
            # M 키로 설정 모드 나가기
            self.is_settings_mode = False

    def _decrease_setting(self):
        # 값 낮추거나 토글함
        if self.settings_index == 0:  # 볼륨
            self.volume = max(0, self.volume - 10)
        elif self.settings_index == 1:  # FPS 표시
            self.show_fps = not self.show_fps
        elif self.settings_index == 2:  # 전체화면
            self.fullscreen = not self.fullscreen

    def _increase_setting(self):
        # 값 올리거나 토글함
        if self.settings_index == 0:  # 볼륨
            self.volume = min(100, self.volume + 10)
        elif self.settings_index == 1:  # FPS 표시
            self.show_fps = not self.show_fps
        elif self.settings_index == 2:  # 전체화면
            self.fullscreen = not self.fullscreen

    def _activate(self):
        # 선택된 메뉴 실행함
        choice = self.items[self.index]
        if choice == "캐릭터":
            from .character import Character
            self.game.push_state(Character(self.game))
        elif choice == "상점":
            from .shop import Shop
            self.game.push_state(Shop(self.game))
        elif choice == "퀘스트":
            from .quests import QuestLog
            self.game.push_state(QuestLog(self.game))
        elif choice == "설정":
            self.is_settings_mode = True
            self.settings_index = 0
        elif choice == "세이브":
            from .quests import SaveLoad
            self.game.push_state(SaveLoad(self.game, mode="save"))
        elif choice == "로드":
            from .quests import SaveLoad
            self.game.push_state(SaveLoad(self.game, mode="load"))
        elif choice == "닫기":
            self.game.pop_state()

    def update(self, delta_time):
        # 별도 업데이트 필요 없음
        pass

    def render(self, surface):
        if self.is_settings_mode:
            self._render_settings(surface)
        else:
            self._render_menu(surface)

    def _render_menu(self, surface):
        # 메뉴 렌더링함(선택 항목은 노란색으로 표시됨)
        surface.fill(THEME["bg"])
        panel = pygame.Rect(self.game.width//2 - 120, self.game.height//2 - 100, 240, 250)
        draw_panel(surface, panel)
        
        # 메뉴 항목 표시함
        for i, it in enumerate(self.items):
            color = (255, 255, 0) if i == self.index else THEME["text"]
            surface.blit(self.font.render(it, True, color), (panel.x + 16, panel.y + 20 + i * 28))

    def _render_settings(self, surface):
        # 설정 화면 렌더링함
        surface.fill(THEME["bg"])
        panel = pygame.Rect(self.game.width//2 - 120, self.game.height//2 - 100, 240, 250)
        draw_panel(surface, panel)
        
        # 제목 표시함
        title = self.font.render("설정", True, THEME["text"])
        surface.blit(title, (panel.x + 16, panel.y + 12))
        
        # 설정 항목 표시함
        for i, item in enumerate(self.settings_items):
            color = (255, 255, 0) if i == self.settings_index else THEME["text"]
            
            if item == "볼륨":
                item_text = f"{item}: {self.volume}%"
            elif item == "FPS 표시":
                item_text = f"{item}: {'켜짐' if self.show_fps else '꺼짐'}"
            elif item == "전체화면":
                item_text = f"{item}: {'켜짐' if self.fullscreen else '꺼짐'}"
            else:
                item_text = item
            
            surface.blit(self.font.render(item_text, True, color), (panel.x + 16, panel.y + 20 + i * 28))
        
        # 조작법 안내 표시함
        controls = [
            "↑↓: 설정 선택",
            "←→: 값 변경",
            "Enter: 돌아가기",
            "ESC: 돌아가기"
        ]
        
        control_y = panel.y + panel.height - 80
        for i, control in enumerate(controls):
            control_text = self.font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (panel.x + 16, control_y + i * 20))


