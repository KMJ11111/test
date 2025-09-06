import pygame


# UI 색상 테마임
THEME = {
    "bg": (16, 16, 24),
    "panel": (28, 28, 40),
    "panel_border": (210, 210, 210),
    "accent": (255, 215, 0),
    "text": (230, 230, 230),
    "text_dim": (200, 200, 200),
}


_font_cache = {}  # 폰트 캐시임


def get_font(size):
    # 지정한 크기의 폰트 반환함(캐시 사용). 한글 폰트 우선 탐색함
    if size in _font_cache:
        return _font_cache[size]
    candidates = [
        "Malgun Gothic", "맑은 고딕", "NanumGothic", "Nanum Gothic",
        "Apple SD Gothic Neo", "Noto Sans CJK KR", "Noto Sans Korean",
        "Arial Unicode MS", "Arial", "DejaVu Sans",
    ]
    font = None
    for name in candidates:
        try:
            fpath = pygame.font.match_font(name)
            if fpath:
                font = pygame.font.Font(fpath, size)
                break
        except Exception:
            pass
    if font is None:
        font = pygame.font.SysFont("arial", size)
    _font_cache[size] = font
    return font


def draw_panel(surface, rect, fill=None, border=None, border_width=2, shadow=True):
    # 기본 패널 그림(옵션: 그림자)
    fill = fill if fill is not None else THEME["panel"]
    border = border if border is not None else THEME["panel_border"]
    if shadow:
        shadow_rect = rect.move(3, 3)
        pygame.draw.rect(surface, (0, 0, 0), shadow_rect, border_radius=6)
    pygame.draw.rect(surface, fill, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, border_width, border_radius=6)


def draw_gauge(surface, x, y, w, h, ratio, fill_color=None, back_color=(60, 60, 60), border_color=(20, 20, 20)):
    # 게이지 바 그림(ratio 0~1 범위)
    fill_color = fill_color if fill_color is not None else THEME["accent"]
    pygame.draw.rect(surface, back_color, pygame.Rect(x, y, w, h), border_radius=3)
    fill_w = int(max(0.0, min(1.0, ratio)) * w)
    if fill_w > 0:
        pygame.draw.rect(surface, fill_color, pygame.Rect(x, y, fill_w, h), border_radius=3)
    pygame.draw.rect(surface, border_color, pygame.Rect(x, y, w, h), 1, border_radius=3)


def measure_text_lines(font, lines):
    # 여러 줄 텍스트 총 크기 계산함
    max_w = 0
    total_h = 0
    for line in lines:
        surf = font.render(line, True, (255, 255, 255))
        max_w = max(max_w, surf.get_width())
        total_h += surf.get_height()
    return max_w, total_h


def draw_text_panel(surface, lines, pos, font, padding=10, margin=0):
    # 텍스트 박스 그림(여러 줄 지원)
    w, h = measure_text_lines(font, lines)
    rect = pygame.Rect(pos[0], pos[1], w + padding * 2, h + padding * 2)
    draw_panel(surface, rect, shadow=False)
    y = rect.y + padding
    for line in lines:
        surf = font.render(line, True, THEME["text"])
        surface.blit(surf, (rect.x + padding, y))
        y += surf.get_height()
    return rect


def blit_text(surface, text, pos, font, color=None, line_spacing=0, max_width=None, align="left"):
    # 여러 줄(\n)과 단어 단위 줄바꿈 지원하여 텍스트 그림
    if color is None:
        color = THEME["text"]
    x, y = pos
    for raw_line in text.split("\n"):
        if max_width is None:
            line_surface = font.render(raw_line, True, color)
            line_rect = line_surface.get_rect()
            if align == "center":
                line_rect.midtop = (x, y)
            elif align == "right":
                line_rect.topright = (x, y)
            else:
                line_rect.topleft = (x, y)
            surface.blit(line_surface, line_rect)
            y += line_surface.get_height() + line_spacing
            continue
        # max_width가 있으면 단어 단위로 줄바꿈
        words = raw_line.split(" ")
        current_line = ""
        for word in words:
            test_line = word if current_line == "" else current_line + " " + word
            test_surface = font.render(test_line, True, color)
            if test_surface.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line != "":
                    line_surface = font.render(current_line, True, color)
                    line_rect = line_surface.get_rect()
                    if align == "center":
                        line_rect.midtop = (x + max_width // 2, y)
                    elif align == "right":
                        line_rect.topright = (x + max_width, y)
                    else:
                        line_rect.topleft = (x, y)
                    surface.blit(line_surface, line_rect)
                    y += line_surface.get_height() + line_spacing
                current_line = word
        if current_line != "":
            line_surface = font.render(current_line, True, color)
            line_rect = line_surface.get_rect()
            if align == "center":
                line_rect.midtop = (x + max_width // 2, y)
            elif align == "right":
                line_rect.topright = (x + max_width, y)
            else:
                line_rect.topleft = (x, y)
            surface.blit(line_surface, line_rect)
            y += line_surface.get_height() + line_spacing
    return y - pos[1]
