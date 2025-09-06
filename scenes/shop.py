import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel, draw_text_panel
from .battle import Item


class Shop(State):
    # 상점 및 인벤토리 관리 화면입니다.
    
    def __init__(self, game):
        super().__init__(game)
        self.font = get_font(16)
        self.small_font = get_font(14)
        
        # 상점 아이템 목록입니다.
        self.shop_items = self._create_shop_items()
        
        # 상점 상태(0: 소비 아이템, 1: 무기)
        self.current_page = 0
        self.selected_item = 0
        self.pages = ["소비아이템", "무기"]
        
        # 인벤토리 탭 상태입니다.
        self.tabs = ["장비", "소비", "중요"]
        self.tab_index = 0
        self.item_index = 0
        
        # UI 설정입니다.
        self.panel_width = 400
        self.panel_height = 300
        
    def _create_shop_items(self):
        # 상점 아이템 초기 목록을 생성합니다.
        consumables = [
            Item("포션", "consumable", 50, "HP 30 회복", hp_bonus=30),
            Item("에너지 포션", "consumable", 40, "에너지 20 회복", energy_bonus=20),
            Item("해독약", "consumable", 60, "상태이상 해제"),
            Item("고급 포션", "consumable", 100, "HP 60 회복", hp_bonus=60),
        ]
        
        weapons = [
            Item("철검", "weapon", 200, "공격력 +5", atk_bonus=5),
            Item("강화된 검", "weapon", 400, "공격력 +10", atk_bonus=10),
            Item("마법검", "weapon", 600, "공격력 +15", atk_bonus=15),
            Item("전설의 검", "weapon", 1000, "공격력 +25", atk_bonus=25),
        ]
        
        return {
            "consumables": consumables,
            "weapons": weapons
        }
    
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            # ESC 키 제거 - B 키로 나가기
            if event.key == pygame.K_b:
                self.game.pop_state()
            elif event.key == pygame.K_TAB:
                # 상점과 인벤토리 모드를 전환합니다.
                if hasattr(self, 'is_inventory_mode'):
                    self.is_inventory_mode = not self.is_inventory_mode
                else:
                    self.is_inventory_mode = False
            elif self._is_shop_mode():
                self._handle_shop_events(event)
            else:
                self._handle_inventory_events(event)
    
    def _is_shop_mode(self):
        # 현재 화면이 상점인지 여부를 반환합니다.
        return not getattr(self, 'is_inventory_mode', False)
    
    def _handle_shop_events(self, event):
        # 상점 모드에서 입력을 처리합니다.
        if event.key == pygame.K_LEFT:
            self.current_page = (self.current_page - 1) % len(self.pages)
            self.selected_item = 0
        elif event.key == pygame.K_RIGHT:
            self.current_page = (self.current_page + 1) % len(self.pages)
            self.selected_item = 0
        elif event.key == pygame.K_UP:
            current_items = self._get_current_shop_items()
            self.selected_item = max(0, self.selected_item - 1)
        elif event.key == pygame.K_DOWN:
            current_items = self._get_current_shop_items()
            self.selected_item = min(len(current_items) - 1, self.selected_item + 1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._purchase_item()
    
    def _handle_inventory_events(self, event):
        # 인벤토리 모드에서 입력을 처리합니다.
        if event.key == pygame.K_LEFT:
            self.tab_index = (self.tab_index - 1) % len(self.tabs)
            self.item_index = 0
        elif event.key == pygame.K_RIGHT:
            self.tab_index = (self.tab_index + 1) % len(self.tabs)
            self.item_index = 0
        elif event.key == pygame.K_UP:
            self.item_index = max(0, self.item_index - 1)
        elif event.key == pygame.K_DOWN:
            items = self._get_current_inventory_items()
            self.item_index = min(len(items) - 1, self.item_index + 1)
    
    def _get_current_shop_items(self):
        # 현재 페이지의 상점 아이템 목록을 반환합니다.
        if self.current_page == 0:
            return self.shop_items["consumables"]
        else:
            return self.shop_items["weapons"]
    
    def _get_current_inventory_items(self):
        # 현재 탭의 인벤토리 아이템 목록입니다(Item 리스트 기준).
        inventory = getattr(self.game, "inventory", [])
        if not isinstance(inventory, list):
            # 딕셔너리 형태도 방어적으로 처리합니다.
            equipment = [name for name in inventory.get("equipment", [])]
            consumables = [name for name in inventory.get("consumables", [])]
            key_items = [name for name in inventory.get("key", [])]
            if self.tab_index == 0:
                return equipment
            elif self.tab_index == 1:
                return consumables
            else:
                return key_items
        if self.tab_index == 0:
            return [it.name for it in inventory if getattr(it, 'item_type', '') == 'weapon']
        elif self.tab_index == 1:
            return [it.name for it in inventory if getattr(it, 'item_type', '') == 'consumable']
        else:
            return []
    
    def _purchase_item(self):
        # 선택된 아이템 구매 로직입니다.
        current_items = self._get_current_shop_items()
        if not current_items or self.selected_item >= len(current_items):
            return
        
        item = current_items[self.selected_item]
        current_gold = getattr(self.game, "gold", 0)
        
        if current_gold >= item.price:
            # 골드를 차감합니다.
            self.game.gold -= item.price
            
            # 인벤토리에 아이템을 추가합니다.
            if not hasattr(self.game, "inventory"):
                self.game.inventory = []
            
            if isinstance(self.game.inventory, list):
                self.game.inventory.append(item)
            else:
                # 기존 딕셔너리 형태를 리스트로 승격합니다.
                upgraded = []
                for name in self.game.inventory.get("equipment", []):
                    upgraded.append(Item(name, "weapon", 0, ""))
                for name in self.game.inventory.get("consumables", []):
                    upgraded.append(Item(name, "consumable", 0, ""))
                for name in self.game.inventory.get("key", []):
                    upgraded.append(Item(name, "key", 0, ""))
                self.game.inventory = upgraded
                self.game.inventory.append(item)
            
            # 구매 성공 메시지를 출력합니다.
            self._show_message(f"{item.name} 구매 완료!")
        else:
            # 골드 부족 메시지를 출력합니다.
            self._show_message("골드가 부족합니다!")
    
    def _show_message(self, message):
        # 간단한 메시지를 콘솔에 출력합니다.
        print(f"상점: {message}")
    
    def update(self, delta_time):
        # 상점에서는 별도의 업데이트가 필요하지 않습니다.
        pass
    
    def render(self, surface):
        if self._is_shop_mode():
            self._render_shop(surface)
        else:
            self._render_inventory(surface)
    
    def _render_shop(self, surface):
        # 상점 화면을 렌더링합니다.
        surface.fill(THEME["bg"])
        
        # 메인 패널을 표시합니다.
        panel = pygame.Rect(
            (self.game.width - self.panel_width) // 2,
            (self.game.height - self.panel_height) // 2,
            self.panel_width,
            self.panel_height
        )
        draw_panel(surface, panel)
        
        # 제목을 표시합니다.
        title = self.font.render("상점", True, (255, 255, 100))
        surface.blit(title, (panel.x + 20, panel.y + 20))
        
        # 페이지 탭을 표시합니다.
        tab_y = panel.y + 50
        for i, page in enumerate(self.pages):
            color = (255, 255, 0) if i == self.current_page else THEME["text"]
            tab_text = self.font.render(f"[{page}]", True, color)
            tab_x = panel.x + 20 + i * 120
            surface.blit(tab_text, (tab_x, tab_y))
        
        # 아이템 목록을 표시합니다.
        items = self._get_current_shop_items()
        item_y = tab_y + 40
        
        if not items:
            no_items = self.font.render("아이템이 없습니다.", True, THEME["text"])
            surface.blit(no_items, (panel.x + 20, item_y))
            return
        
        for i, item in enumerate(items):
            # 선택 항목을 강조합니다.
            color = (255, 255, 0) if i == self.selected_item else THEME["text"]
            
            # 아이템 정보를 표시합니다.
            item_text = f"{item.name} - {item.price} 골드"
            if item.effect:
                item_text += f" ({item.effect})"
            
            text_surface = self.font.render(item_text, True, color)
            surface.blit(text_surface, (panel.x + 20, item_y + i * 25))
        
        # 조작법 안내를 표시합니다.
        controls = [
            "← → : 페이지 변경",
            "↑ ↓ : 아이템 선택",
            "Enter/Space : 구매",
            "Tab : 인벤토리 보기",
            "B : 나가기"
        ]
        
        control_y = panel.y + panel.height - 80
        for i, control in enumerate(controls):
            control_text = self.small_font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (panel.x + 20, control_y + i * 18))
    
    def _render_inventory(self, surface):
        # 인벤토리 화면을 렌더링합니다.
        surface.fill(THEME["bg"])
        
        # 메인 패널을 표시합니다.
        panel = pygame.Rect(
            (self.game.width - self.panel_width) // 2,
            (self.game.height - self.panel_height) // 2,
            self.panel_width,
            self.panel_height
        )
        draw_panel(surface, panel)
        
        # 제목을 표시합니다.
        title = self.font.render("인벤토리", True, (255, 255, 100))
        surface.blit(title, (panel.x + 20, panel.y + 20))
        
        # 탭을 표시합니다.
        tab_y = panel.y + 50
        for i, tab in enumerate(self.tabs):
            color = (255, 255, 0) if i == self.tab_index else THEME["text"]
            tab_text = self.font.render(f"[{tab}]", True, color)
            tab_x = panel.x + 20 + i * 80
            surface.blit(tab_text, (tab_x, tab_y))
        
        # 아이템 목록을 표시합니다.
        items = self._get_current_inventory_items()
        item_y = tab_y + 40
        
        if not items:
            no_items = self.font.render("아이템이 없습니다.", True, THEME["text"])
            surface.blit(no_items, (panel.x + 20, item_y))
        else:
            for i, item_name in enumerate(items):
                color = (255, 255, 0) if i == self.item_index else THEME["text"]
                item_text = self.font.render(item_name, True, color)
                surface.blit(item_text, (panel.x + 20, item_y + i * 22))
        
        # 조작법 안내를 표시합니다.
        controls = [
            "← → : 탭 변경",
            "↑ ↓ : 아이템 선택",
            "Tab : 상점 보기",
            "B : 나가기"
        ]
        
        control_y = panel.y + panel.height - 80
        for i, control in enumerate(controls):
            control_text = self.small_font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (panel.x + 20, control_y + i * 18))
