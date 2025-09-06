import json
import os
import pygame

from core.state import State
from ui.ui import get_font, THEME, draw_panel


class Quest:
    # 퀘스트 데이터(목표, 보상, 진행도)를 관리합니다.
    def __init__(self, id, title, description, target_count, progress=0, completed=False, accepted=False, reward_exp=0, reward_gold=0, rewarded=False):
        self.id = id
        self.title = title
        self.description = description
        self.target_count = target_count
        self.progress = progress
        self.completed = completed
        self.accepted = accepted
        self.reward_exp = reward_exp
        self.reward_gold = reward_gold
        self.rewarded = rewarded
    
    def accept(self):
        # 퀘스트를 수락합니다.
        self.accepted = True
    
    def update_progress(self, amount=1):
        # 진행도를 업데이트합니다.
        self.progress = min(self.target_count, self.progress + amount)
        if self.progress >= self.target_count:
            self.completed = True


class QuestLog(State):
    # 퀘스트 목록과 상세 정보를 표시합니다.
    
    def __init__(self, game):
        super().__init__(game)
        self.font = get_font(16)
        self.selected_index = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                quests = getattr(self.game, "quests", [])
                if quests:
                    self.selected_index = (self.selected_index - 1) % len(quests)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                quests = getattr(self.game, "quests", [])
                if quests:
                    self.selected_index = (self.selected_index + 1) % len(quests)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._accept_quest()
            elif event.key in (pygame.K_ESCAPE,):
                self.game.pop_state()

    def _accept_quest(self):
        # 선택된 퀘스트를 수락합니다.
        quests = getattr(self.game, "quests", [])
        if quests and 0 <= self.selected_index < len(quests):
            quest = quests[self.selected_index]
            if not quest.accepted and not quest.completed:
                quest.accept()

    def render(self, surface):
        surface.fill(THEME["bg"])
        panel = pygame.Rect(40, 40, self.game.width - 80, self.game.height - 80)
        draw_panel(surface, panel)
        
        title = self.font.render("퀘스트 로그", True, THEME["text"])
        surface.blit(title, (panel.x + 16, panel.y + 12))
        
        quests = getattr(self.game, "quests", [])
        if not quests:
            no_quests = self.font.render("퀘스트가 없습니다.", True, THEME["text_dim"])
            surface.blit(no_quests, (panel.x + 16, panel.y + 40))
            return
        
        for i, quest in enumerate(quests):
            y_pos = panel.y + 40 + i * 30
            color = (255, 255, 0) if i == self.selected_index else THEME["text"]
            
            # 퀘스트 상태에 따른 표시
            status = ""
            if quest.completed:
                status = " [완료]"
                color = (100, 255, 100)
            elif quest.accepted:
                status = " [진행중]"
                color = (255, 255, 100)
            else:
                status = " [수락가능]"
                color = (200, 200, 200)
            
            quest_text = f"{quest.title}{status} ({quest.progress}/{quest.target_count})"
            surface.blit(self.font.render(quest_text, True, color), (panel.x + 16, y_pos))
            
            # 선택된 퀘스트의 상세 정보 표시
            if i == self.selected_index:
                detail_y = y_pos + 20
                detail_text = f"설명: {quest.description}"
                surface.blit(self.font.render(detail_text, True, (150, 150, 150)), (panel.x + 32, detail_y))
                
                reward_text = f"보상: EXP {quest.reward_exp}, 골드 {quest.reward_gold}"
                surface.blit(self.font.render(reward_text, True, (255, 215, 0)), (panel.x + 32, detail_y + 20))
                
                if not quest.accepted and not quest.completed:
                    accept_text = "Enter: 퀘스트 수락"
                    surface.blit(self.font.render(accept_text, True, (100, 255, 100)), (panel.x + 32, detail_y + 40))


class SaveLoad(State):
    # 저장/불러오기 화면
    
    def __init__(self, game, mode="save"):
        super().__init__(game)
        self.font = get_font(16)
        self.mode = mode  # "save" 또는 "load"
        self.selected_slot = 0
        self.slots = ["슬롯 1", "슬롯 2", "슬롯 3"]
        self.save_dir = "saves"
        
        # 저장 디렉토리 생성
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_slot = (self.selected_slot - 1) % len(self.slots)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_slot = (self.selected_slot + 1) % len(self.slots)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.mode == "save":
                    self._save_game()
                else:
                    self._load_game()
            elif event.key in (pygame.K_ESCAPE,):
                self.game.pop_state()

    def _save_game(self):
        # 게임 상태를 JSON으로 저장합니다.
        slot_name = f"slot{self.selected_slot + 1}.json"
        file_path = os.path.join(self.save_dir, slot_name)
        
        try:
            # 게임 상태 데이터를 수집합니다.
            save_data = {
                "party": self._serialize_party(),
                "gold": getattr(self.game, "gold", 0),
                "gems": getattr(self.game, "gems", 0),
                "inventory": self._serialize_inventory(),
                "quests": self._serialize_quests(),
                "overworld_enemies": self._serialize_overworld_enemies(),
                "defeated_enemy_index": None,
                "world_seed": getattr(self.game, "world_seed", None),
                "schema_version": getattr(self.game, "schema_version", 1),
                "saved_at": __import__("time").strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # JSON 파일로 저장합니다.
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            # 저장 성공 메시지를 표시합니다.
            self._show_message(f"슬롯 {self.selected_slot + 1}에 저장되었습니다!")
            
        except Exception as e:
            # 저장 실패 메시지를 표시합니다.
            self._show_message(f"저장 실패: {str(e)}")

    def _load_game(self):
        # 게임 상태를 JSON에서 불러옵니다.
        slot_name = f"slot{self.selected_slot + 1}.json"
        file_path = os.path.join(self.save_dir, slot_name)
        
        if not os.path.exists(file_path):
            self._show_message("저장된 파일이 없습니다!")
            return
        
        try:
            # JSON 파일에서 데이터를 로드합니다.
            with open(file_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # 게임 상태를 복원합니다.
            self._deserialize_party(save_data.get("party", []))
            self.game.gold = save_data.get("gold", 0)
            self.game.gems = save_data.get("gems", 0)
            self.game.inventory = self._deserialize_inventory(save_data.get("inventory", []))
            self._deserialize_quests(save_data.get("quests", []))
            self.game.overworld_enemies = self._deserialize_overworld_enemies(save_data.get("overworld_enemies", []))
            self.game.defeated_enemy_index = None
            self.game.world_seed = save_data.get("world_seed", None)
            
            # 로드 성공 메시지를 표시합니다.
            self._show_message(f"슬롯 {self.selected_slot + 1}에서 불러왔습니다!")
            
            # 오버월드로 이동합니다.
            from .overworld import Overworld
            self.game.pop_state()  # 현재 상태 제거
            self.game.push_state(Overworld(self.game))
            
        except Exception as e:
            # 로드 실패 메시지를 표시합니다.
            self._show_message(f"불러오기 실패: {str(e)}")

    def _serialize_party(self):
        # 파티 정보를 JSON 직렬화 형태로 변환합니다.
        party = getattr(self.game, "party", [])
        serialized = []
        
        for member in party:
            member_data = {
                "name": member.name,
                "max_hp": member.max_hp,
                "hp": member.hp,
                "atk": member.atk,
                "speed": member.speed,
                "level": getattr(member, "level", 1),
                "exp": getattr(member, "exp", 0),
                "max_exp": getattr(member, "max_exp", 100),
                "energy": getattr(member, "energy", 100),
                "max_energy": getattr(member, "max_energy", 100),
                "base_atk": getattr(member, "base_atk", member.atk),
                "gold": getattr(member, "gold", 0),
                "equipped_weapon": None  # 무기는 이름으로 저장
            }
            
            if hasattr(member, "equipped_weapon") and member.equipped_weapon:
                member_data["equipped_weapon"] = member.equipped_weapon.name
            
            serialized.append(member_data)
        
        return serialized

    def _deserialize_party(self, party_data):
        # 파티 정보를 복원합니다.
        from .battle import Combatant
        
        party = []
        for member_data in party_data:
            member = Combatant(
                name=member_data["name"],
                max_hp=member_data["max_hp"],
                atk=member_data["atk"],
                speed=member_data["speed"],
                is_enemy=False,
                gold=member_data.get("gold", 0),
                level=member_data.get("level", 1)
            )
            
            # 추가 속성을 설정합니다.
            member.hp = member_data["hp"]
            member.level = member_data.get("level", 1)
            member.exp = member_data.get("exp", 0)
            member.max_exp = member_data.get("max_exp", 100)
            member.energy = member_data.get("energy", 100)
            member.max_energy = member_data.get("max_energy", 100)
            member.base_atk = member_data.get("base_atk", member.atk)
            member.max_exp = member_data.get("max_exp", 100)
            
            # 무기를 착용합니다(인벤토리에서 찾아 설정).
            equipped_weapon_name = member_data.get("equipped_weapon")
            if equipped_weapon_name:
                # 인벤토리에서 해당 무기 찾기
                inventory = getattr(self.game, "inventory", [])
                for item in inventory:
                    if hasattr(item, 'name') and item.name == equipped_weapon_name:
                        if hasattr(member, 'equip_weapon'):
                            member.equip_weapon(item)
                        break
            
            party.append(member)
        
        self.game.party = party

    def _serialize_quests(self):
        # 퀘스트 목록을 직렬화합니다.
        quests = getattr(self.game, "quests", [])
        serialized = []
        
        for quest in quests:
            quest_data = {
                "id": quest.id,
                "title": quest.title,
                "description": quest.description,
                "target_count": quest.target_count,
                "progress": quest.progress,
                "completed": quest.completed,
                "accepted": quest.accepted,
                "reward_exp": quest.reward_exp,
                "reward_gold": quest.reward_gold,
                "rewarded": getattr(quest, 'rewarded', False)
            }
            serialized.append(quest_data)
        
        return serialized

    def _serialize_inventory(self):
        # 인벤토리를 직렬화합니다(Item 필드만 저장).
        inventory = getattr(self.game, "inventory", [])
        serialized = []
        
        for item in inventory:
            if hasattr(item, 'name'):
                item_data = {
                    "name": item.name,
                    "item_type": getattr(item, 'item_type', ''),
                    "price": getattr(item, 'price', 0),
                    "effect": getattr(item, 'effect', ''),
                    "atk_bonus": getattr(item, 'atk_bonus', 0),
                    "hp_bonus": getattr(item, 'hp_bonus', 0),
                    "energy_bonus": getattr(item, 'energy_bonus', 0)
                }
                serialized.append(item_data)
        
        return serialized

    def _serialize_overworld_enemies(self):
        # 오버월드 적(Rect)을 저장 가능한 형태로 변환합니다.
        enemies = getattr(self.game, "overworld_enemies", [])
        serialized = []
        
        for enemy in enemies:
            if hasattr(enemy, 'x') and hasattr(enemy, 'y') and hasattr(enemy, 'width') and hasattr(enemy, 'height'):
                # pygame.Rect 객체를 딕셔너리로 변환
                enemy_data = {
                    "x": enemy.x,
                    "y": enemy.y,
                    "width": enemy.width,
                    "height": enemy.height
                }
                serialized.append(enemy_data)
        
        return serialized

    def _deserialize_inventory(self, inventory_data):
        # 인벤토리를 Item 리스트로 복원합니다.
        from .battle import Item
        
        inventory = []
        for item_data in inventory_data:
            if isinstance(item_data, dict) and 'name' in item_data:
                item = Item(
                    name=item_data["name"],
                    item_type=item_data.get("item_type", ""),
                    price=item_data.get("price", 0),
                    effect=item_data.get("effect", ""),
                    atk_bonus=item_data.get("atk_bonus", 0),
                    hp_bonus=item_data.get("hp_bonus", 0),
                    energy_bonus=item_data.get("energy_bonus", 0)
                )
                inventory.append(item)
        
        return inventory

    def _deserialize_overworld_enemies(self, enemies_data):
        # 적 Rect 리스트를 복원합니다.
        import pygame
        
        enemies = []
        for enemy_data in enemies_data:
            if isinstance(enemy_data, dict) and 'x' in enemy_data:
                enemy = pygame.Rect(
                    enemy_data["x"],
                    enemy_data["y"],
                    enemy_data["width"],
                    enemy_data["height"]
                )
                enemies.append(enemy)
        
        return enemies

    def _deserialize_quests(self, quests_data):
        # 퀘스트 리스트를 복원합니다.
        quests = []
        
        for quest_data in quests_data:
            quest = Quest(
                id=quest_data["id"],
                title=quest_data["title"],
                description=quest_data["description"],
                target_count=quest_data["target_count"],
                progress=quest_data.get("progress", 0),
                completed=quest_data.get("completed", False),
                accepted=quest_data.get("accepted", False),
                reward_exp=quest_data.get("reward_exp", 0),
                reward_gold=quest_data.get("reward_gold", 0),
                rewarded=quest_data.get("rewarded", False)
            )
            quests.append(quest)
        
        self.game.quests = quests

    def _show_message(self, message):
        # 간단한 메시지를 출력합니다.
        print(f"저장/로드: {message}")

    def update(self, delta_time):
        # 별도의 업데이트는 없습니다.
        pass

    def render(self, surface):
        surface.fill(THEME["bg"])
        panel = pygame.Rect(40, 40, self.game.width - 80, self.game.height - 80)
        draw_panel(surface, panel)
        
        # 제목을 표시합니다.
        title_text = "저장" if self.mode == "save" else "불러오기"
        title = self.font.render(title_text, True, THEME["text"])
        surface.blit(title, (panel.x + 16, panel.y + 12))
        
        # 슬롯 목록을 표시합니다.
        for i, slot in enumerate(self.slots):
            y_pos = panel.y + 40 + i * 30
            color = (255, 255, 0) if i == self.selected_slot else THEME["text"]
            
            # 슬롯 정보 표시
            slot_text = slot
            slot_file = f"slot{i + 1}.json"
            slot_path = os.path.join(self.save_dir, slot_file)
            
            if os.path.exists(slot_path):
                # 저장된 파일이 있으면 정보 표시
                try:
                    with open(slot_path, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    
                    # 저장 시간이나 파티 정보 표시
                    party = save_data.get("party", [])
                    if party:
                        slot_text += f" - {party[0]['name']} Lv.{party[0].get('level', 1)}"
                    else:
                        slot_text += " - 빈 슬롯"
                        
                except:
                    slot_text += " - 손상된 파일"
            else:
                slot_text += " - 빈 슬롯"
            
            surface.blit(self.font.render(slot_text, True, color), (panel.x + 16, y_pos))
        
        # 조작법 안내
        controls = [
            "↑↓: 슬롯 선택",
            "Enter: " + ("저장" if self.mode == "save" else "불러오기"),
            "ESC: 나가기"
        ]
        
        control_y = panel.y + panel.height - 60
        for i, control in enumerate(controls):
            control_text = self.font.render(control, True, (150, 150, 150))
            surface.blit(control_text, (panel.x + 16, control_y + i * 20))


def create_sample_quests():
    # 샘플 퀘스트 생성
    return [
        Quest(
            id="forest_imps",
            title="숲의 임프 퇴치",
            description="숲에 나타난 임프들을 5마리 처치하세요.",
            target_count=5,
            reward_exp=50,
            reward_gold=100
        ),
        Quest(
            id="strong_enemies",
            title="강한 적 처치",
            description="레벨 3 이상의 강한 적을 3마리 처치하세요.",
            target_count=3,
            reward_exp=100,
            reward_gold=200
        ),
        Quest(
            id="boss_defeat",
            title="보스 처치",
            description="강력한 보스를 처치하세요.",
            target_count=1,
            reward_exp=200,
            reward_gold=500
        ),
        Quest(
            id="level_up",
            title="레벨업",
            description="캐릭터를 3레벨 올리세요.",
            target_count=3,
            reward_exp=150,
            reward_gold=300
        )
    ]


