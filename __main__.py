import os
import sys
import pygame

from core.game import Game
from scenes.overworld import Overworld
from scenes.battle import Battle
from scenes.character import Character
from scenes.battle import Combatant, Item
from scenes.title import TitleScreen


def main():
    # 화면 크기 기본값으로 설정함
    game = Game(640, 480, "네모의 꿈")

    # 타이틀 화면부터 시작함
    from scenes.title import TitleScreen
    game.push_state(TitleScreen(game))

    # 오버월드 입력 처리는 각 씬에서 담당함

    # 파티/인벤토리 없으면 기본값 초기화함
    if not getattr(game, "party", None):
        cecil = Combatant("겨울이", max_hp=60, atk=10, speed=140, is_enemy=False)
        rydia = Combatant("가을이", max_hp=40, atk=7, speed=120, is_enemy=False)
        game.party = [cecil, rydia]
    if not getattr(game, "inventory", None):
        game.inventory = [
            Item("포션", "consumable", 0, "HP 30 회복", hp_bonus=30),  # HP 부족할 때 사용함
            Item("해독약", "consumable", 0, "상태이상 해제"),         # 중독 등 상태이상 해제함
            Item("목검", "weapon", 0, "공격력 +3", atk_bonus=3),        # 초기 무기로 사용함
        ]

    # 게임 루프 시작함
    game.run()


if __name__ == "__main__":
    main()


