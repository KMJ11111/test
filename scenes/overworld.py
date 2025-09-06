import pygame

from core.state import State
from world.world import Camera, TileMap
from ui.ui import THEME, draw_panel, get_font, draw_text_panel, blit_text
from .character import Character
from .quests import Quest
# Town 기능은 Overworld에 통합됨
from .battle import Battle
from .menu import Menu
from world.world import generate_horizontal_world


class Overworld(State):
    # 오버월드: 이동/마을/적 조우/퀘스트 요약 패널 관리함
    def __init__(self, game):
        super().__init__(game)
        # world_seed가 있으면 재현 가능한 맵 생성함
        seed = getattr(self.game, "world_seed", None)
        tiles = generate_horizontal_world(chunks=6, width=20, height=10, seed=seed)
        self.tilemap = TileMap(tiles, tile_size=32)
        world_w = self.tilemap.cols * self.tilemap.tile_size
        world_h = self.tilemap.rows * self.tilemap.tile_size
        self.camera = Camera((self.game.width, self.game.height), (world_w, world_h))

        self.player_speed = 120.0
        self.player_size = (16, 24)
        start_x = 2 * self.tilemap.tile_size
        start_y = 2 * self.tilemap.tile_size
        self.player_rect = pygame.Rect(start_x, start_y, *self.player_size)

        self.enemies = []
        self.enemy_dirs = []
        self.enemy_speed = 60.0
        
        # 적 리젠 시스템 위한 변수임
        self.defeated_enemies = []  # 패배한 적들의 정보 저장
        self.respawn_timer = 60.0  # 리젠 시간(초)
        
        # 초기 적 생성함(8가지 타입)
        for i in range(8):
            ex = start_x + 100 + i * 70
            ey = start_y + 40 + (i % 2) * 60
            self.enemies.append(pygame.Rect(ex, ey, 16, 16))
            # world_seed가 있으면 좌우 방향도 고정함
            if seed is not None:
                self.enemy_dirs.append(pygame.Vector2(1 if (i % 2 == 0) else -1, 0))
            else:
                self.enemy_dirs.append(pygame.Vector2(1 if i % 2 == 0 else -1, 0))

        self.town_value = 2
        self.font = get_font(14)
        self.encounter_cooldown = 0.0
        self.dialog_lines = []
        self.dialog_timer = 0.0
        # UI: 메뉴 버튼(햄버거 아이콘)
        self.menu_btn_size = (30, 22)
        self.menu_btn_margin = 10
        
        # 퀘스트 패널 상태(아코디언 형식)
        self.expanded_quests = set()
        self.quest_click_areas = []
        self.quest_panel_collapsed = False
        
        # 마을 모드 관련 변수들임
        self.is_in_town = False
        self.town_player_rect = pygame.Rect(2*32, 5*32, 16, 24)
        self.town_player_speed = 120.0
        self.town_shop_rect = pygame.Rect(6*32, 2*32, 32, 32)
        self.town_quest_rect = pygame.Rect(10*32, 2*32, 32, 32)
        # 마을 크기 확장(가로/세로 증가, 외곽 벽 유지)
        self.town_tiles = [
            [1]*26,
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]+[0]*24+[1],
            [1]*26,
        ]
        self.town_tilemap = TileMap(self.town_tiles, tile_size=32)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.is_running = False
            elif event.key == pygame.K_i:
                self.game.push_state(Character(self.game))
            elif event.key == pygame.K_b:  # B키로 상점 열기
                from .shop import Shop
                self.game.push_state(Shop(self.game))
            elif event.key == pygame.K_RETURN:
                # Enter 키는 더 이상 마을 입장에 사용하지 않음
                pass
            elif event.key == pygame.K_e:
                # E 키는 오버월드에서만 대화용으로 사용
                if not self.is_in_town:
                    nearest = None
                    nearest_dist = 999999
                    for er in self.enemies:
                        d = (er.centerx - self.player_rect.centerx) ** 2 + (er.centery - self.player_rect.centery) ** 2
                        if d < nearest_dist and d <= (48 * 48):
                            nearest = er
                            nearest_dist = d
                    if nearest is not None:
                        self.dialog_lines = ["안녕, 여행자!", "이 길은 위험하니 조심해."]
                        self.dialog_timer = 3.0
            elif event.key == pygame.K_g and self.is_in_town:
                self._exit_town()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 마을에서 나가기 버튼 클릭
            if self.is_in_town:
                exit_button_rect = pygame.Rect(self.game.width - 120, 10, 100, 30)
                if exit_button_rect.collidepoint(event.pos):
                    self._exit_town()
                    return
            
            # 메뉴 버튼 클릭 (오른쪽 상단)
            btn_w, btn_h = self.menu_btn_size
            rect = pygame.Rect(self.game.width - btn_w - self.menu_btn_margin, self.menu_btn_margin, btn_w, btn_h)
            if rect.collidepoint(event.pos):
                self.game.push_state(Menu(self.game))
            
            # 퀘스트창 접기/펼치기 버튼 
            if self.quest_panel_collapsed:
                panel_width = 120
            else:
                panel_width = 280
            panel_x = self.game.width - panel_width - 10
            panel_y = 10
            quest_collapse_btn = pygame.Rect(panel_x + 10, panel_y + 8, 40, 20)
            if quest_collapse_btn.collidepoint(event.pos):
                self.quest_panel_collapsed = not self.quest_panel_collapsed
                # 접히면 펼쳐진 항목 초기화
                if self.quest_panel_collapsed:
                    self.expanded_quests.clear()
            
            # 퀘스트 아코디언 클릭 (펼치기/접기)
            if not self.quest_panel_collapsed:
                for i, quest_rect in enumerate(self.quest_click_areas):
                    if quest_rect.collidepoint(event.pos):
                        quest_id = i
                        if quest_id in self.expanded_quests:
                            self.expanded_quests.remove(quest_id)
                        else:
                            self.expanded_quests.add(quest_id)
                        break

    def update(self, delta_time):
        # 마을 모드일 땐 마을 업데이트만 수행
        if self.is_in_town:
            self._update_town(delta_time)
            if self.dialog_timer > 0:
                self.dialog_timer = max(0.0, self.dialog_timer - delta_time)
            return

        if self.encounter_cooldown > 0.0:
            self.encounter_cooldown = max(0.0, self.encounter_cooldown - delta_time)
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction.x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction.x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            direction.y -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction.y += 1

        if direction.length_squared() > 0:
            direction = direction.normalize()
            move = direction * self.player_speed * delta_time
            new_rect = self.player_rect.move(int(move.x), 0)
            if not self.tilemap.rect_collides(new_rect):
                self.player_rect = new_rect
            new_rect = self.player_rect.move(0, int(move.y))
            if not self.tilemap.rect_collides(new_rect):
                self.player_rect = new_rect

        for idx, enemy_rect in enumerate(self.enemies):
            dir_vec = self.enemy_dirs[idx]
            enemy_move = dir_vec * self.enemy_speed * delta_time
            new_enemy = enemy_rect.move(int(enemy_move.x), 0)
            if self.tilemap.rect_collides(new_enemy):
                dir_vec.x *= -1
            else:
                self.enemies[idx] = new_enemy
            new_enemy = self.enemies[idx].move(0, int(enemy_move.y))
            if self.tilemap.rect_collides(new_enemy):
                dir_vec.y *= -1
            else:
                self.enemies[idx] = new_enemy

        # 마을 접촉 감지 (마을에 있지 않을 때만)
        if not self.is_in_town and self.tilemap.rect_on_tile_value(self.player_rect, self.town_value):
            self._enter_town()
        
        if self.encounter_cooldown <= 0.0:
            for idx, er in enumerate(self.enemies):
                if self.player_rect.colliderect(er):
                    self.enemies[idx].x += 32
                    self.encounter_cooldown = 2.0
                    # 오버월드 적 목록을 전투로 전달하기 위해 저장
                    self.game.overworld_enemies = self.enemies
                    # 전투로 진입하면서 인덱스 전달
                    self.game.push_state(Battle(self.game, enemy_index=idx))
                    break

        if self.dialog_timer > 0:
            self.dialog_timer = max(0.0, self.dialog_timer - delta_time)
        
        # 전투 승리 후: 해당 적 제거 및 리젠 큐에 등록
        defeated_enemy_index = getattr(self.game, "defeated_enemy_index", None)
        if defeated_enemy_index is not None and 0 <= defeated_enemy_index < len(self.enemies):
            # 리젠에 필요한 정보 저장
            defeated_enemy = {
                'rect': self.enemies[defeated_enemy_index].copy(),
                'dir': self.enemy_dirs[defeated_enemy_index].copy(),
                'type': defeated_enemy_index % 8,  # 적 타입 저장 
                'respawn_time': self.respawn_timer  # 리젠 
            }
            self.defeated_enemies.append(defeated_enemy)
            
            # 해당 적 제거 및 방향 목록도 정리
            self.enemies.pop(defeated_enemy_index)
            # 적의 방향도 함께 제거
            if defeated_enemy_index < len(self.enemy_dirs):
                self.enemy_dirs.pop(defeated_enemy_index)
            # 제거 정보 초기화
            self.game.defeated_enemy_index = None
        
        # 적 리젠 타이머 갱신 및 스폰
        defeated_enemies_to_remove = []
        for defeated_enemy in self.defeated_enemies:
            defeated_enemy['respawn_time'] -= delta_time
            
            if defeated_enemy['respawn_time'] <= 0:
                # 리젠 시간 도달: 적 재생성
                self.enemies.append(defeated_enemy['rect'].copy())
                self.enemy_dirs.append(defeated_enemy['dir'].copy())
                
                # 제거 대상 목록에 추가 (반복 중 제거 방지)
                defeated_enemies_to_remove.append(defeated_enemy)
                
                # 알림 메시지 표시
                self.dialog_lines = [f"새로운 적이 나타났다!"]
                self.dialog_timer = 2.0
        
        # 리젠된 적들을 defeated_enemies에서 제거
        for defeated_enemy in defeated_enemies_to_remove:
            self.defeated_enemies.remove(defeated_enemy)
    
    def _enter_town(self):
        # 마을 진입
        self.is_in_town = True
        self.town_player_rect.x = 2 * 32
        self.town_player_rect.y = 5 * 32
    
    def _exit_town(self):
        # 마을에서 나가기
        self.is_in_town = False
    
    def _update_town(self, delta_time):
        # 마을 모드 업데이트
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction.x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction.x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            direction.y -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction.y += 1
        
        if direction.length_squared() > 0:
            direction = direction.normalize()
            move = direction * self.town_player_speed * delta_time
            nr = self.town_player_rect.move(int(move.x), 0)
            if not self.town_tilemap.rect_collides(nr):
                self.town_player_rect = nr
            nr = self.town_player_rect.move(0, int(move.y))
            if not self.town_tilemap.rect_collides(nr):
                self.town_player_rect = nr
        
        # 접촉식 상호작용 감지
        self._check_town_contact()
    
    def _check_town_contact(self):
        # 마을에서 접촉식 상호작용 감지
        # 상점 접촉 감지
        if self.town_player_rect.colliderect(self.town_shop_rect.inflate(10, 10)):
            from .shop import Shop
            self.game.push_state(Shop(self.game))
            return
        
        # 퀘스트 접촉 감지
        if self.town_player_rect.colliderect(self.town_quest_rect.inflate(10, 10)):
            self._handle_quest_interaction()
            return
    
    def _handle_town_interaction(self):
        # 마을 상호작용 처리
        if self.town_player_rect.colliderect(self.town_shop_rect.inflate(10, 10)):
            from .shop import Shop
            self.game.push_state(Shop(self.game))
        elif self.town_player_rect.colliderect(self.town_quest_rect.inflate(10, 10)):
            self._handle_quest_interaction()
    
    def _handle_quest_interaction(self):
        # 퀘스트 상호작용 처리
        quests = getattr(self.game, "quests", []) or []

        # 퀘스트가 비어 있으면 NPC가 처음으로 퀘스트를 제공
        if not quests:
            from .quests import create_sample_quests
            quests = create_sample_quests()
            self.game.quests = quests

        # 아직 수락하지 않은 퀘스트가 있으면 하나 수락
        available_quests = [q for q in quests if not q.accepted]
        if available_quests:
            quest = available_quests[0]
            quest.accept()
            self.dialog_lines = [
                f"퀘스트 수락: {quest.title}",
                quest.description,
                "오버월드에서 진행도를 확인하세요!",
            ]
            self.dialog_timer = 4.0
        else:
            # 완료된 퀘스트 보상 처리
            completed_quests = [q for q in quests if q.completed and not getattr(q, 'rewarded', False)]
            if completed_quests:
                for quest in completed_quests:
                    if not hasattr(quest, 'rewarded'):
                        quest.rewarded = False
                    if not quest.rewarded:
                        party = getattr(self.game, "party", [])
                        if party:
                            levelup_messages = []
                            for member in party:
                                if quest.reward_exp > 0:
                                    msgs = member.gain_exp(quest.reward_exp)
                                    levelup_messages.extend(msgs)
                            if quest.reward_gold > 0:
                                self.game.gold = getattr(self.game, "gold", 0) + quest.reward_gold
                            quest.rewarded = True
                            reward_messages = [f"퀘스트 완료: {quest.title}"]
                            if quest.reward_exp > 0:
                                reward_messages.append(f"경험치 {quest.reward_exp} 획득!")
                                if levelup_messages:
                                    reward_messages.append("레벨업!")
                                    for msg in levelup_messages[:3]:
                                        reward_messages.append(msg)
                            if quest.reward_gold > 0:
                                reward_messages.append(f"골드 {quest.reward_gold} 획득!")
                            self.dialog_lines = reward_messages
                            self.dialog_timer = 6.0
                            break
            else:
                self.dialog_lines = ["수락한 퀘스트가 없어요.", "NPC에게 퀘스트를 받아보세요!"]
                self.dialog_timer = 3.0
        
        # 퀘스트 클릭 영역 초기화
        self.quest_click_areas.clear()
    
    def _render_town(self, surface):
        # 마을 렌더링
        # 마을 타일맵 렌더링
        self.town_tilemap.draw(surface, self.camera.offset)
        
        # 상점과 퀘스트 NPC 표시(원형)
        shop_center = (self.town_shop_rect.centerx, self.town_shop_rect.centery)
        quest_center = (self.town_quest_rect.centerx, self.town_quest_rect.centery)
        shop_radius = min(self.town_shop_rect.width, self.town_shop_rect.height) // 2
        quest_radius = min(self.town_quest_rect.width, self.town_quest_rect.height) // 2
        pygame.draw.circle(surface, (255, 100, 100), shop_center, shop_radius)  # 상점 (빨간색)
        pygame.draw.circle(surface, (100, 255, 100), quest_center, quest_radius)  # 퀘스트 (초록색)
        
        # 상점과 퀘스트 라벨
        shop_label = self.font.render("상점", True, (255, 255, 255))
        quest_label = self.font.render("퀘스트", True, (255, 255, 255))
        
        surface.blit(shop_label, (self.town_shop_rect.x + 2, self.town_shop_rect.y + 8))
        surface.blit(quest_label, (self.town_quest_rect.x + 2, self.town_quest_rect.y + 8))
        
        # 플레이어 렌더링
        pygame.draw.rect(surface, (100, 100, 255), self.town_player_rect)  # 플레이어 (파란색)
        
        # 마을 모드 안내 텍스트
        hint_text = "접촉시 자동 상호작용"
        hint_surface = self.font.render(hint_text, True, (230, 230, 230))
        hint_rect = pygame.Rect(10, 10, 300, 30)
        pygame.draw.rect(surface, (32, 32, 48), hint_rect, border_radius=4)
        pygame.draw.rect(surface, (200, 200, 200), hint_rect, 1, border_radius=4)
        surface.blit(hint_surface, (hint_rect.x + 10, hint_rect.y + 8))
        
        # 나가기 버튼
        exit_button_rect = pygame.Rect(self.game.width - 120, 10, 100, 30)
        pygame.draw.rect(surface, (150, 50, 50), exit_button_rect, border_radius=4)
        pygame.draw.rect(surface, (200, 200, 200), exit_button_rect, 1, border_radius=4)
        exit_text = self.font.render("나가기", True, (255, 255, 255))
        exit_text_rect = exit_text.get_rect(center=exit_button_rect.center)
        surface.blit(exit_text, exit_text_rect)
        
        # 퀘스트 완료 체크 및 보상 지급
        self._check_quest_completion()
        
        # 파티 상태 확인 (모든 파티원이 죽었는지 체크)
        self._check_party_status()
    
    def _check_quest_completion(self):
        # 완료된 퀘스트 확인 및 보상 지급
        quests = getattr(self.game, "quests", []) or []
        if not quests:
            return
        
        for quest in quests:
            if (hasattr(quest, 'accepted') and 
                quest.accepted and 
                quest.completed and 
                not hasattr(quest, 'rewarded')):
                
                # 보상 지급
                self._give_quest_reward(quest)
                quest.rewarded = True
    
    def _give_quest_reward(self, quest):
        # 퀘스트 완료 보상 지급
        party = getattr(self.game, "party", [])
        if not party:
            return
        
        # 경험치와 골드 보상 지급
        levelup_messages = []
        
        for member in party:
            if quest.reward_exp > 0:
                # 경험치 지급 및 레벨업 처리
                member_messages = member.gain_exp(quest.reward_exp)
                levelup_messages.extend(member_messages)
        
        # 골드 보상
        if quest.reward_gold > 0:
            if hasattr(self.game, "gold"):
                self.game.gold += quest.reward_gold
            else:
                self.game.gold = quest.reward_gold
        
        # 보상 메시지 표시
        if quest.reward_exp > 0:
            self.dialog_lines = [f"퀘스트 완료! 경험치 {quest.reward_exp} 획득!"]
            if levelup_messages:
                self.dialog_lines.append("레벨업!")
                # 레벨업 상세 정보 추가 (최대 2개)
                for msg in levelup_messages[:2]:
                    self.dialog_lines.append(msg)
        elif quest.reward_gold > 0:
            self.dialog_lines = [f"퀘스트 완료! 골드 {quest.reward_gold} 획득!"]
        
        self.dialog_timer = 4.0
    
    def _check_party_status(self):
        # 모든 파티원 사망 시 게임오버로 전환
        party = getattr(self.game, "party", [])
        if party:
            # 모든 파티원이 죽었는지 확인
            all_dead = all(not member.is_alive() for member in party)
            if all_dead:
                # 게임오버 상태로 전환
                from .title import TitleScreen
                title_screen = TitleScreen(self.game)
                title_screen.set_game_over_mode()
                self.game.push_state(title_screen)
     
    def _render_quest_panel(self, surface):
        # 우측 퀘스트 패널(아코디언)
        # 퀘스트는 시작 시 비어 있을 수 있음
        quests = getattr(self.game, "quests", []) or []
        
        # 활성 퀘스트만 필터링 (수락되었지만 완료되지 않은 퀘스트)
        active_quests = [q for q in quests if hasattr(q, 'accepted') and q.accepted and not q.completed]
        
        # 활성 퀘스트가 없으면 패널은 빈 상태로 안내만 표시
        
        # 접힌 상태일 때는 작은 패널만 표시
        if self.quest_panel_collapsed:
            panel_width = 120
            panel_height = 35
            panel_x = self.game.width - panel_width - 10
            panel_y = 10
            
            # 접힌 퀘스트 패널 그리기
            quest_panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
            draw_panel(surface, quest_panel, shadow=False)
            
            # 제목(버튼과 겹치지 않게 오른쪽으로)
            title_text = "퀘스트"
            title_surface = self.font.render(title_text, True, (255, 255, 100))
            surface.blit(title_surface, (panel_x + 60, panel_y + 10))
            
            # 펼치기 버튼(좌측)
            expand_btn = pygame.Rect(panel_x + 10, panel_y + 8, 40, 20)
            pygame.draw.rect(surface, (100, 150, 255), expand_btn, border_radius=3)
            pygame.draw.rect(surface, (200, 200, 200), expand_btn, 1, border_radius=3)
            expand_text = "▼"
            expand_surface = self.font.render(expand_text, True, (255, 255, 255))
            surface.blit(expand_surface, (panel_x + 22, panel_y + 8))
            
            return
        
        # 패널 크기 계산 (내용 기반)
        panel_width = 280
        base_height = 35
        row_collapsed = 30
        line_h = self.font.get_height()
        expanded_extra = line_h + 4 + line_h  # 설명 1줄 + 보상 1줄 가정

        total_height = base_height
        if active_quests:
            for i, quest in enumerate(active_quests[:3]):
                total_height += row_collapsed
                if i in self.expanded_quests:
                    total_height += expanded_extra
        else:
            # 안내 문구 높이(두 줄 가정)
            total_height += line_h * 2 + 10
        
        panel_x = self.game.width - panel_width - 10
        panel_y = 10
        
        # 퀘스트 패널 그리기
        quest_panel = pygame.Rect(panel_x, panel_y, panel_width, total_height)
        draw_panel(surface, quest_panel, shadow=False)
        
        # 제목과 접기 버튼(좌측)
        title_text = "퀘스트"
        title_surface = self.font.render(title_text, True, (255, 255, 100))
        surface.blit(title_surface, (panel_x + 60, panel_y + 10))
        
        # 접기 버튼(좌측)
        collapse_btn = pygame.Rect(panel_x + 10, panel_y + 8, 40, 20)
        pygame.draw.rect(surface, (255, 150, 100), collapse_btn, border_radius=3)
        pygame.draw.rect(surface, (200, 200, 200), collapse_btn, 1, border_radius=3)
        collapse_text = "▲"
        collapse_surface = self.font.render(collapse_text, True, (255, 255, 255))
        surface.blit(collapse_surface, (panel_x + 22, panel_y + 8))
        
        # 퀘스트 목록 (아코디언 형식)
        y_offset = base_height
        self.quest_click_areas.clear()

        if not active_quests:
            empty_lines = ["수락한 퀘스트 없음", "마을 NPC에게서 퀘스트 받기"]
            for idx, line in enumerate(empty_lines):
                surf = self.font.render(line, True, (200, 200, 200))
                surface.blit(surf, (panel_x + 15, panel_y + y_offset + idx * (line_h + 2)))
        else:
            for i, quest in enumerate(active_quests[:3]):
                # 퀘스트 제목과 진행도
                title_text = getattr(quest, 'title', '알 수 없는 퀘스트')
                progress = getattr(quest, 'progress', 0)
                target_count = getattr(quest, 'target_count', 1)

                quest_text = f"{title_text} ({progress}/{target_count})"
                quest_color = (100, 255, 100) if progress >= target_count else (255, 255, 255)
                quest_surface = self.font.render(quest_text, True, quest_color)
                surface.blit(quest_surface, (panel_x + 15, panel_y + y_offset))

                # 클릭 영역 저장(접힌 행 높이)
                quest_rect = pygame.Rect(panel_x + 10, panel_y + y_offset - 3, panel_width - 20, row_collapsed)
                self.quest_click_areas.append(quest_rect)

                # 펼쳐진 상태면 상세 정보
                if i in self.expanded_quests:
                    y_offset += row_collapsed
                    description = getattr(quest, 'description', '설명 없음')
                    desc_surface = self.font.render(description, True, (200, 200, 200))
                    surface.blit(desc_surface, (panel_x + 20, panel_y + y_offset))
                    y_offset += line_h + 4

                    reward_text = "보상: "
                    if getattr(quest, 'reward_exp', 0) > 0:
                        reward_text += f"EXP {quest.reward_exp} "
                    if getattr(quest, 'reward_gold', 0) > 0:
                        reward_text += f"골드 {quest.reward_gold}"
                    reward_surface = self.font.render(reward_text, True, (255, 215, 0))
                    surface.blit(reward_surface, (panel_x + 20, panel_y + y_offset))
                    y_offset += line_h
                else:
                    y_offset += row_collapsed

    def render(self, surface):
        self.camera.follow(self.player_rect)
        surface.fill(THEME["bg"])
        # 오버월드에서는 바닥 타일을 그리지 않음 (미니멀 연출)
        # 대신 길/벽은 희미한 오버레이로 표시하여 맵 윤곽을 제공함
        ts = self.tilemap.tile_size
        offset = self.camera.offset
        start_col = max(0, int(offset.x // ts))
        end_col = min(self.tilemap.cols, int((offset.x + surface.get_width()) // ts) + 1)
        start_row = max(0, int(offset.y // ts))
        end_row = min(self.tilemap.rows, int((offset.y + surface.get_height()) // ts) + 1)
        # 반투명 오버레이 레이어
        map_overlay = pygame.Surface((self.game.width, self.game.height), pygame.SRCALPHA)
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_value = self.tilemap.tiles[row][col]
                cx = col * ts - int(offset.x) + ts // 2
                cy = row * ts - int(offset.y) + ts // 2
                if tile_value == self.town_value:
                    pygame.draw.circle(surface, (200, 180, 100), (cx, cy), max(3, ts // 3))
                elif tile_value == 3:
                    # 길(3): 희미한 선
                    line_w = max(1, ts // 8)
                    pygame.draw.line(map_overlay, (200, 200, 200, 60), (cx - ts // 2, cy), (cx + ts // 2, cy), line_w)
                elif tile_value == 1:
                    # 벽(1): 희미한 사각형
                    r = max(3, ts // 3)
                    wall_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
                    pygame.draw.rect(map_overlay, (180, 180, 180, 50), wall_rect, 1)
        # 월드 경계(희미한 사각 프레임)
        world_w = self.tilemap.cols * ts
        world_h = self.tilemap.rows * ts
        border_rect = pygame.Rect(-int(offset.x), -int(offset.y), world_w, world_h)
        pygame.draw.rect(map_overlay, (220, 220, 220, 40), border_rect, 1)
        surface.blit(map_overlay, (0, 0))
        pr = self.player_rect.move(-int(self.camera.offset.x), -int(self.camera.offset.y))
        pygame.draw.rect(surface, (240, 224, 96), pr)
        for er in self.enemies:
            er_screen = er.move(-int(self.camera.offset.x), -int(self.camera.offset.y))
            # 적의 인덱스에 따라 다른 색깔 사용 (8가지 타입)
            enemy_index = self.enemies.index(er)
            if enemy_index % 8 == 0:
                color = (220, 90, 90)  # Imp Lv.1 - 빨간색
            elif enemy_index % 8 == 1:
                color = (90, 220, 90)  # Goblin Lv.2 - 초록색
            elif enemy_index % 8 == 2:
                color = (180, 180, 220)  # Wolf Lv.3 - 파란색
            elif enemy_index % 8 == 3:
                color = (220, 180, 90)  # Orc Lv.4 - 주황색
            elif enemy_index % 8 == 4:
                color = (150, 100, 50)  # Troll Lv.5 - 갈색
            elif enemy_index % 8 == 5:
                color = (100, 50, 150)  # Dark Knight Lv.6 - 보라색
            elif enemy_index % 8 == 6:
                color = (255, 100, 0)  # Dragon Lv.7 - 주황빨강
            else:
                color = (150, 0, 0)  # Demon Lord Lv.8 - 진한 빨강
            # 적을 동그라미로 표시 (전투 화면과 동일한 모양)
            center_x = er_screen.x + er_screen.width // 2
            center_y = er_screen.y + er_screen.height // 2
            radius = min(er_screen.width, er_screen.height) // 2
            pygame.draw.circle(surface, color, (center_x, center_y), radius)

        hint_rect = pygame.Rect(12, 12, 320, 48)
        draw_panel(surface, hint_rect, shadow=False)
        hint_text = "E: 대화  I: 상태  B: 인벤토리\n마을 접촉시 자동 입장"
        blit_text(surface, hint_text, (hint_rect.x + 10, hint_rect.y + 10), self.font, (230, 230, 230))
        
        # 퀘스트 정보 패널 (화면 오른쪽)
        self._render_quest_panel(surface)
        
        # 마을 모드 렌더링(그리기만 담당)
        if self.is_in_town:
            # 마을 그리기. 업데이트는 update()에서 처리
            self.town_tilemap.draw(surface, self.camera.offset)
            # 상점/퀘스트 NPC를 원형으로 표시
            shop_center = (self.town_shop_rect.centerx, self.town_shop_rect.centery)
            quest_center = (self.town_quest_rect.centerx, self.town_quest_rect.centery)
            shop_radius = min(self.town_shop_rect.width, self.town_shop_rect.height) // 2
            quest_radius = min(self.town_quest_rect.width, self.town_quest_rect.height) // 2
            pygame.draw.circle(surface, (255, 100, 100), shop_center, shop_radius)
            pygame.draw.circle(surface, (100, 255, 100), quest_center, quest_radius)
            shop_label = self.font.render("상점", True, (255, 255, 255))
            quest_label = self.font.render("퀘스트", True, (255, 255, 255))
            surface.blit(shop_label, (self.town_shop_rect.x + 2, self.town_shop_rect.y + 8))
            surface.blit(quest_label, (self.town_quest_rect.x + 2, self.town_quest_rect.y + 8))
            pygame.draw.rect(surface, (100, 100, 255), self.town_player_rect)
            hint_text = "접촉시 자동 상호작용\nG: 마을 나가기"
            hint_rect = pygame.Rect(10, 10, 300, 48)
            pygame.draw.rect(surface, (32, 32, 48), hint_rect, border_radius=4)
            pygame.draw.rect(surface, (200, 200, 200), hint_rect, 1, border_radius=4)
            blit_text(surface, hint_text, (hint_rect.x + 10, hint_rect.y + 10), self.font, (230, 230, 230))

        if self.dialog_timer > 0 and self.dialog_lines:
            # 대화창을 화면 중앙 상단에 표시
            dialog_x = self.game.width // 2 - 150
            dialog_y = 80
            draw_text_panel(surface, self.dialog_lines, (dialog_x, dialog_y), self.font)

        # 메뉴 버튼(햄버거) 그리기 - 화면 오른쪽 상단
        btn_w, btn_h = self.menu_btn_size
        x = self.game.width - btn_w - self.menu_btn_margin
        y = self.menu_btn_margin
        btn_rect = pygame.Rect(x, y, btn_w, btn_h)
        pygame.draw.rect(surface, (32, 32, 48), btn_rect, border_radius=4)
        pygame.draw.rect(surface, (200, 200, 200), btn_rect, 1, border_radius=4)
        # 세 줄 라인
        line_color = (230, 230, 230)
        pad = 5
        l1 = (x + pad, y + pad, btn_w - pad * 2, 2)
        l2 = (x + pad, y + btn_h // 2 - 1, btn_w - pad * 2, 2)
        l3 = (x + pad, y + btn_h - pad - 2, btn_w - pad * 2, 2)
        pygame.draw.rect(surface, line_color, pygame.Rect(*l1))
        pygame.draw.rect(surface, line_color, pygame.Rect(*l2))
        pygame.draw.rect(surface, line_color, pygame.Rect(*l3))

        # 플레이어 정보 패널 (좌측 하단)
        player_info_rect = pygame.Rect(12, self.game.height - 180, 320, 160)
        draw_panel(surface, player_info_rect, shadow=False)
        
        # 패널 제목
        title_text = "플레이어 정보"
        title_surface = self.font.render(title_text, True, (255, 255, 255))
        surface.blit(title_surface, (player_info_rect.x + 10, player_info_rect.y + 8))
        
        # 파티 정보 표시
        party = getattr(self.game, "party", [])
        if party:
            # 첫 번째 파티원 정보 표시
            player = party[0]
            # 이름과 레벨
            name_level_text = f"{player.name} Lv.{getattr(player, 'level', 1)}"
            name_surface = self.font.render(name_level_text, True, (255, 255, 100))
            surface.blit(name_surface, (player_info_rect.x + 10, player_info_rect.y + 28))
            
            # HP 표시
            hp_text = f"HP: {player.hp}/{player.max_hp}"
            hp_surface = self.font.render(hp_text, True, (255, 100, 100))
            surface.blit(hp_surface, (player_info_rect.x + 10, player_info_rect.y + 48))
            
            # HP 게이지
            hp_ratio = player.hp / max(1, player.max_hp)
            hp_gauge_rect = pygame.Rect(player_info_rect.x + 10, player_info_rect.y + 68, 280, 8)
            pygame.draw.rect(surface, (60, 60, 60), hp_gauge_rect, border_radius=4)
            hp_fill_width = int(280 * hp_ratio)
            if hp_fill_width > 0:
                hp_fill_rect = pygame.Rect(player_info_rect.x + 10, player_info_rect.y + 68, hp_fill_width, 8)
                pygame.draw.rect(surface, (255, 100, 100), hp_fill_rect, border_radius=4)
            pygame.draw.rect(surface, (200, 200, 200), hp_gauge_rect, 1, border_radius=4)
            
            # 경험치 표시
            exp = getattr(player, 'exp', 0)
            max_exp = getattr(player, 'max_exp', 100)
            exp_text = f"EXP: {exp}/{max_exp}"
            exp_surface = self.font.render(exp_text, True, (100, 255, 100))
            surface.blit(exp_surface, (player_info_rect.x + 10, player_info_rect.y + 82))
            
            # 경험치 게이지
            exp_ratio = exp / max(1, max_exp)
            exp_gauge_rect = pygame.Rect(player_info_rect.x + 10, player_info_rect.y + 102, 280, 6)
            pygame.draw.rect(surface, (60, 60, 60), exp_gauge_rect, border_radius=3)
            exp_fill_width = int(280 * exp_ratio)
            if exp_fill_width > 0:
                exp_fill_rect = pygame.Rect(player_info_rect.x + 10, player_info_rect.y + 102, exp_fill_width, 6)
                pygame.draw.rect(surface, (100, 255, 100), exp_fill_rect, border_radius=3)
            pygame.draw.rect(surface, (200, 200, 200), exp_gauge_rect, 1, border_radius=3)
            
            # 골드 표시 (노란색)
            current_gold = getattr(self.game, "gold", 0)
            gold_text = f"골드: {current_gold}"
            gold_surface = self.font.render(gold_text, True, (255, 215, 0))  # 노란색
            surface.blit(gold_surface, (player_info_rect.x + 10, player_info_rect.y + 114))
            
            # 보석 표시 (파란색)
            current_gems = getattr(self.game, "gems", 0)
            gems_text = f"보석: {current_gems}"
            gems_surface = self.font.render(gems_text, True, (100, 200, 255))  # 파란색
            surface.blit(gems_surface, (player_info_rect.x + 10, player_info_rect.y + 130))
        else:
            # 파티가 없을 때
            no_party_text = self.font.render("파티 없음", True, (200, 200, 200))
            surface.blit(no_party_text, (player_info_rect.x + 10, player_info_rect.y + 45))
        
        # 리젠 정보 표시 (우측 하단)
        if self.defeated_enemies:
            respawn_info_rect = pygame.Rect(self.game.width - 200, self.game.height - 140, 180, 120)
            draw_panel(surface, respawn_info_rect, shadow=False)
            
            # 제목
            respawn_title = "적 리젠 정보"
            respawn_title_surface = self.font.render(respawn_title, True, (255, 255, 255))
            surface.blit(respawn_title_surface, (respawn_info_rect.x + 10, respawn_info_rect.y + 8))
            
            # 각 패배한 적의 리젠 타이머 표시
            for i, defeated_enemy in enumerate(self.defeated_enemies[:3]):  # 최대 3개까지만 표시
                remaining_time = max(0, int(defeated_enemy['respawn_time']))
                enemy_type_names = ["Imp Lv.1", "Goblin Lv.2", "Wolf Lv.3", "Orc Lv.4", "Troll Lv.5", "Dark Knight Lv.6", "Dragon Lv.7", "Demon Lord Lv.8"]
                enemy_name = enemy_type_names[defeated_enemy['type']]
                
                timer_text = f"{enemy_name}: {remaining_time}초"
                timer_color = (255, 200, 100) if remaining_time <= 10 else (200, 200, 200)
                timer_surface = self.font.render(timer_text, True, timer_color)
                surface.blit(timer_surface, (respawn_info_rect.x + 10, respawn_info_rect.y + 28 + i * 20))
    
    
