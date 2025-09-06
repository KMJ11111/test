import pygame

from .state import State


class Game:
    # 게임 핵심 클래스임. 창 생성, 시간 관리, 상태 전환 담당함

    def __init__(self, width=640, height=480, title="RPG"):
        # Pygame 초기화함(초기화 안 하면 오류 날 수 있음)
        pygame.init()
        pygame.font.init()

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))  # 화면 생성함
        pygame.display.set_caption(title)  # 창 제목 설정함

        self.clock = pygame.time.Clock()  # FPS 동기화용 시계임
        self.is_running = True  # 종료 전까지 실행함
        self.state_stack = []  # 씬 스택(타이틀, 전투 등)임
        
        # 저장 데이터 호환용 스키마 버전임
        self.schema_version = 1

        # 골드/보석 기본값 초기화함
        self.gold = 0
        self.gems = 0
        self.inventory = []
        
        # 퀘스트는 초기 비어 있음. 게임 내 NPC 상호작용으로 추가됨
        self.quests = []

    def push_state(self, state):
        # 새 씬 스택에 추가하고 on_enter 호출함
        self.state_stack.append(state)
        state.on_enter()

    def pop_state(self):
        # 스택 비어 있으면 None 반환함
        if not self.state_stack:
            return None
        # 맨 위 씬 제거하고 on_exit 호출함
        top = self.state_stack.pop()
        top.on_exit()
        return top

    def current_state(self):
        # 현재 활성화된 씬 반환함
        if not self.state_stack:
            return None
        return self.state_stack[-1]

    def run(self):
        # 메인 루프: 입력 처리, 업데이트, 렌더링 반복함
        while self.is_running:
            delta_time = self.clock.tick(60) / 1000.0  # 60 FPS 기준 경과 시간 계산함
            if not self.state_stack:
                self.is_running = False  # 씬 없으면 종료함
                break
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False  # 창 닫기 이벤트 발생 시 종료함
                else:
                    current = self.current_state()
                    if current is not None:
                        current.handle_event(event)  # 입력 처리함
            current = self.current_state()
            if current is not None:
                current.update(delta_time)  # 게임 로직 업데이트함
            self.screen.fill((0, 0, 0))  # 배경 먼저 그림
            current = self.current_state()
            if current is not None:
                current.render(self.screen)  # 현재 씬 렌더링함
            pygame.display.flip()  # 화면에 반영함
        pygame.quit()  # Pygame 종료함


