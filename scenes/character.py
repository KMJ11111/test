import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel
from .battle import Combatant, Item


class Character(State):
    # 캐릭터 상태 및 인벤토리 화면임
    
    def __init__(self, game):
        super().__init__(game)
        self.title_font = get_font(22)
        self.text_font = get_font(16)
        self.font = get_font(16)
        
        # 모드: 0=상태, 1=인벤토리
        self.mode = 0
        self.modes = ["상태", "인벤토리"]
        
        # 인벤토리 선택 상태임
        self.selected_index = 0
        self.message = "인벤토리를 확인하세요"
        
        # 인벤토리는 항상 Item 리스트 형태로 유지함
        if not hasattr(self.game, "inventory"):
            self.game.inventory = []
        elif not isinstance(self.game, object) or not isinstance(self.game.inventory, list):
            # 딕셔너리 형태일 경우 가능한 정보 바탕으로 Item 리스트 재구성함
            upgraded = []
            inv = getattr(self.game, "inventory", {}) or {}
            for name in inv.get("equipment", []):
                upgraded.append(Item(name, "weapon", 0, ""))
            for name in inv.get("consumables", []):
                upgraded.append(Item(name, "consumable", 0, ""))
            for name in inv.get("key", []):
                upgraded.append(Item(name, "key", 0, ""))
            self.game.inventory = upgraded

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            # ESC 키 제거 - I 키로 나가기
            if event.key == pygame.K_i:
                self.game.pop_state()
            elif event.key == pygame.K_TAB:
                # 모드 전환함
                self.mode = (self.mode + 1) % len(self.modes)
                self.selected_index = 0
            elif self.mode == 0:  # 상태 모드
                self._handle_status_events(event)
            else:  # 인벤토리 모드
                self._handle_inventory_events(event)
    
    def _handle_status_events(self, event):
        # 상태 모드 이벤트 처리
        pass
    
    def _handle_inventory_events(self, event):
        # 인벤토리: ↑/↓로 선택하고 Enter로 사용/착용함
        if event.key in (pygame.K_UP, pygame.K_w):
            if self.game.inventory:
                self.selected_index = (self.selected_index - 1) % len(self.game.inventory)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            if self.game.inventory:
                self.selected_index = (self.selected_index + 1) % len(self.game.inventory)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._use_item()
    
    def _use_item(self):
        # 선택된 아이템 사용하거나 착용함
        if not self.game.inventory:
            return
        
        selected_item = self.game.inventory[self.selected_index]
        party = getattr(self.game, "party", [])
        
        if not party:
            self.message = "파티가 없습니다"
            return
        
        player = party[0]  # 첫 번째 파티원 대상으로 처리
        
        if selected_item.item_type == "weapon":
            # 무기 착용/해제 동작 수행함
            if hasattr(player, 'equipped_weapon') and player.equipped_weapon == selected_item:
                # 이미 착용된 무기인 경우 해제함
                if hasattr(player, 'unequip_weapon'):
                    player.unequip_weapon()
                self.message = f"{selected_item.name} 해제됨"
            else:
                # 새로운 무기 착용함
                if hasattr(player, 'equip_weapon'):
                    player.equip_weapon(selected_item)
                    if hasattr(player, 'get_total_atk'):
                        self.message = f"{selected_item.name} 착용! ATK: {getattr(player, 'base_atk', player.atk)} → {player.get_total_atk()}"
                    else:
                        self.message = f"{selected_item.name} 착용!"
                else:
                    self.message = f"{selected_item.name} 착용!"
        else:
            # 소비 아이템 사용함
            if selected_item.name == "포션":
                if hasattr(player, 'heal'):
                    player.heal(selected_item.hp_bonus)
                else:
                    player.hp = min(player.max_hp, player.hp + selected_item.hp_bonus)
                self.message = f"{selected_item.name} 사용! HP {selected_item.hp_bonus} 회복"
            elif selected_item.name == "해독약":
                if hasattr(player, 'statuses'):
                    player.statuses = [s for s in player.statuses if getattr(s, 'type', '') != "poison"]
                self.message = f"{selected_item.name} 사용! 독 상태 해제"
            elif selected_item.name == "부활의깃털":
                if player.hp <= 0:
                    player.hp = max(1, int(player.max_hp * 0.5))
                    self.message = f"{selected_item.name} 사용! 부활!"
                else:
                    self.message = f"{selected_item.name} 사용!"
            elif selected_item.name == "에너지 드링크":
                if hasattr(player, 'energy') and hasattr(player, 'max_energy'):
                    player.energy = min(player.max_energy, player.energy + selected_item.energy_bonus)
                    self.message = f"{selected_item.name} 사용! 에너지 {selected_item.energy_bonus} 회복"
                else:
                    self.message = f"{selected_item.name} 사용!"
            elif selected_item.name == "고급 포션":
                if hasattr(player, 'heal'):
                    player.heal(selected_item.hp_bonus)
                else:
                    player.hp = min(player.max_hp, player.hp + selected_item.hp_bonus)
                self.message = f"{selected_item.name} 사용! HP {selected_item.hp_bonus} 회복"
            
            # 사용한 소비 아이템은 인벤토리에서 제거함
            self.game.inventory.pop(self.selected_index)
            if self.game.inventory:
                self.selected_index = self.selected_index % len(self.game.inventory)
            else:
                self.selected_index = 0

    def update(self, delta_time):
        # 별도 업데이트 필요 없음
        pass

    def render(self, surface):
        if self.mode == 0:
            self._render_status(surface)
        else:
            self._render_inventory(surface)
    
    def _render_status(self, surface):
        # 상태 화면 렌더링함
        surface.fill(THEME["bg"])
        
        # 제목과 모드 표시함
        title = self.title_font.render("캐릭터 상태", True, THEME["text"])
        surface.blit(title, (20, 16))
        
        # 모드 전환 안내 표시함
        mode_text = f"Tab: {self.modes[1]} 보기"
        mode_surface = self.font.render(mode_text, True, (150, 150, 150))
        surface.blit(mode_surface, (20, 40))
        
        # 파티 정보 표시함
        party = getattr(self.game, "party", []) or []
        panel_rect = pygame.Rect(20, 70, self.game.width - 40, self.game.height - 90)
        draw_panel(surface, panel_rect)
        
        if not party:
            empty = self.text_font.render("파티가 없습니다.", True, THEME["text_dim"])
            surface.blit(empty, (panel_rect.x + 16, panel_rect.y + 16))
            return
        
        # 컬럼 헤더 출력함
        col_x = [panel_rect.x + 16, panel_rect.x + 120, panel_rect.x + 220, 
                panel_rect.x + 300, panel_rect.x + 400, panel_rect.x + 520]
        header = ["이름", "레벨", "HP", "공격", "경험치", "상태이상"]
        
        for i, h in enumerate(header):
            surface.blit(self.text_font.render(h, True, THEME["text"]), (col_x[i], panel_rect.y + 12))
        
        # 파티원 정보 출력함
        y = panel_rect.y + 40
        for c in party:
            # 이름
            surface.blit(self.text_font.render(c.name, True, THEME["text"]), (col_x[0], y))
            
            # 레벨
            level_text = f"Lv.{getattr(c, 'level', 1)}"
            surface.blit(self.text_font.render(level_text, True, THEME["text"]), (col_x[1], y))
            
            # HP
            hp_text = f"{c.hp}/{c.max_hp}"
            surface.blit(self.text_font.render(hp_text, True, THEME["text"]), (col_x[2], y))
            
            # 공격력
            atk_text = str(getattr(c, 'get_total_atk', lambda: c.atk)())
            surface.blit(self.text_font.render(atk_text, True, THEME["text"]), (col_x[3], y))
            
            # 경험치
            exp = getattr(c, 'exp', 0)
            max_exp = getattr(c, 'max_exp', 100)
            exp_text = f"{exp}/{max_exp}"
            surface.blit(self.text_font.render(exp_text, True, THEME["text"]), (col_x[4], y))
            
            # 상태이상
            if hasattr(c, 'statuses') and c.statuses:
                st = ", ".join(s.name for s in c.statuses if hasattr(s, 'is_active') and s.is_active())
            else:
                st = "없음"
            surface.blit(self.text_font.render(st, True, THEME["text"]), (col_x[5], y))
            
            y += 28
        
        # 조작 안내 표시함
        controls = [
            "Tab: 인벤토리 보기",
            "ESC: 나가기"
        ]
        
        control_y = self.game.height - 60
        for i, control in enumerate(controls):
            control_text = self.font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (20, control_y + i * 20))
    
    def _render_inventory(self, surface):
        # 인벤토리 화면 렌더링함
        surface.fill(THEME["bg"])
        
        # 메인 패널 표시함
        panel_width = 500
        panel_height = 400
        panel = pygame.Rect(self.game.width//2 - panel_width//2, self.game.height//2 - panel_height//2, panel_width, panel_height)
        draw_panel(surface, panel)
        
        # 제목과 모드 전환 안내 표시함
        title_text = "인벤토리"
        title_surface = self.font.render(title_text, True, THEME["text"])
        surface.blit(title_surface, (panel.x + 16, panel.y + 12))
        
        mode_text = f"Tab: {self.modes[0]} 보기"
        mode_surface = self.font.render(mode_text, True, (150, 150, 150))
        surface.blit(mode_surface, (panel.x + 16, panel.y + 30))
        
        # 플레이어 정보 표시함
        party = getattr(self.game, "party", [])
        if party:
            player = party[0]
            player_info = f"플레이어: {player.name} Lv.{getattr(player, 'level', 1)} | ATK: "
            
            if hasattr(player, 'get_total_atk'):
                player_info += str(player.get_total_atk())
            else:
                player_info += str(player.atk)
            
            if hasattr(player, 'equipped_weapon') and player.equipped_weapon:
                player_info += f" (착용무기: {player.equipped_weapon.name})"
            else:
                player_info += " (착용무기: 없음)"
            
            player_surface = self.font.render(player_info, True, (255, 255, 100))
            surface.blit(player_surface, (panel.x + 16, panel.y + 50))
        
        # 아이템 목록 표시함
        if not self.game.inventory:
            no_items_text = "인벤토리가 비어있습니다"
            no_items_surface = self.font.render(no_items_text, True, (200, 200, 200))
            surface.blit(no_items_surface, (panel.x + 16, panel.y + 90))
        else:
            for i, item in enumerate(self.game.inventory):
                y_pos = panel.y + 90 + i * 35
                
                # 선택된 아이템 강조함
                color = (255, 255, 0) if i == self.selected_index else THEME["text"]
                
                # 아이템 이름 표시함
                name_text = item.name
                name_surface = self.font.render(name_text, True, color)
                surface.blit(name_surface, (panel.x + 16, y_pos))
                
                # 아이템 타입 표시함
                type_text = f"[{getattr(item, 'item_type', '')}]"
                type_color = (100, 255, 100) if item.item_type == "weapon" else (255, 100, 100)
                type_surface = self.font.render(type_text, True, type_color)
                surface.blit(type_surface, (panel.x + 120, y_pos))
                
                # 효과 설명 표시함
                effect_text = getattr(item, 'effect', '')
                effect_surface = self.font.render(effect_text, True, (100, 255, 100))
                surface.blit(effect_surface, (panel.x + 200, y_pos))
                
                # 착용 상태 표시함(무기인 경우)
                if (item.item_type == "weapon" and party and 
                    hasattr(party[0], 'equipped_weapon') and 
                    party[0].equipped_weapon == item):
                    equipped_text = "[착용중]"
                    equipped_surface = self.font.render(equipped_text, True, (255, 215, 0))
                    surface.blit(equipped_surface, (panel.x + 350, y_pos))
        
        # 조작 안내 표시함
        help_text = "↑↓: 선택  Enter: 사용/착용  Tab: 상태 보기  I: 나가기"
        help_surface = self.font.render(help_text, True, (200, 200, 200))
        surface.blit(help_surface, (panel.x + 16, panel.y + panel.height - 50))
        
        # 메시지 표시함
        message_surface = self.font.render(self.message, True, THEME["text"])
        surface.blit(message_surface, (panel.x + 16, panel.y + panel.height - 26))
