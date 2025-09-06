class State:
    # 모든 화면(씬)의 기본 틀 제공하는 베이스 클래스임
    def __init__(self, game):
        self.game = game  # 게임 본체에 접근하기 위한 참조임

    def on_enter(self):
        # 씬 진입 시 한 번 호출됨. 필요 없으면 구현 안 해도 됨
        pass

    def on_exit(self):
        # 씬 이탈 시 한 번 호출됨. 정리 필요하면 여기서 수행함
        pass

    def handle_event(self, event):
        # 키보드/마우스 입력 처리함
        pass

    def update(self, delta_time):
        # 매 프레임 로직 업데이트함. delta_time은 경과 시간(초)임
        pass

    def render(self, surface):
        # 화면 그리기 처리 수행함
        pass


