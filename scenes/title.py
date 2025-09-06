import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel, draw_text_panel
from .battle import Combatant


class TitleScreen(State):
    # 타이틀 화면: 시작, 불러오기, 종료와 게임오버를 함께 관리합니다.
    
    def __init__(self, game):
        super().__init__(game)
        self.font = get_font(32)
        self.small_font = get_font(16)
        
        # 타이틀 모드(0: 메인 타이틀, 1: 게임오버)
        self.mode = 0
        self.modes = ["메인 타이틀", "게임오버"]
        
        # 타이틀 상태입니다.
        self.selected_index = 0
        self.title_items = ["새로 시작하기", "불러오기", "종료"]
        
        # 게임오버 상태입니다.
        self.game_over_selected_index = 0
        self.game_over_items = ["다시 도전", "로드", "종료"]
        
        # 게임오버 메시지입니다.
        self.game_over_messages = [
            "게임 오버",
            "모든 파티원이 쓰러졌습니다...",
            "",
            "다시 도전하시겠습니까?"
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.mode == 0:  # 메인 타이틀
                self._handle_title_events(event)
            else:  # 게임오버
                self._handle_game_over_events(event)

    def _handle_title_events(self, event):
        # 메인 타이틀 입력을 처리합니다.
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected_index = (self.selected_index - 1) % len(self.title_items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = (self.selected_index + 1) % len(self.title_items)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate_title()
        elif event.key == pygame.K_ESCAPE:
            self.game.is_running = False

    def _handle_game_over_events(self, event):
        # 게임오버 화면 입력을 처리합니다.
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.game_over_selected_index = (self.game_over_selected_index - 1) % len(self.game_over_items)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.game_over_selected_index = (self.game_over_selected_index + 1) % len(self.game_over_items)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate_game_over()
        elif event.key == pygame.K_ESCAPE:
            self.game.is_running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_game_over_mouse_click(event.pos)

    def _handle_game_over_mouse_click(self, pos):
        # 게임오버 화면의 마우스 클릭을 처리합니다.
        # 버튼 영역 계산
        button_width = 120
        button_height = 40
        button_margin = 20
        center_x = self.game.width // 2
        center_y = self.game.height // 2
        
        # 다시 도전 버튼
        restart_btn = pygame.Rect(
            center_x - button_width - button_margin // 2,
            center_y + 50,
            button_width,
            button_height
        )
        
        # 로드 버튼
        load_btn = pygame.Rect(
            center_x + button_margin // 2,
            center_y + 50,
            button_width,
            button_height
        )
        
        if restart_btn.collidepoint(pos):
            self.game_over_selected_index = 0
            self._activate_game_over()
        elif load_btn.collidepoint(pos):
            self.game_over_selected_index = 1
            self._activate_game_over()

    def _activate_title(self):
        # 메인 타이틀 선택을 실행합니다.
        choice = self.title_items[self.selected_index]
        if choice == "새로 시작하기":
            self._start_new_game()
        elif choice == "불러오기":
            self._load_game()
        elif choice == "종료":
            self.game.is_running = False

    def _activate_game_over(self):
        # 게임오버 선택을 실행합니다.
        choice = self.game_over_items[self.game_over_selected_index]
        if choice == "다시 도전":
            self._restart_game()
        elif choice == "로드":
            self._load_game()
        elif choice == "종료":
            self.game.is_running = False

    def _start_new_game(self):
        # 새 게임을 시작합니다.
        self._reset_game_state()
        # 새로 시작하기에서는 오프닝부터 시작
        from .intro import Intro
        self.game.push_state(Intro(self.game))

    def _restart_game(self):
        # 게임을 처음부터 다시 시작합니다.
        self._reset_game_state()
        self._go_to_overworld()

    def _load_game(self):
        # 저장된 게임을 불러옵니다.
        try:
            from .quests import SaveLoad
            self.game.push_state(SaveLoad(self.game))
        except ImportError:
            # 저장/로드 시스템이 없는 경우 기본 재시작합니다.
            self._restart_game()

    def _reset_game_state(self):
        # 게임 상태를 초기화합니다.
        # 기본 게임 데이터를 초기화합니다.
        self.game.gold = 0
        self.game.gems = 0
        self.game.inventory = []
        
        # 파티를 초기화합니다.
        default_party = [
            Combatant("겨울이", max_hp=60, atk=10, speed=140, is_enemy=False, gold=0, level=1),
            Combatant("가을이", max_hp=40, atk=7, speed=120, is_enemy=False, gold=0, level=1),
        ]
        self.game.party = default_party
        
        # 퀘스트를 초기화합니다.
        from .quests import create_sample_quests
        self.game.quests = create_sample_quests()
        
        # 오버월드 적 정보를 초기화합니다.
        if hasattr(self.game, "overworld_enemies"):
            delattr(self.game, "overworld_enemies")
        if hasattr(self.game, "defeated_enemy_index"):
            delattr(self.game, "defeated_enemy_index")

    def _go_to_overworld(self):
        # 오버월드로 이동합니다.
        from .overworld import Overworld
        self.game.state_stack.clear()  # 모든 상태 제거
        self.game.push_state(Overworld(self.game))

    def set_game_over_mode(self):
        # 게임오버 모드로 전환합니다.
        self.mode = 1
        self.game_over_selected_index = 0

    def update(self, delta_time):
        # 별도의 업데이트는 필요하지 않습니다.
        pass

    def render(self, surface):
        if self.mode == 0:
            self._render_title(surface)
        else:
            self._render_game_over(surface)

    def _render_title(self, surface):
        # 메인 타이틀을 렌더링합니다.
        surface.fill((20, 30, 50))
        
        # 게임 제목을 표시합니다.
        title_text = "네모의 꿈"
        title_surface = self.font.render(title_text, True, (255, 255, 100))
        title_rect = title_surface.get_rect(center=(self.game.width // 2, self.game.height // 3))
        surface.blit(title_surface, title_rect)
        
        # 메뉴 항목을 표시합니다.
        for i, item in enumerate(self.title_items):
            color = (255, 255, 0) if i == self.selected_index else (200, 200, 200)
            item_surface = self.small_font.render(item, True, color)
            item_rect = item_surface.get_rect(center=(self.game.width // 2, self.game.height // 2 + i * 40))
            surface.blit(item_surface, item_rect)
        
        # 조작법 안내를 표시합니다.
        controls = [
            "↑↓: 선택",
            "Enter/Space: 실행",
            "ESC: 종료"
        ]
        
        control_y = self.game.height - 80
        for i, control in enumerate(controls):
            control_text = self.small_font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (20, control_y + i * 20))

    def _render_game_over(self, surface):
        # 게임오버 화면을 렌더링합니다.
        # 어두운 배경을 적용합니다.
        surface.fill((20, 10, 10))
        
        # 게임오버 메시지를 표시합니다.
        self._render_game_over_message(surface)
        
        # 버튼들을 표시합니다.
        self._render_game_over_buttons(surface)
        
        # 조작법 안내를 표시합니다.
        self._render_game_over_controls(surface)

    def _render_game_over_message(self, surface):
        # 게임오버 메시지를 표시합니다.
        center_x = self.game.width // 2
        start_y = self.game.height // 3
        
        for i, message in enumerate(self.game_over_messages):
            if message:  # 빈 문자열이 아닌 경우만 표시
                if i == 0:  # "게임 오버"는 큰 글씨로
                    text_surface = self.font.render(message, True, (255, 100, 100))
                else:
                    text_surface = self.small_font.render(message, True, (200, 200, 200))
                
                text_rect = text_surface.get_rect(center=(center_x, start_y + i * 40))
                surface.blit(text_surface, text_rect)

    def _render_game_over_buttons(self, surface):
        # 게임오버 버튼을 표시합니다.
        button_width = 120
        button_height = 40
        button_margin = 20
        center_x = self.game.width // 2
        center_y = self.game.height // 2
        
        # 다시 도전 버튼
        restart_btn = pygame.Rect(
            center_x - button_width - button_margin // 2,
            center_y + 50,
            button_width,
            button_height
        )
        
        restart_color = (255, 200, 100) if self.game_over_selected_index == 0 else (150, 150, 150)
        pygame.draw.rect(surface, restart_color, restart_btn, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), restart_btn, 2, border_radius=8)
        
        restart_text = self.small_font.render("다시 도전", True, (50, 50, 50))
        restart_text_rect = restart_text.get_rect(center=restart_btn.center)
        surface.blit(restart_text, restart_text_rect)
        
        # 로드 버튼
        load_btn = pygame.Rect(
            center_x + button_margin // 2,
            center_y + 50,
            button_width,
            button_height
        )
        
        load_color = (255, 200, 100) if self.game_over_selected_index == 1 else (150, 150, 150)
        pygame.draw.rect(surface, load_color, load_btn, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), load_btn, 2, border_radius=8)
        
        load_text = self.small_font.render("로드", True, (50, 50, 50))
        load_text_rect = load_text.get_rect(center=load_btn.center)
        surface.blit(load_text, load_text_rect)

    def _render_game_over_controls(self, surface):
        # 게임오버 조작 안내를 표시합니다.
        controls = [
            "← → : 버튼 선택",
            "Enter/Space : 선택",
            "ESC : 게임 종료"
        ]
        
        control_y = self.game.height - 80
        for i, control in enumerate(controls):
            control_text = self.small_font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (20, control_y + i * 20))


