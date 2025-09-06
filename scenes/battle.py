import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel, draw_gauge

ATB_RATE_DIVISOR = 150.0  # ATB 게이지 충전 속도임(값 클수록 느림)


class StatusEffect:
    # 독/기절 등 상태이상 표현함. 시간 경과에 따라 지속 시간 감소함
    def __init__(self, name, duration, type, potency=0):
        self.name = name
        self.duration = duration
        self.type = type
        self.potency = potency

    def tick(self, delta_time):
        self.duration = max(0.0, self.duration - delta_time)

    def is_active(self):
        return self.duration > 0


class Item:
    def __init__(self, name, item_type, price, effect, atk_bonus=0, hp_bonus=0, energy_bonus=0):
        self.name = name
        self.item_type = item_type  # 예: "weapon", "consumable"
        self.price = price
        self.effect = effect
        self.atk_bonus = atk_bonus
        self.hp_bonus = hp_bonus
        self.energy_bonus = energy_bonus


class Combatant:
    def __init__(self, name, max_hp, atk, speed, is_enemy=False, gold=0, level=1):
        self.name = name
        self.max_hp = max_hp
        self.atk = atk
        self.speed = speed
        self.is_enemy = is_enemy

        self.hp = self.max_hp
        self.atb = 0.0
        self.ready = False
        self.statuses = []
        self.max_energy = 100
        self.energy = self.max_energy
        
        # 레벨 시스템
        self.level = level
        self.exp = 0
        self.max_exp = self._calculate_max_exp()
        
        # 돈 시스템
        self.gold = gold
        
        # 무기 시스템
        self.equipped_weapon = None
        self.base_atk = self.atk  # 기본 공격력 저장함

    def _calculate_max_exp(self):
        return self.level * 100

    def apply_damage(self, amount):
        self.hp = max(0, self.hp - amount)

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, type):
        for s in self.statuses:
            if s.type == type and s.is_active():
                return True
        return False

    def tick_statuses(self, delta_time):
        for s in self.statuses:
            s.tick(delta_time)
        if self.has_status("poison"):
            self.apply_damage(max(0, int(1 * delta_time)))

    def tick_atb(self, delta_time):
        if self.ready or self.hp <= 0:
            return
        if self.has_status("stun"):
            return
        self.atb += delta_time * (self.speed / ATB_RATE_DIVISOR)
        if self.atb >= 1.0:
            self.atb = 1.0
            self.ready = True

    def spend_energy(self, cost):
        # 에너지 소모하여 행동 가능 여부 확인함
        if self.energy >= cost:
            self.energy -= cost
            return True
        return False

    def consume_turn(self):
        # 턴 종료: 준비 상태 해제하고 게이지 초기화함
        self.ready = False
        self.atb = 0.0

    def is_alive(self):
        # HP 0보다 크면 생존 상태임
        return self.hp > 0

    def gain_exp(self, amount):
        # 경험치 획득함. 레벨업 시 능력치 상승함
        self.exp += amount
        messages = []
        
        while self.exp >= self.max_exp:
            self.exp -= self.max_exp
            self.level += 1
            self.max_exp = self._calculate_max_exp()
            
            # 레벨업 했으니까 체력/공격/속도/에너지 조금 보너스
            self.max_hp += 5
            self.hp = self.max_hp  # HP 완전 회복함
            self.atk += 2
            self.speed += 5
            self.max_energy += 10
            self.energy = self.max_energy  # 에너지 완전 회복함
            
            messages.append(f"{self.name} 레벨업! Lv.{self.level}")
        
        return messages

    def equip_weapon(self, weapon):
        # 무기 장착 시 공격력 변경됨(기본 공격력 + 보너스)
        if hasattr(weapon, 'atk_bonus'):
            self.atk = self.base_atk + weapon.atk_bonus
        self.equipped_weapon = weapon

    def unequip_weapon(self):
        # 무기 해제하면 공격력 원래대로 복구함
        self.atk = self.base_atk
        self.equipped_weapon = None

    def get_total_atk(self):
        # 현재 총 공격력(무기 보너스 포함) 반환함
        if self.equipped_weapon and hasattr(self.equipped_weapon, 'atk_bonus'):
            return self.base_atk + self.equipped_weapon.atk_bonus
        return self.base_atk


class Skill:
    def __init__(self, name, mp_cost, power, status_inflict=None):
        self.name = name
        self.mp_cost = mp_cost
        self.power = power
        self.status_inflict = status_inflict


class Battle(State):
    def __init__(self, game, enemy_index=None):
        super().__init__(game)
        self.font = get_font(16)
        self.menu_items = ["공격", "스킬", "아이템", "도망"]
        self.selected_index = 0

        default_party = [
            Combatant("겨울이", max_hp=60, atk=10, speed=140, is_enemy=False),
            Combatant("가을이", max_hp=40, atk=7, speed=120, is_enemy=False),
        ]
        self.party = getattr(self.game, "party", default_party)
        setattr(self.game, "party", self.party)
        
        # 오버월드에서 전투 시작 시 전달받은 적 인덱스 저장
        self.enemy_index = enemy_index
        
        # 적 생성 (오버월드에서 전달받은 인덱스가 있으면 해당 적만, 없으면 기본 적들)
        if enemy_index is not None:
            # 오버월드의 적 정보를 가져와서 전투용 적 생성
            overworld_enemies = getattr(self.game, "overworld_enemies", [])
            if 0 <= enemy_index < len(overworld_enemies):
                enemy_rect = overworld_enemies[enemy_index]
                # 적의 위치에 따라 다른 타입 결정 (난이도별 레벨과 보상)
                enemy_type = enemy_index % 8  # 8가지 적 타입으로 확장
                if enemy_type == 0:
                    # 난이도 1: Imp (초급)
                    self.enemies = [Combatant("Imp Lv.1", max_hp=25, atk=5, speed=90, is_enemy=True, gold=10, level=1)]
                elif enemy_type == 1:
                    # 난이도 2: Goblin (초급)
                    self.enemies = [Combatant("Goblin Lv.2", max_hp=35, atk=7, speed=100, is_enemy=True, gold=20, level=2)]
                elif enemy_type == 2:
                    # 난이도 3: Wolf (중급)
                    self.enemies = [Combatant("Wolf Lv.3", max_hp=45, atk=9, speed=110, is_enemy=True, gold=35, level=3)]
                elif enemy_type == 3:
                    # 난이도 4: Orc (중급)
                    self.enemies = [Combatant("Orc Lv.4", max_hp=55, atk=11, speed=95, is_enemy=True, gold=50, level=4)]
                elif enemy_type == 4:
                    # 난이도 5: Troll (고급)
                    self.enemies = [Combatant("Troll Lv.5", max_hp=70, atk=14, speed=85, is_enemy=True, gold=70, level=5)]
                elif enemy_type == 5:
                    # 난이도 6: Dark Knight (고급)
                    self.enemies = [Combatant("Dark Knight Lv.6", max_hp=80, atk=16, speed=105, is_enemy=True, gold=90, level=6)]
                elif enemy_type == 6:
                    # 난이도 7: Dragon (최고급)
                    self.enemies = [Combatant("Dragon Lv.7", max_hp=100, atk=20, speed=80, is_enemy=True, gold=150, level=7)]
                else:
                    # 난이도 8: Demon Lord (보스급)
                    self.enemies = [Combatant("Demon Lord Lv.8", max_hp=120, atk=25, speed=75, is_enemy=True, gold=250, level=8)]
            else:
                # 기본 적들
                self.enemies = [
                    Combatant("Imp Lv.1", max_hp=25, atk=5, speed=90, is_enemy=True, gold=10, level=1),
                    Combatant("Goblin Lv.2", max_hp=35, atk=7, speed=100, is_enemy=True, gold=20, level=2),
                ]
        else:
            # 기본 적들
            self.enemies = [
                Combatant("Imp Lv.1", max_hp=25, atk=5, speed=90, is_enemy=True, gold=10, level=1),
                Combatant("Goblin Lv.2", max_hp=35, atk=7, speed=100, is_enemy=True, gold=20, level=2),
            ]

        self.skills = [
            Skill("Fire", mp_cost=0, power=12, status_inflict=None),
            Skill("Poison Sting", mp_cost=0, power=6, status_inflict=StatusEffect("Poison", duration=8.0, type="poison", potency=1)),
            Skill("Stun Blow", mp_cost=0, power=4, status_inflict=StatusEffect("Stun", duration=2.5, type="stun", potency=0)),
        ]

        self.message = "Enemies appear!"
        self.pending_action = None
        self.target_index = 0
        self.in_targeting = False
        self.is_animating = False
        self.anim_timer = 0.0
        self.anim_payload = None

        # 선택 흐름 관리
        self.selection_stage = "actor"  # actor → command → target
        self.ready_actor_indices = []
        self.actor_choice_idx = 0

        # 별도 메시지 
        self.result_message = ""
        self.result_timer = 0.0
        
        # 전투 시작 시 파티원 상태 초기화
        self._initialize_party_for_battle()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.is_animating:
                return
            # ESC 키 제거 - 나가기 버튼으로 대체
            elif self.selection_stage == "actor":
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.refresh_ready_list()
                    if self.ready_actor_indices:
                        self.actor_choice_idx = (self.actor_choice_idx - 1) % len(self.ready_actor_indices)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.refresh_ready_list()
                    if self.ready_actor_indices:
                        self.actor_choice_idx = (self.actor_choice_idx + 1) % len(self.ready_actor_indices)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.refresh_ready_list()
                    if self.ready_actor_indices:
                        self.selection_stage = "command"
                        self.selected_index = 0
            elif self.selection_stage == "command":
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % len(self.menu_items)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_index = (self.selected_index + 1) % len(self.menu_items)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    actor = self.get_selected_actor()
                    if actor is None or not actor.ready:
                        return
                    choice = self.menu_items[self.selected_index]
                    if choice in ("공격", "스킬"):
                        self.pending_action = choice
                        self.in_targeting = True
                        self.target_index = 0
                        self.selection_stage = "target"
                    elif choice == "아이템":
                        actor.heal(10)
                        # 아이템 사용 시 에너지도 회복 (회복량 증가)
                        actor.energy = min(actor.max_energy, actor.energy + 50)
                        actor.consume_turn()
                        self.message = f"{actor.name}이(가) 포션을 사용했다 (+10 HP, +50 에너지)"
                        self.selection_stage = "actor"
                    elif choice == "도망":
                        self.message = "도망쳤다!"
                        self.game.pop_state()
            elif self.selection_stage == "target":
                if event.key in (pygame.K_LEFT,):
                    if self.in_targeting:
                        self.target_index = (self.target_index - 1) % len(self.enemies)
                elif event.key in (pygame.K_RIGHT,):
                    if self.in_targeting:
                        self.target_index = (self.target_index + 1) % len(self.enemies)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.in_targeting:
                        self.execute_action()
                        return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 나가기 버튼 클릭
            exit_button_rect = pygame.Rect(self.game.width - 100, 10, 80, 30)
            if exit_button_rect.collidepoint(event.pos):
                self.game.pop_state()

    def update(self, delta_time):
        if self.is_animating:
            self.anim_timer -= delta_time
            if self.anim_timer <= 0.0 and self.anim_payload is not None:
                target = self.anim_payload["target"]
                damage = self.anim_payload.get("damage", 0)
                status = self.anim_payload.get("status")
                if damage:
                    target.apply_damage(damage)
                    actor = self.anim_payload.get("actor")
                    if isinstance(actor, Combatant):
                        self.result_message = f"{actor.name} → {target.name}: {damage}"
                        self.result_timer = 2.0
                    
                        # 적 처치 시 경험치와 돈 획득 및 레벨업 처리
                        if not target.is_alive() and target.is_enemy:
                            # 적별 경험치 설정
                            enemy_exp = {"Imp": 25, "Goblin": 35, "Orc": 50}
                            exp_gain = enemy_exp.get(target.name, 20)  # 기본 20
                            
                            # 돈 획득
                            gold_gain = target.gold
                            
                            # 게임에 돈 추가
                            current_gold = getattr(self.game, "gold", 0)
                            self.game.gold = current_gold + gold_gain
                            
                            # 파티 전체에게 경험치 지급
                            levelup_messages = []
                            for party_member in self.party:
                                if party_member.is_alive():
                                    member_messages = party_member.gain_exp(exp_gain)
                                    levelup_messages.extend(member_messages)
                            
                            # 경험치와 돈 획득 메시지 추가
                            if levelup_messages:
                                self.result_message = f"{target.name} 처치! 경험치 {exp_gain} + 돈 {gold_gain} 획득!"
                                self.result_timer = 3.0
                                # 레벨업 메시지도 표시
                                if len(levelup_messages) > 0:
                                    self.message = levelup_messages[0]  # 첫 번째 레벨업 메시지 표시
                            else:
                                self.result_message = f"{target.name} 처치! 경험치 {exp_gain} + 돈 {gold_gain} 획득!"
                                self.result_timer = 2.0
                    
                    # 퀘스트 진행도 업데이트(예: 몬스터 처치)
                    if not target.is_alive():
                        quests = getattr(self.game, "quests", [])
                        if quests:
                            # 몬스터 처치 관련 퀘스트 찾기
                            for quest in quests:
                                if (hasattr(quest, 'title') and 
                                    '몬스터' in quest.title and 
                                    hasattr(quest, 'accepted') and 
                                    quest.accepted and 
                                    not quest.completed):
                                    # 진행도 증가
                                    if hasattr(quest, 'progress'):
                                        quest.progress = min(quest.target_count, quest.progress + 1)
                                        # 완료 체크
                                        if quest.progress >= quest.target_count:
                                            quest.completed = True
                                            # 퀘스트 완료 시 즉시 보상 지급
                                            self._give_quest_reward(quest)
                                    break
                if status is not None:
                    target.add_status(StatusEffect(status.name, status.duration, status.type, status.potency))
                self.is_animating = False
                self.anim_payload = None
                self.selection_stage = "actor"
            return

        # 플레이어가 준비 상태인지 확인
        player_ready = any(p.ready and p.is_alive() for p in self.party)
        
        # 상태이상은 항상 업데이트
        for c in self.party + self.enemies:
            c.tick_statuses(delta_time)
        
        # 에너지 회복 (전투 중 교착 상태 방지)
        for p in self.party:
            if p.is_alive() and p.energy < p.max_energy:
                p.energy = min(p.max_energy, p.energy + int(20 * delta_time))  # 초당 20으로 증가
        
        # ATB 업데이트: 플레이어가 준비 상태이면 적의 ATB는 멈춤
        for p in self.party:
            p.tick_atb(delta_time)
        
        # 교착 상태 방지: 에너지가 부족한 캐릭터의 턴을 강제로 소모 (완화된 버전)
        for p in self.party:
            if p.ready and p.is_alive() and p.energy < 20:  # 최소 공격 비용
                # 에너지가 너무 부족할 때만 턴을 소모
                if p.energy < 15:  # 15 미만일 때만 강제 턴 소모
                    p.consume_turn()
                    self.message = f"{p.name}: 에너지 부족으로 턴을 건너뜁니다"
                # 에너지가 15-20 사이면 턴을 유지하고 에너지 회복 기다림
        
        # 추가 안전장치: 에너지가 0인 캐릭터에게 최소 에너지 부여
        for p in self.party:
            if p.is_alive() and p.energy <= 0:
                p.energy = 25  # 최소 에너지 보장
                self.message = f"{p.name}: 에너지 회복!"
        
        if not player_ready:  # 플레이어가 준비 상태가 아닐 때만 적의 ATB 증가
            for e in self.enemies:
                e.tick_atb(delta_time)

        # 적의 행동: 플레이어가 준비 상태가 아닐 때만
        if not player_ready:
            enemy_ready = [e for e in self.enemies if e.ready and e.is_alive()]
            if enemy_ready:
                enemy = enemy_ready[0]
                target = next((p for p in self.party if p.is_alive()), None)
                if target is not None:
                    self.message = f"{enemy.name}의 공격!"
                    enemy.consume_turn()
                    self.is_animating = True
                    self.anim_timer = 1.2
                    self.anim_payload = {"actor": enemy, "target": target, "damage": enemy.atk, "status": None}

        self.enemies = [e for e in self.enemies if e.is_alive()]
        self.party = [p for p in self.party if p.is_alive()]
        if not self.enemies:
            # 전투 승리 시 적의 레벨에 따라 다른 보상 제공
            defeated_enemy = None
            if hasattr(self, 'enemy_index') and self.enemy_index is not None:
                # 오버월드에서 전투를 시작한 경우, 해당 적의 정보를 가져옴
                overworld_enemies = getattr(self.game, "overworld_enemies", [])
                if 0 <= self.enemy_index < len(overworld_enemies):
                    enemy_type = self.enemy_index % 8
                    # 적 타입에 따른 보상 계산
                    if enemy_type == 0:  # Imp Lv.1
                        exp_reward = 15
                        gold_reward = 10
                        gems_reward = 0
                    elif enemy_type == 1:  # Goblin Lv.2
                        exp_reward = 25
                        gold_reward = 20
                        gems_reward = 0
                    elif enemy_type == 2:  # Wolf Lv.3
                        exp_reward = 40
                        gold_reward = 35
                        gems_reward = 1
                    elif enemy_type == 3:  # Orc Lv.4
                        exp_reward = 60
                        gold_reward = 50
                        gems_reward = 2
                    elif enemy_type == 4:  # Troll Lv.5
                        exp_reward = 85
                        gold_reward = 70
                        gems_reward = 3
                    elif enemy_type == 5:  # Dark Knight Lv.6
                        exp_reward = 115
                        gold_reward = 90
                        gems_reward = 5
                    elif enemy_type == 6:  # Dragon Lv.7
                        exp_reward = 150
                        gold_reward = 150
                        gems_reward = 8
                    else:  # Demon Lord Lv.8
                        exp_reward = 200
                        gold_reward = 250
                        gems_reward = 15
                        # 최종보스 처치 시 엔딩으로 이동
                        self._trigger_ending()
                        return
                else:
                    exp_reward = 25
                    gold_reward = 20
                    gems_reward = 0
            else:
                exp_reward = 25
                gold_reward = 20
            
            # 경험치와 골드 획득
            levelup_messages = []
            for party_member in self.party:
                if party_member.is_alive():
                    member_messages = party_member.gain_exp(exp_reward)
                    levelup_messages.extend(member_messages)
            
            # 골드 획득
            if hasattr(self.game, "gold"):
                self.game.gold += gold_reward
            else:
                self.game.gold = gold_reward
            
            # 보석 획득
            if hasattr(self.game, "gems"):
                self.game.gems += gems_reward
            else:
                self.game.gems = gems_reward
            
            # 승리 메시지
            if levelup_messages:
                if gems_reward > 0:
                    self.message = f"승리! 경험치 {exp_reward}, 골드 {gold_reward}, 보석 {gems_reward} 획득! 레벨업!"
                else:
                    self.message = f"승리! 경험치 {exp_reward}, 골드 {gold_reward} 획득! 레벨업!"
            else:
                if gems_reward > 0:
                    self.message = f"승리! 경험치 {exp_reward}, 골드 {gold_reward}, 보석 {gems_reward} 획득!"
                else:
                    self.message = f"승리! 경험치 {exp_reward}, 골드 {gold_reward} 획득!"
            
            # 전투 후 캐릭터 상태 복구
            self._restore_party_after_battle()
            
            # 퀘스트 진행도 업데이트
            self._update_quest_progress()
            
            # 오버월드에서 전투를 시작한 경우, 해당 적을 제거
            if self.enemy_index is not None:
                # 게임에 오버월드 적 제거 정보 저장
                self.game.defeated_enemy_index = self.enemy_index
            
            self.game.pop_state()
        elif not self.party:
            self.message = "Defeat..."
            # 전투 후 캐릭터 상태 복구 (패배 시에도)
            self._restore_party_after_battle()
            
            # 게임오버 상태로 전환
            from .title import TitleScreen
            self.game.pop_state()  # 현재 전투 상태 제거
            title_screen = TitleScreen(self.game)
            title_screen.set_game_over_mode()
            self.game.push_state(title_screen)

        if self.result_timer > 0.0:
            self.result_timer = max(0.0, self.result_timer - delta_time)

    def get_current_actor(self):
        for p in self.party:
            if p.ready:
                return p
        return None

    def refresh_ready_list(self):
        # 준비된 액터 인덱스 목록 갱신
        self.ready_actor_indices = [i for i, p in enumerate(self.party) if p.is_alive() and p.ready]
        if self.actor_choice_idx >= len(self.ready_actor_indices):
            self.actor_choice_idx = 0

    def get_selected_actor(self):
        # 현재 선택된 액터 반환
        self.refresh_ready_list()
        if not self.ready_actor_indices:
            return None
        if self.actor_choice_idx < len(self.ready_actor_indices):
            return self.party[self.ready_actor_indices[self.actor_choice_idx]]
        return None

    def _restore_party_after_battle(self):
        # 전투 후 파티원 상태 복구
        for party_member in self.party:
            if party_member.is_alive():
                # HP를 최대 HP의 80%로 복구 (전투 후 피로도 반영)
                party_member.hp = min(party_member.max_hp, int(party_member.max_hp * 0.8))
                
                # 에너지를 최대 에너지의 60%로 복구
                party_member.energy = min(party_member.max_energy, int(party_member.max_energy * 0.6))
                
                # ATB를 0으로 리셋
                party_member.atb = 0.0
                
                # 상태 효과 제거
                party_member.statuses.clear()
    
    def _update_quest_progress(self):
        # 전투 승리 후 퀘스트 진행도 업데이트
        quests = getattr(self.game, "quests", []) or []
        if not quests:
            return
        
        # 몬스터 처치 퀘스트 업데이트
        for quest in quests:
            if (hasattr(quest, 'title') and 
                hasattr(quest, 'accepted') and 
                quest.accepted and 
                not quest.completed):
                
                # 처치한 적의 이름 확인
                defeated_enemy_name = ""
                if self.enemies:
                    defeated_enemy_name = self.enemies[0].name
                
                # 몬스터 사냥 퀘스트 (임프, 고블린 등)
                if ('몬스터' in quest.title or '임프' in quest.title or '고블린' in quest.title) and hasattr(quest, 'progress'):
                    # 임프나 고블린을 처치했는지 확인
                    if 'Imp' in defeated_enemy_name or 'Goblin' in defeated_enemy_name:
                        quest.progress = min(quest.target_count, quest.progress + 1)
                        print(f"퀘스트 진행도 업데이트: {quest.title} - {quest.progress}/{quest.target_count} (처치한 적: {defeated_enemy_name})")
                
                # 강한 적 처치 퀘스트 (레벨 3 이상)
                elif '강한 적' in quest.title and hasattr(self, 'enemy_index') and self.enemy_index is not None:
                    enemy_type = self.enemy_index % 8
                    if enemy_type >= 2:  # Wolf Lv.3 이상
                        quest.progress = min(quest.target_count, quest.progress + 1)
                        print(f"퀘스트 진행도 업데이트: {quest.title} - {quest.progress}/{quest.target_count}")
                
                # 보스 처치 퀘스트 (Demon Lord)
                elif '보스' in quest.title and hasattr(self, 'enemy_index') and self.enemy_index is not None:
                    enemy_type = self.enemy_index % 8
                    if enemy_type == 7:  # Demon Lord Lv.8
                        quest.progress = min(quest.target_count, quest.progress + 1)
                        print(f"퀘스트 진행도 업데이트: {quest.title} - {quest.progress}/{quest.target_count}")
                
                # 완료 체크
                if hasattr(quest, 'progress') and quest.progress >= quest.target_count:
                    quest.completed = True
                    print(f"퀘스트 완료: {quest.title}")
                    # 퀘스트 완료 시 즉시 보상 지급
                    self._give_quest_reward(quest)

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
            self.message = f"퀘스트 완료! 경험치 {quest.reward_exp} 획득!"
            if levelup_messages:
                self.message += " 레벨업!"
        elif quest.reward_gold > 0:
            self.message = f"퀘스트 완료! 골드 {quest.reward_gold} 획득!"

    def _initialize_party_for_battle(self):
        # 전투 시작 시 파티원 상태 초기화
        for party_member in self.party:
            if party_member.is_alive():
                # HP가 0 이하인 경우 최소 HP로 복구
                if party_member.hp <= 0:
                    party_member.hp = max(1, int(party_member.max_hp * 0.3))  # 최소 30% HP
                
                # 에너지가 0 이하인 경우 최소 에너지로 복구
                if party_member.energy <= 0:
                    party_member.energy = max(10, int(party_member.max_energy * 0.4))  # 최소 40% 에너지
                
                # ATB를 0으로 리셋
                party_member.atb = 0.0
                
                # 상태 효과 제거
                party_member.statuses.clear()
                
                # 턴 준비 상태 리셋
                party_member.ready = False

    def execute_action(self):
        actor = self.get_selected_actor()
        if actor is None:
            self.in_targeting = False
            self.pending_action = None
            return
        if not self.enemies:
            return
        target = self.enemies[self.target_index % len(self.enemies)]
        damage = 0
        status_to_apply = None
        if self.pending_action == "공격":
            # 에너지 소모: 20
            if not actor.spend_energy(20):
                self.message = f"{actor.name}: 에너지가 부족합니다"
                # 에너지 부족 시에도 턴 소모
                actor.consume_turn()
                self.in_targeting = False
                self.pending_action = None
                self.selection_stage = "actor"
                return
            damage = actor.atk
            self.message = f"{actor.name}의 공격!"
        elif self.pending_action == "스킬":
            skill = self.skills[0]
            # 스킬 에너지 소모: 30
            if not actor.spend_energy(30):
                self.message = f"{actor.name}: 에너지가 부족합니다"
                # 에너지 부족 시에도 턴 소모
                actor.consume_turn()
                self.in_targeting = False
                self.pending_action = None
                self.selection_stage = "actor"
                return
            damage = skill.power
            status_to_apply = skill.status_inflict
            self.message = f"{actor.name} - {skill.name}!"
        actor.consume_turn()
        self.in_targeting = False
        self.pending_action = None
        self.is_animating = True
        self.anim_timer = 1.2
        self.anim_payload = {"actor": actor, "target": target, "damage": damage, "status": status_to_apply}

    def render(self, surface):
        surface.fill(THEME["bg"])
        top_h = 96
        top_rect = pygame.Rect(20, 12, self.game.width - 40, top_h)
        draw_panel(surface, top_rect)
        padding = 12
        # HP 정보 (빨간색)
        hp_text = "  ".join(f"{p.name}:{p.hp}/{p.max_hp}" for p in self.party)
        hp_surface = self.font.render(hp_text, True, (255, 100, 100))  # 빨간색
        surface.blit(hp_surface, (top_rect.x + padding, top_rect.y + padding))
        
        # 에너지 정보 (파란색)
        energy_text = "  ".join(f"{p.name}: EP {p.energy}/{p.max_energy}" for p in self.party)
        energy_surface = self.font.render(energy_text, True, (100, 150, 255))  # 파란색
        surface.blit(energy_surface, (top_rect.x + padding, top_rect.y + padding + 20))
        
        # 적 정보 (기존과 동일)
        enemy_hp = "  ".join(f"{e.name}:{e.hp}/{e.max_hp}" for e in self.enemies)
        enemy_text = self.font.render(enemy_hp, True, (220, 180, 180))
        surface.blit(enemy_text, (top_rect.x + padding, top_rect.y + padding + 40))
        
        # 현재 보유한 돈 표시 (노란색)
        current_gold = getattr(self.game, "gold", 0)
        gold_text = f"보유 금액: {current_gold} 골드"
        gold_surface = self.font.render(gold_text, True, (255, 215, 0))  # 노란색
        surface.blit(gold_surface, (top_rect.x + padding, top_rect.y + padding + 60))
        
        # 현재 보유한 보석 표시 (파란색)
        current_gems = getattr(self.game, "gems", 0)
        gems_text = f"보유 보석: {current_gems} 개"
        gems_surface = self.font.render(gems_text, True, (100, 200, 255))  # 파란색
        surface.blit(gems_surface, (top_rect.x + padding, top_rect.y + padding + 80))
        for i, p in enumerate(self.party):
            gx = top_rect.x + padding + i * 160
            gy = top_rect.y + top_h - 24
            draw_gauge(surface, gx, gy, 120, 8, p.atb)
        base_y = self.game.height // 2
        for i, e in enumerate(self.enemies):
            x = self.game.width // 2 + i * 60
            # 적의 이름에 따라 다른 색깔 사용 (8가지 타입으로 확장)
            if "Imp Lv.1" in e.name:
                color = (220, 90, 90) if e.is_alive() else (60, 60, 60)  # Imp Lv.1 - 빨간색
            elif "Goblin Lv.2" in e.name:
                color = (90, 220, 90) if e.is_alive() else (60, 60, 60)  # Goblin Lv.2 - 초록색
            elif "Wolf Lv.3" in e.name:
                color = (180, 180, 220) if e.is_alive() else (60, 60, 60)  # Wolf Lv.3 - 파란색
            elif "Orc Lv.4" in e.name:
                color = (220, 180, 90) if e.is_alive() else (60, 60, 60)  # Orc Lv.4 - 주황색
            elif "Troll Lv.5" in e.name:
                color = (150, 100, 50) if e.is_alive() else (60, 60, 60)  # Troll Lv.5 - 갈색
            elif "Dark Knight Lv.6" in e.name:
                color = (100, 50, 150) if e.is_alive() else (60, 60, 60)  # Dark Knight Lv.6 - 보라색
            elif "Dragon Lv.7" in e.name:
                color = (255, 100, 0) if e.is_alive() else (60, 60, 60)  # Dragon Lv.7 - 주황빨강
            elif "Demon Lord Lv.8" in e.name:
                color = (150, 0, 0) if e.is_alive() else (60, 60, 60)  # Demon Lord Lv.8 - 진한 빨강
            else:
                color = (180, 60, 60) if e.is_alive() else (60, 60, 60)  # 기본 빨간색
            
            # 모든 적을 동그라미로 표시
            pygame.draw.circle(surface, color, (x, base_y), 20)
            # 적의 이름을 위에 표시
            name_text = self.font.render(e.name, True, color)
            name_x = x - name_text.get_width() // 2
            surface.blit(name_text, (name_x, base_y - 40))
            # ATB 게이지 표시
            draw_gauge(surface, x - 20, base_y + 24, 40, 6, e.atb)
        for i, p in enumerate(self.party):
            x = 80 + i * 80
            color = (80, 160, 220) if p.is_alive() else (60, 60, 60)
            pygame.draw.rect(surface, color, pygame.Rect(x - 16, base_y + 60, 32, 32))
            # ATB 게이지 (노란색)
            draw_gauge(surface, x - 16, base_y + 96, 32, 6, p.atb, fill_color=(255, 255, 100))
            # HP 게이지 (빨간색), ATB 아래 표시
            hp_ratio = p.hp / max(1, p.max_hp)
            hp_gauge_rect = pygame.Rect(x - 16, base_y + 106, 32, 6)
            pygame.draw.rect(surface, (60, 60, 60), hp_gauge_rect, border_radius=3)
            if hp_ratio > 0:
                hp_fill_width = int(32 * hp_ratio)
                hp_fill_rect = pygame.Rect(x - 16, base_y + 106, hp_fill_width, 6)
                pygame.draw.rect(surface, (255, 100, 100), hp_fill_rect, border_radius=3)
            pygame.draw.rect(surface, (200, 200, 200), hp_gauge_rect, 1, border_radius=3)
            
            # HP 레이블 (빨간색)
            hp_label = self.font.render("HP", True, (255, 100, 100))
            surface.blit(hp_label, (x - 16, base_y + 114))
            
            # 에너지 게이지 (파란색), HP 아래 표시
            energy_ratio = p.energy / max(1, p.max_energy)
            energy_gauge_rect = pygame.Rect(x - 16, base_y + 116, 32, 6)
            pygame.draw.rect(surface, (60, 60, 60), energy_gauge_rect, border_radius=3)
            if energy_ratio > 0:
                energy_fill_width = int(32 * energy_ratio)
                energy_fill_rect = pygame.Rect(x - 16, base_y + 116, energy_fill_width, 6)
                pygame.draw.rect(surface, (100, 150, 255), energy_fill_rect, border_radius=3)
            pygame.draw.rect(surface, (200, 200, 200), energy_gauge_rect, 1, border_radius=3)
            
            # EP 레이블 (파란색)
            ep_label = self.font.render("EP", True, (100, 150, 255))
            surface.blit(ep_label, (x - 16, base_y + 124))
        menu_width = self.game.width - 40
        menu_height = 100
        menu_rect = pygame.Rect(20, self.game.height - menu_height - 28, menu_width, menu_height)
        draw_panel(surface, menu_rect)

        # 좌측: 행동자 선택 리스트
        left_x = menu_rect.x + padding
        left_y = menu_rect.y + padding
        ready_idxs = [i for i, p in enumerate(self.party) if p.is_alive() and p.ready]
        if not ready_idxs:
            surface.blit(self.font.render("행동자 없음", True, THEME["text"]), (left_x, left_y))
        else:
            for row, idx in enumerate(ready_idxs):
                name = self.party[idx].name
                selected = (self.selection_stage == "actor" and row == self.actor_choice_idx)
                color = (255, 255, 0) if selected else THEME["text"]
                label = ("▶ " if selected else "  ") + name
                surface.blit(self.font.render(label, True, color), (left_x, left_y + row * 20))

        # 우측: 커맨드 메뉴
        cmd_x = menu_rect.x + 180
        cmd_y = menu_rect.y + padding
        for i, label in enumerate(self.menu_items):
            selected = (self.selection_stage == "command" and i == self.selected_index)
            color = (255, 255, 0) if selected else (220, 220, 220)
            text_surface = self.font.render(label, True, color)
            surface.blit(text_surface, (cmd_x + 10, cmd_y + i * 20))

        # 별도 결과 메시지 패널(메뉴 위)
        if self.result_timer > 0.0 and self.result_message:
            info_rect = pygame.Rect(menu_rect.x, menu_rect.y - 36, menu_rect.width, 28)
            draw_panel(surface, info_rect, shadow=False)
            surface.blit(self.font.render(self.result_message, True, THEME["text"]), (info_rect.x + padding, info_rect.y + 6))

        # 타깃 선택 인디케이터
        if self.selection_stage == "target" and self.enemies:
            idx = self.target_index % len(self.enemies)
            x = self.game.width // 2 + idx * 60
            # 아래를 향하는 삼각형 (꼭짓점이 더 아래)
            pygame.draw.polygon(surface, (255, 255, 0), [(x, base_y - 6), (x - 8, base_y - 18), (x + 8, base_y - 18)])

        # 시간 정지 상태 표시
        player_ready = any(p.ready and p.is_alive() for p in self.party)
        if player_ready:
            pause_rect = pygame.Rect(self.game.width - 120, 80, 100, 30)
            draw_panel(surface, pause_rect, shadow=False)
            pause_text = self.font.render("시간 정지", True, (255, 255, 100))
            surface.blit(pause_text, (pause_rect.x + 10, pause_rect.y + 8))
        
        # 나가기 버튼
        exit_button_rect = pygame.Rect(self.game.width - 100, 10, 80, 30)
        pygame.draw.rect(surface, (150, 50, 50), exit_button_rect, border_radius=4)
        pygame.draw.rect(surface, (200, 200, 200), exit_button_rect, 1, border_radius=4)
        exit_text = self.font.render("나가기", True, (255, 255, 255))
        exit_text_rect = exit_text.get_rect(center=exit_button_rect.center)
        surface.blit(exit_text, exit_text_rect)

    def _trigger_ending(self):
        # 최종보스 처치 시 엔딩으로 이동
        from .ending import Ending
        self.game.state_stack.clear()  # 모든 상태 제거
        self.game.push_state(Ending(self.game))


