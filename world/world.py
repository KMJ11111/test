import pygame
import random


class Camera:
    # 카메라 시스템: 대상 기준으로 화면에 보여줄 영역 계산함
    
    def __init__(self, screen_size, world_size):
        self.screen_width, self.screen_height = screen_size
        self.world_width, self.world_height = world_size
        self.offset = pygame.Vector2(0, 0)
    
    def follow(self, target_rect):
        # 타깃을 화면 중앙에 위치시키기 위한 오프셋 계산함
        target_center_x = target_rect.centerx
        target_center_y = target_rect.centery
        
        # 화면 중앙 좌표임
        screen_center_x = self.screen_width // 2
        screen_center_y = self.screen_height // 2
        
        # 오프셋 계산함
        self.offset.x = target_center_x - screen_center_x
        self.offset.y = target_center_y - screen_center_y
        
        # 월드 경계 벗어나지 않도록 제한함
        self.offset.x = max(0, min(self.offset.x, self.world_width - self.screen_width))
        self.offset.y = max(0, min(self.offset.y, self.world_height - self.screen_height))


class TileMap:
    # 타일맵: 타일 충돌/타일 값 확인/렌더링 담당함
    
    def __init__(self, tiles, tile_size=32):
        self.tiles = tiles
        self.tile_size = tile_size
        self.rows = len(tiles)
        self.cols = len(tiles[0]) if tiles else 0
        
        # 타일 타입별 색상 정의
        self.tile_colors = {
            0: (100, 150, 100),  # 풀
            1: (80, 80, 80),     # 벽
            2: (200, 180, 100),  # 마을
            3: (120, 120, 120),  # 길
            4: (150, 100, 50),   # 흙
            5: (100, 100, 150),  # 물
        }
    
    def rect_collides(self, rect):
        # 사각형 포함 모든 타일 확인함
        start_col = max(0, rect.left // self.tile_size)
        end_col = min(self.cols - 1, rect.right // self.tile_size)
        start_row = max(0, rect.top // self.tile_size)
        end_row = min(self.rows - 1, rect.bottom // self.tile_size)
        
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                if self.tiles[row][col] == 1:  # 벽
                    return True
        return False
    
    def rect_on_tile_value(self, rect, tile_value):
        center_x = rect.centerx // self.tile_size
        center_y = rect.centery // self.tile_size
        
        if (0 <= center_y < self.rows and 
            0 <= center_x < self.cols):
            return self.tiles[center_y][center_x] == tile_value
        return False
    
    def draw(self, surface, offset=None):
        if offset is None:
            offset = pygame.Vector2(0, 0)
        
        # 화면에 보이는 타일만 그림
        start_col = max(0, int(offset.x // self.tile_size))
        end_col = min(self.cols, int((offset.x + surface.get_width()) // self.tile_size) + 1)
        start_row = max(0, int(offset.y // self.tile_size))
        end_row = min(self.rows, int((offset.y + surface.get_height()) // self.tile_size) + 1)
        
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_value = self.tiles[row][col]
                tile_color = self.tile_colors.get(tile_value, (0, 0, 0))
                
                # 타일 위치 계산함
                tile_x = col * self.tile_size - int(offset.x)
                tile_y = row * self.tile_size - int(offset.y)
                
                # 화면 밖 타일은 그리지 않음
                if (tile_x + self.tile_size > 0 and tile_x < surface.get_width() and
                    tile_y + self.tile_size > 0 and tile_y < surface.get_height()):
                    # 사각형 타일로 렌더링
                    tile_rect = pygame.Rect(tile_x + 1, tile_y + 1, self.tile_size - 2, self.tile_size - 2)
                    pygame.draw.rect(surface, tile_color, tile_rect)
                    # 벽(1)인 경우 테두리 표시
                    if tile_value == 1:
                        pygame.draw.rect(surface, (50, 50, 50), tile_rect, 1)


def generate_horizontal_world(chunks=6, width=20, height=10, seed=None):
    # 수평으로 확장되는 월드 생성함(seed 있으면 항상 같은 맵 생성)
    rng = random.Random(seed) if seed is not None else random
    world = []
    
    # 기본 지형 생성함
    for row in range(height):
        world_row = []
        for col in range(width * chunks):
            if row == 0 or row == height - 1:  # 상하 경계
                world_row.append(1)  # 벽
            elif col == 0 or col == width * chunks - 1:  # 좌우 경계
                world_row.append(1)  # 벽
            else:
                # 지형 타입 결정함
                if row == height // 2:  # 중앙 행은 길
                    world_row.append(3)  # 길
                elif row == height // 2 - 1 or row == height // 2 + 1:  # 길 주변
                    if rng.random() < 0.3:
                        world_row.append(1)  # 가끔 벽
                    else:
                        world_row.append(0)  # 풀
                else:
                    # 일반 지형임
                    rand = rng.random()
                    if rand < 0.05:
                        world_row.append(1)  # 5% 확률로 벽
                    elif rand < 0.1:
                        world_row.append(4)  # 5% 확률로 흙
                    elif rand < 0.15:
                        world_row.append(5)  # 5% 확률로 물
                    else:
                        world_row.append(0)  # 80% 확률로 풀
        
        world.append(world_row)
    
    # 마을 배치함
    for chunk in range(chunks):
        chunk_start = chunk * width
        chunk_end = (chunk + 1) * width
        
        # 각 청크에 마을 배치함
        if chunk % 2 == 0:  # 짝수 청크에만 마을
            village_col = chunk_start + width // 2
            village_row = height // 2
            
            if (0 < village_col < len(world[0]) - 1 and 
                0 < village_row < len(world) - 1):
                world[village_row][village_col] = 2  # 마을
                
                # 마을 주변 정리함
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        r, c = village_row + dr, village_col + dc
                        if (0 < r < len(world) - 1 and 
                            0 < c < len(world[0]) - 1 and
                            world[r][c] != 2):  # 마을이 아닌 경우
                            world[r][c] = 0  # 풀로 정리
    
    return world


def generate_forest_world(width=30, height=20, seed=None):
    # 숲 테마 월드를 생성합니다(seed 지원).
    rng = random.Random(seed) if seed is not None else random
    world = []
    
    for row in range(height):
        world_row = []
        for col in range(width):
            if row == 0 or row == height - 1 or col == 0 or col == width - 1:
                world_row.append(1)  # 경계 벽
            else:
                rand = rng.random()
                if rand < 0.15:
                    world_row.append(1)  # 15% 확률로 나무(벽)
                elif rand < 0.25:
                    world_row.append(4)  # 10% 확률로 흙
                elif rand < 0.30:
                    world_row.append(5)  # 5% 확률로 연못
                else:
                    world_row.append(0)  # 70% 확률로 풀
        
        world.append(world_row)
    
    # 중앙에 길을 만듭니다.
    center_row = height // 2
    for col in range(1, width - 1):
        world[center_row][col] = 3  # 길
    
    return world


def generate_dungeon_world(width=25, height=25, seed=None):
    # 던전 테마 월드를 생성합니다(seed 지원).
    rng = random.Random(seed) if seed is not None else random
    world = []
    
    for row in range(height):
        world_row = []
        for col in range(width):
            if row == 0 or row == height - 1 or col == 0 or col == width - 1:
                world_row.append(1)  # 외벽
            else:
                rand = rng.random()
                if rand < 0.25:
                    world_row.append(1)  # 25% 확률로 벽
                elif rand < 0.35:
                    world_row.append(4)  # 10% 확률로 흙
                else:
                    world_row.append(0)  # 65% 확률로 바닥
        
        world.append(world_row)
    
    # 중앙에 넓은 공간을 만듭니다.
    center_row, center_col = height // 2, width // 2
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            r, c = center_row + dr, center_col + dc
            if 0 < r < height - 1 and 0 < c < width - 1:
                world[r][c] = 0  # 바닥
    
    return world
