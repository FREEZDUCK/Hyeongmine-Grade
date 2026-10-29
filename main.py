# -*- coding: utf-8 -*-
"""형민그레이드 - 검 강화하기 스타일 강화 게임 (pygame)

조작
  Space / ↑ : 업그레이드       ↓ : 형민 판매
  S : 상점     O : 설정 (빠른 업그레이드 · 화면 크기 · 데이터 초기화)
  1 / 2 / 3 : (상점에서) 방지권 / 보험권 / 확률석 구매      Esc : 창 닫기
  ← / → : 확률석 적용 개수 줄이기 / 늘리기 (로비)
  D : 도감   (도감에서 ↑ / ↓ · 마우스 휠 = 스크롤, ← / → = 이전 / 다음 형민, Esc = 뒤로)
  도감 상세 : 카드 클릭 후 좌우 드래그 = 가로 회전 (놓으면 관성으로 돌다가 서서히 정지)
"""
import json
import math
import os
import random
import time

import pygame

# ================================================================== 설정값
W, H = 480, 820                  # 기준(논리) 해상도. 실제 창은 아래 SCALES 배율로 확대/축소
SCALES = [0.9, 1.0, 1.25, 1.5]   # 설정에서 고를 수 있는 화면 크기
FPS = 60
VERSION = "1.2.0v"
BASE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE, "assets", "images")
FONT_DIR = os.path.join(BASE, "assets", "fonts")
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".hyeongmin_grade_save.json")

# 형민 이름 리스트 : 0번부터 assets/images/0.png, 1.png ... 와 1:1 대응
# 이름 + 이미지(N.png)를 하나씩 추가하면 다음 단계가 자동으로 생긴다.
TITLES = ["형민이 머리카락", "형민이 안경", "형민 상의", "형민 목도리", "형민이 마우스",
          "형민이 애착 키캡", "실제로 사용한 형민 수저", "형민이 하의", "형민이 현금",
          "형민이 립밤", "형민이집 김장김치", "형민이 수면양말", "형민이 애착모자",
          "형민이 엔믹스 카드지갑", "형민이 갤탭 펜슬", "형민이 주민등록증",
          "형민이 키보드", "형민이의 명품 자켓", "형민이의 은밀한 폴더", "치 킨",
          "(주)박형민", "형민이 인스타 계정", "형민이 기숙사 침대", "형민이 노트북", "형민이 실착 마스크",
          "형민이 HEART", "형민이 가발", "형민이 에어팟", "형민이 손", "형민이 뇌", "형민이 생가",
          "형민 육안", "형민이의 세월", "형민 검", "형민이의 성대모사 스킬", "형민 드림카", "박형민",
          "뭉크의 형규", "형민크래프트", "로댕의 생각하는 형민(유일작)", "대 형 민", "형나리자", "형지창조",
          "형 아저씨", "형작도", "형대미술"]
MAX_LEVEL = len(TITLES) - 1

# ---- 강화 기본 공식 (데모와 동일)
PER_DECAY = 0.978                 # 단계마다 성공 확률 배율
SELL_POWER = 1.0307                 # 판매 값어치 지수
SELL_RAND = (1.1, 1.4)            # 판매 값어치 랜덤 배율
COST_POWER = 1.05                 # 업그레이드 비용 지수

START_MONEY = 100                # 새 게임 시작 자금
UPGRADE_COST_RATE = 0.17         # 현재 단계 판매 기준값의 20%를 강화비로 사용
SELL_VALUE_RANDOM = (0.9, 1.1)   # 단계별 기준 판매가에서 ±10% 변동


# ---- 황금 형민
GOLD_CHANCE = 0.01               # 업그레이드 성공 시 황금이 될 확률 (1%)
GOLD_SELL_MULT = 2                # 황금 판매 값어치 배율

# ---- 상점 가격 (가격 = max(최소가, 최고 도달 단계의 평균 판매가 × 비율))
PROTECT_PRICE_RATE = 0.15         # 파괴 방지권 : 판매가 대비 비율  ← 오르는 정도 조절
PROTECT_MIN_PRICE = 60            # 파괴 방지권 : 최소 가격
INSURANCE_PRICE_RATE = 0.07       # 파괴 보험권 : 판매가 대비 비율  ← 오르는 정도 조절
INSURANCE_MIN_PRICE = 30          # 파괴 보험권 : 최소 가격
INSURANCE_REFUND = 0.5            # 파괴 시 판매 값어치의 50% 환급

# ---- 확률석
STONE_PRICE_RATE = 0.08           # 확률석 : 판매가 대비 비율  ← 오르는 정도 조절
STONE_MIN_PRICE = 100             # 확률석 : 최소 가격
STONE_BOOST = 15                  # 확률석 1개당 성공 확률 증가량 (%p)
STONE_MAX_USE = 5                 # 한 번의 업그레이드에 적용할 수 있는 최대 개수

# ---- 업그레이드 연출 시간
CHARGE_NORMAL = 1.0               # 원이 다 차는 시간(초)
FAST_FACTOR = 10                  # 빠른 업그레이드 배율

# ---- 도감 : 미발견 형민(검은 실루엣) 흐림 정도
SILHOUETTE_BLUR = 5               # 흐림 반경(px, 108px 썸네일 기준). 0 = 선명한 실루엣 / 클수록 형태가 뭉개짐
SILHOUETTE_ALPHA = 255            # 실루엣 진하기 (0~255). 낮출수록 옅어짐
SILHOUETTE_COLOR = (22, 22, 26)   # 실루엣 색

# ---- 도감 : 좌우 드래그 회전 (skew / 원근 / 자동 흔들림 없음)
DEX_DRAG_DEGREES_PER_PIXEL = 0.9  # 논리 좌표 1px당 회전각. 0.9면 400px 드래그 = 360도
DEX_INERTIA_DAMPING = 2.4        # 마찰 계수(1/초): 낮을수록 오래 돌고, 높을수록 빨리 멈춤
DEX_INERTIA_MULTIPLIER = 1.0     # 놓을 때 회전 속도 배율. 0이면 관성 끔
DEX_INERTIA_MAX_SPEED = 1440.0   # 관성 최대 속도(도/초). 비정상 입력의 급회전 방지
DEX_INERTIA_STOP_SPEED = 2.0     # 이 속도(도/초)까지 느려지면 완전히 정지
DEX_INERTIA_SAMPLE_TIME = 0.08   # 놓기 직전 속도를 측정하는 시간(초)
DEX_MIRROR_BACK = False          # False = 뒷면도 같은 정방향 이미지 / True = 뒷면 좌우 반전
DEX_EDGE_WIDTH = 2               # 완전히 옆으로 돌았을 때 보이는 카드 두께(px)
DEX_DRAG_MIN_HIT_WIDTH = 24      # 옆면에서도 다시 잡을 수 있는 최소 클릭 폭(px)
DEX_FACE_PAD = 24               # 황금 후광 여백
DEX_SHADOW_SHIFT_X = 18         # 회전에 따른 그림자 좌우 이동량(px)
DEX_SHADOW_OFFSET_Y = 14        # 기본 그림자 아래쪽 거리(px)
DEX_SHADOW_LIFT = 6             # 옆면으로 돌수록 그림자가 더 내려가는 거리(px)
DEX_SHADOW_SPREAD = 0.06        # 옆면으로 돌수록 그림자가 조금 퍼지는 비율
DEX_SHADOW_FADE = 0.35          # 옆면으로 돌수록 그림자가 옅어지는 비율

# ---- 색상 (미술관 톤)
BG = (250, 250, 248)
WHITE = (255, 255, 255)
INK = (28, 28, 32)
MUTED = (128, 130, 140)
LINE = (226, 226, 230)
LINE_D = (200, 202, 208)
GOLD_D = (184, 134, 11)
GOLD_L = (236, 194, 78)
RED = (200, 64, 74)
GREEN = (46, 150, 96)
BLUE = (58, 108, 196)
PURPLE = (126, 82, 196)


def sell_table():
    """평균 배율로 계산한 단계별 판매가 - 상점 가격 기준"""
    mid = sum(SELL_RAND) / 2
    t, sv = [0], 0
    for _ in range(MAX_LEVEL):
        sv = int((sv + 5) ** SELL_POWER * mid)
        t.append(sv)
    return t


SELL_TABLE = sell_table()


# ================================================================== 폰트
def find_font(names, fallback_files=()):
    for n in names:
        p = pygame.font.match_font(n)
        if p:
            return p
    for p in fallback_files:
        if os.path.exists(p):
            return p
    return None


class Fonts:
    def __init__(self):
        sans = find_font(["malgungothic", "applegothic", "nanumgothic", "nanumbarungothic",
                          "notosanscjkkr", "notosanskr", "notosanscjk", "arialunicodems"],
                         ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                          "/System/Library/Fonts/AppleSDGothicNeo.ttc"])
        if not sans and os.path.isdir(FONT_DIR):
            for f in sorted(os.listdir(FONT_DIR)):
                if f.lower().endswith((".ttf", ".otf", ".ttc")):
                    sans = os.path.join(FONT_DIR, f)
                    break
        serif = find_font(["batang", "batangche", "applemyungjo", "nanummyeongjo",
                           "notoserifcjkkr", "notoserifkr", "notoserifcjk"],
                          ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"]) or sans
        self.sans, self.serif = sans, serif
        self.cache = {}

    def get(self, size, bold=False, serif=False):
        key = (size, bold, serif)
        if key not in self.cache:
            f = pygame.font.Font(self.serif if serif else self.sans, size)
            f.set_bold(bold)
            self.cache[key] = f
        return self.cache[key]


# ================================================================== 그리기 도구
def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def fmt(n):
    """금액을 한국식 단위(해·경·조·억·만)로 표시"""
    n = int(n)
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    parts = []
    for unit, name in ((10**20, "해"), (10**16, "경"), (10**12, "조"), (10**8, "억"), (10**4, "만")):
        q, n = divmod(n, unit)
        if q:
            parts.append(f"{q:,}{name}")
    if n:
        parts.append(f"{n:,}")
    return sign + " ".join(parts)


def text(surf, fonts, s, size, color, pos, anchor="center", bold=False, serif=False):
    img = fonts.get(size, bold, serif).render(s, True, color)
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r


def fit_text_width(surf, fonts, s, size, color, pos, max_width, anchor="center",
             bold=False, serif=False, min_size=8):
    """지정한 가로 폭을 넘지 않도록 글자 크기만 줄여서 그린다."""
    size = int(size)
    while size > min_size and fonts.get(size, bold, serif).size(str(s))[0] > max_width:
        size -= 1
    return text(surf, fonts, s, size, color, pos, anchor, bold, serif)


def rrect(surf, color, rect, radius=10, width=0):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def alpha_rect(surf, color, rect, radius=0):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, color, (0, 0, rect[2], rect[3]), border_radius=radius)
    surf.blit(s, (rect[0], rect[1]))


def soft_shadow(w, h, radius=18, pad=44, alpha=70, div=6):
    """부드럽게 번지는 사각형 그림자"""
    s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, alpha), (pad, pad, w, h), border_radius=radius)
    size = s.get_size()
    small = pygame.transform.smoothscale(s, (max(1, size[0] // div), max(1, size[1] // div)))
    return pygame.transform.smoothscale(small, size)


def draw_ring(surf, center, radius, progress, width, color, track=LINE):
    pygame.draw.circle(surf, track, center, radius, 2)
    if progress <= 0:
        return
    pts = []
    steps = max(2, int(120 * progress))
    for i in range(steps + 1):
        a = -math.pi / 2 + math.tau * progress * i / steps
        pts.append((center[0] + math.cos(a) * radius, center[1] + math.sin(a) * radius))
    pygame.draw.lines(surf, color, False, pts, width)
    pygame.draw.circle(surf, color, (int(pts[-1][0]), int(pts[-1][1])), width // 2 + 1)


def draw_switch(surf, rect, on):
    rect = pygame.Rect(rect)
    rrect(surf, INK if on else (214, 214, 220), rect, rect.h // 2)
    kx = rect.right - rect.h // 2 if on else rect.x + rect.h // 2
    pygame.draw.circle(surf, (0, 0, 0, 30), (kx, rect.centery + 1), rect.h // 2 - 2)
    pygame.draw.circle(surf, WHITE, (kx, rect.centery), rect.h // 2 - 3)


def fit_text(font, s, max_w):
    """max_w 안에 들어가도록 뒤를 ... 으로 줄인다"""
    if font.size(s)[0] <= max_w:
        return s
    while s and font.size(s + "...")[0] > max_w:
        s = s[:-1]
    return s + "..."


def draw_star(surf, c, r, color):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rad = r if k % 2 == 0 else r * 0.45
        pts.append((c[0] + math.cos(a) * rad, c[1] + math.sin(a) * rad))
    pygame.draw.polygon(surf, color, pts)


def make_silhouette(flat):
    """흰 배경 + 검은 선 이미지를 '속이 꽉 찬 검정 실루엣'으로 바꾼다 (도감 미발견용).
    선을 살짝 두껍게 만들어 틈을 메우고, 바깥 배경만 flood-fill 해서 나머지를 전부 칠한다."""
    w, h = flat.get_size()
    lines = pygame.mask.from_threshold(flat, (0, 0, 0), (230, 230, 230, 255))
    ls = lines.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
    grown = pygame.Surface((w, h), pygame.SRCALPHA)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if dx * dx + dy * dy <= 5:
                grown.blit(ls, (dx, dy))
    gm = pygame.mask.from_surface(grown, 128)
    inv = gm.copy()
    inv.invert()
    outside = pygame.mask.Mask((w, h))
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if inv.get_at(seed) and not outside.get_at(seed):
            outside.draw(inv.connected_component(seed), (0, 0))
    filled = outside.copy()
    filled.invert()
    return filled.to_surface(setcolor=(*SILHOUETTE_COLOR, 255), unsetcolor=(*SILHOUETTE_COLOR, 0))


def blur_surface(surf, radius):
    """간단한 blur (pygame 버전에 상관없이 동작) : 줄였다가 두 단계로 다시 키운다.
    radius 가 클수록 더 흐려진다. 0 이하이면 원본 그대로."""
    if radius <= 0:
        return surf
    w, h = surf.get_size()
    f = 1.0 + radius * 0.6
    small = pygame.transform.smoothscale(surf, (max(2, int(w / f)), max(2, int(h / f))))
    mid = pygame.transform.smoothscale(small, (max(2, int(w / f * 2)), max(2, int(h / f * 2))))
    return pygame.transform.smoothscale(mid, (w, h))


def make_silhouette_thumb(flat, size=108):
    """도감 목록의 미발견 형민 : 속이 꽉 찬 실루엣을 SILHOUETTE_BLUR 만큼 흐리게 만든다."""
    thumb = pygame.transform.smoothscale(make_silhouette(flat), (size, size))
    pad = int(SILHOUETTE_BLUR * 3) + 2          # 가장자리에서 blur 가 잘리지 않도록 여백
    canvas = pygame.Surface((size + pad * 2, size + pad * 2), pygame.SRCALPHA)
    canvas.fill((*SILHOUETTE_COLOR, 0))
    canvas.blit(thumb, (pad, pad))
    canvas = blur_surface(canvas, SILHOUETTE_BLUR)
    out = canvas.subsurface((pad, pad, size, size)).copy()
    if SILHOUETTE_ALPHA < 255:
        out.fill((255, 255, 255, max(0, SILHOUETTE_ALPHA)), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def scale_card_x(face, image_x_scale):
    """부호 있는 가로 배율만으로 회전 표현. 세로 길이/중심/사각형 모양은 고정.
    pygame은 음수 크기를 지원하지 않으므로 abs로 축소하고, 필요할 때만 좌우 반전한다.
    """
    scale = max(-1.0, min(1.0, float(image_x_scale)))
    width = max(1, int(DEX_EDGE_WIDTH), round(face.get_width() * abs(scale)))
    image = pygame.transform.smoothscale(face, (width, face.get_height()))
    if scale < 0 and DEX_MIRROR_BACK:
        image = pygame.transform.flip(image, True, False)
    return image


# ================================================================== 버튼
class Button:
    def __init__(self, rect, label, kind="secondary"):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.kind = kind          # primary / secondary
        self.enabled = True
        self.press = 0.0

    def draw(self, surf, fonts, mouse, down):
        hover = self.enabled and self.rect.collidepoint(mouse)
        self.press = lerp(self.press, 1.0 if (hover and down) else 0.0, 0.4)
        r = self.rect.copy()
        r.y += int(self.press * 2)
        alpha_rect(surf, (0, 0, 0, 26 if self.enabled else 12), (r.x, self.rect.y + 4, r.w, r.h), 8)
        if not self.enabled:
            fill, border, tc = (240, 240, 242), LINE, (176, 178, 188)
        elif self.kind == "primary":
            fill, border, tc = (INK if not hover else (60, 60, 68)), INK, WHITE
        else:
            fill, border, tc = (WHITE if not hover else (244, 244, 246)), LINE_D, INK
        rrect(surf, fill, r, 8)
        rrect(surf, border, r, 8, 1)
        text(surf, fonts, self.label, 20 if r.h >= 52 else 17, tc, r.center, bold=(self.kind == "primary"))


# ================================================================== 이펙트
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size, gravity=0.0, shape="circle", drag=0.99):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size, self.gravity, self.shape, self.drag = color, size, gravity, shape, drag
        self.rot = random.uniform(0, 360)
        self.spin = random.uniform(-8, 8)

    def update(self, dt):
        self.vy += self.gravity * dt * 60
        self.vx *= self.drag
        self.vy *= self.drag
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.rot += self.spin
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        a = max(0.0, self.life / self.max_life)
        size = max(1, int(self.size * (0.4 + 0.6 * a)))
        if self.shape == "circle":
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, int(255 * a)), (size, size), size)
            surf.blit(s, (self.x - size, self.y - size))
        elif self.shape == "star":
            s = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            c = size * 2
            pts = []
            for i in range(8):
                ang = math.radians(self.rot + i * 45)
                rad = size * (1.6 if i % 2 == 0 else 0.5)
                pts.append((c + math.cos(ang) * rad, c + math.sin(ang) * rad))
            pygame.draw.polygon(s, (*self.color, int(255 * min(1.0, a * 1.5))), pts)
            surf.blit(s, (self.x - c, self.y - c))
        else:
            s = pygame.Surface((size * 2, size), pygame.SRCALPHA)
            s.fill((*self.color, int(255 * a)))
            s = pygame.transform.rotate(s, self.rot)
            surf.blit(s, s.get_rect(center=(self.x, self.y)))


class Shard:
    """파괴 시 흩어지는 형민 조각 (원본 스프라이트를 잘라서 사용)"""

    def __init__(self, img, x, y, vx, vy):
        self.img, self.x, self.y, self.vx, self.vy = img, x, y, vx, vy
        self.rot = 0.0
        self.spin = random.uniform(-9, 9)
        self.life = self.max_life = random.uniform(0.9, 1.4)

    def update(self, dt):
        self.vy += 0.45 * dt * 60
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.rot += self.spin
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        a = max(0.0, self.life / self.max_life)
        s = pygame.transform.rotate(self.img, self.rot)
        s.set_alpha(int(255 * min(1.0, a * 1.6)))
        surf.blit(s, s.get_rect(center=(self.x, self.y)))


class FloatText:
    def __init__(self, s, x, y, color, size=26, life=1.2):
        self.s, self.x, self.y, self.color, self.size = s, x, y, color, size
        self.life = self.max_life = life

    def update(self, dt):
        self.y -= 40 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf, fonts):
        a = max(0.0, min(1.0, self.life / self.max_life * 1.6))
        size = self.size
        while size > 8 and fonts.get(size, True, True).size(self.s)[0] > W - 40:
            size -= 1
        img = fonts.get(size, True, True).render(self.s, True, self.color)
        img.set_alpha(int(255 * a))
        surf.blit(img, img.get_rect(center=(self.x, self.y)))


class Coin:
    """판매 시 자산 표시로 날아가는 동전"""

    def __init__(self, x, y, tx, ty, delay):
        self.sx, self.sy, self.tx, self.ty = x, y, tx, ty
        self.t = -delay
        self.dur = 0.7
        self.arc = random.uniform(-90, 90)

    def update(self, dt):
        self.t += dt
        return self.t < self.dur

    def draw(self, surf):
        if self.t < 0:
            return
        k = ease_out(self.t / self.dur)
        x = lerp(self.sx, self.tx, k) + math.sin(k * math.pi) * self.arc
        y = lerp(self.sy, self.ty, k) - math.sin(k * math.pi) * 60
        pygame.draw.circle(surf, GOLD_D, (x, y), 9)
        pygame.draw.circle(surf, GOLD_L, (x, y), 8)
        pygame.draw.circle(surf, (255, 244, 190), (x - 2, y - 2), 3)


# ================================================================== 게임 상태
class State:
    def __init__(self):
        self.money = START_MONEY
        self.level = 0
        self.per = 100.0
        self.next_cost = 0
        self.sell_value = 0       # 기본 판매 값어치 (황금 배율 적용 전, 공식 계산용)
        self.golden = False
        self.best = 0
        self.protect = 0
        self.insurance = 0
        self.stone = 0            # 보유 확률석
        self.stone_apply = 0      # 다음 업그레이드에 적용할 확률석 개수
        self.auto_protect = True
        self.auto_insurance = True
        self.fast = False
        self.scale_idx = 1
        self.attempts = 0
        self.successes = 0
        self.destroyed = 0
        self.golds = 0
        # 도감 : {"단계": {"n": 획득 횟수, "g": 황금 횟수, "d": 파괴 횟수, "s": 판매 횟수, "dt": 처음 발견한 날}}
        self.dex = {}
        self.dex_new = []         # 아직 상세를 열어보지 않은 새 형민 (NEW 표시)
        self._entry(0)["n"] = 1   # 0단계는 시작할 때부터 발견

    def reset_form(self):
        self.level = 0
        self.per = 100.0
        self.sell_value = 0
        self.next_cost = 0
        self.golden = False
        self.touch(0)

    # ---- 도감
    def _entry(self, level, dt=None):
        key = str(level)
        e = self.dex.get(key)
        if not isinstance(e, dict):
            e = self.dex[key] = {"n": 0, "g": 0, "d": 0, "s": 0,
                                 "dt": time.strftime("%Y-%m-%d") if dt is None else dt}
        for k in ("n", "g", "d", "s"):
            e[k] = int(e.get(k, 0))
        e.setdefault("dt", "")
        return e

    def touch(self, level, gold=False):
        """level 단계(황금 여부 gold)를 얻었을 때 기록. (새 형민인가, 처음 보는 황금인가) 반환"""
        new = str(level) not in self.dex
        e = self._entry(level)
        e["n"] += 1
        gold_new = False
        if gold:
            gold_new = e["g"] == 0
            e["g"] += 1
        if new and level not in self.dex_new:
            self.dex_new.append(level)
        return new, gold_new

    def dex_add(self, level, key):
        self._entry(level)[key] += 1

    def eff_sell(self):
        return self.sell_value * (GOLD_SELL_MULT if self.golden else 1)

    def _ref(self):
        return SELL_TABLE[min(self.best, MAX_LEVEL)]

    def protect_price(self):
        return max(PROTECT_MIN_PRICE, int(self._ref() * PROTECT_PRICE_RATE))

    def insurance_price(self):
        return max(INSURANCE_MIN_PRICE, int(self._ref() * INSURANCE_PRICE_RATE))

    def stone_price(self):
        return max(STONE_MIN_PRICE, int(self._ref() * STONE_PRICE_RATE))

    # ---- 확률석
    def stone_cap(self):
        """지금 적용할 수 있는 최대 개수 (보유량 · 최대 5개 · 확률 100%까지만 의미 있음)"""
        if self.per >= 100:
            return 0
        need = math.ceil((100 - self.per) / STONE_BOOST - 1e-9)
        return max(0, min(STONE_MAX_USE, self.stone, need))

    def clamp_stone(self):
        self.stone_apply = max(0, min(int(self.stone_apply), self.stone_cap()))

    def eff_per(self):
        return min(100.0, self.per + STONE_BOOST * self.stone_apply)

    def save(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.__dict__, f, ensure_ascii=False)
        except OSError:
            pass

    def load(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self.__dict__:
                    setattr(self, k, v)
            self.level = max(0, min(MAX_LEVEL, int(self.level)))
            self.stone = max(0, int(self.stone))
            self.clamp_stone()
            # 도감 정리 + 예전 세이브 이어받기 (최고 단계까지는 발견한 것으로 처리)
            if not isinstance(self.dex, dict):
                self.dex = {}
            for key in list(self.dex):
                if not key.isdigit() or int(key) > MAX_LEVEL:
                    del self.dex[key]
                else:
                    self._entry(int(key))
            for lv in range(0, max(0, min(MAX_LEVEL, int(self.best))) + 1):
                if str(lv) not in self.dex:
                    self._entry(lv, dt="")["n"] = 1
            self._entry(0)
            self.dex_new = [int(x) for x in self.dex_new if str(x) in self.dex] \
                if isinstance(self.dex_new, list) else []
        except (OSError, ValueError, TypeError, AttributeError):
            pass


def display_name(level, golden):
    return ("황금 " if golden else "") + TITLES[level]


# ================================================================== 메인 게임
class Game:
    CARD = pygame.Rect(40, 150, 400, 400)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("형민그레이드")
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()

        self.st = State()
        self.st.load()
        self.disp_money = float(self.st.money)
        self.init_window()      # 창을 먼저 만들어야 이미지 convert 가능
        self.build_art()

        self.mode = "idle"            # idle / charging / result / selling
        self.timer = 0.0
        self.result = None            # success / golden / destroyed / protected
        self.old_level = 0
        self.old_golden = False
        self.ascale = 1.0
        self.charge_time = CHARGE_NORMAL
        self.rtime = 0.9
        self.boost = 0.0              # 이번 업그레이드에 적용된 확률석 보너스(%p)

        self.panel = None             # None / shop / settings
        self.panel_last = "shop"
        self.panel_anim = 0.0
        self.reset_confirm = False

        self.particles, self.shards, self.floats, self.coins = [], [], [], []
        self.flash = None
        self.shake = 0.0
        self.banner = None
        self.toast = None
        self.gold_fx = None
        self.t = 0.0
        self.mouse_down = False

        self.btn_up = Button((40, 672, 400, 56), "업그레이드", "primary")
        self.btn_sell = Button((40, 748, 94, 48), "형민 판매")
        self.btn_shop = Button((142, 748, 94, 48), "상점")
        self.btn_dex = Button((244, 748, 94, 48), "도감")
        self.btn_set = Button((346, 748, 94, 48), "설정")

        # 도감 화면
        self.dex_open = False
        self.dex_anim = 0.0
        self.dex_sel = None           # None = 목록, 숫자 = 그 단계의 상세
        self.dex_scroll = 0.0
        self.dex_scroll_t = 0.0
        self.dex_press = None         # [누른 위치, 그때의 스크롤, 드래그 중인지]
        self.dex_gold_view = False
        self.dex_angle = 0.0          # 회전각(라디안). 드래그 또는 관성으로 변경.
        self.image_x_scale = 1.0      # cos(dex_angle): 1 → 0 → -1 → 0 → 1
        self.dex_drag = None          # (누른 논리 x, 그때의 회전각)
        self.dex_spin_velocity = 0.0  # 관성 각속도(라디안/초), 좌우 방향은 부호로 표현
        self._dex_drag_samples = []   # (입력 시각, 논리 x): 직전 드래그 속도 측정용
        self._dex_drag_direction = 0
        self._dex_spin_key = None
        self._dex_spin_img = None
        self.dex_close_rect = pygame.Rect(W - 54, 15, 30, 30)
        self.dex_back_rect = pygame.Rect(18, 16, 92, 32)
        self.dex_next_rect = pygame.Rect(W - 24 - 36, 16, 36, 32)
        self.dex_prev_rect = pygame.Rect(W - 24 - 36 - 8 - 36, 16, 36, 32)
        self.dex_pill_n = pygame.Rect(W // 2 - 96, 468, 92, 30)
        self.dex_pill_g = pygame.Rect(W // 2 + 4, 468, 92, 30)
        # 로비의 확률석 적용 컨트롤 (카드 왼쪽 위)
        self.stone_pill = pygame.Rect(52, 162, 200, 34)
        self.stone_minus = pygame.Rect(56, 165, 28, 28)
        self.stone_plus = pygame.Rect(220, 165, 28, 28)
        self.build_panel_rects()

    # ---------------- 화면 크기
    def max_scale_idx(self):
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            return len(SCALES) - 1
        ok = [i for i, sc in enumerate(SCALES) if W * sc <= dw * 0.98 and H * sc <= dh * 0.90]
        return max(ok) if ok else 0

    def init_window(self):
        self.st.scale_idx = max(0, min(self.st.scale_idx, self.max_scale_idx(), len(SCALES) - 1))
        self.apply_scale(self.st.scale_idx, save=False)

    def apply_scale(self, idx, save=True):
        self.st.scale_idx = idx
        self.scale = SCALES[idx]
        self.screen = pygame.display.set_mode((int(W * self.scale), int(H * self.scale)))
        if save:
            self.st.save()

    def mpos(self, pos=None):
        x, y = pos if pos is not None else pygame.mouse.get_pos()
        return (x / self.scale, y / self.scale)

    # ---------------- 리소스
    def build_art(self):
        """원본 PNG는 그대로 두고, 화면에 올릴 때 쓰는 파생 이미지만 만든다.
        - sprites      : 흰 배경 위 원본 (BLEND_MULT로 얹으면 원본과 동일하게 보임)
        - sprites_gold : 황금색 버전 (선 색만 금색 그라데이션)
        - shadows/glows: 그림자 / 황금 후광"""
        self.sprites, self.sprites_gold, self.shadows, self.glows = [], [], [], []
        self.thumbs, self.thumbs_black = [], []     # 도감 목록용 작은 이미지 / 검은 실루엣
        grad =pygame.Surface((350, 350))
        for y in range(350):
            pygame.draw.line(grad, mix((244, 204, 80), (168, 112, 6), y / 349), (0, y), (350, y))
        inv = pygame.Surface((350, 350))
        inv.fill((255, 255, 255))
        inv.blit(grad, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        for i in range(len(TITLES)):
            raw = pygame.image.load(os.path.join(IMG_DIR, f"{i}.png")).convert_alpha()
            flat = pygame.Surface(raw.get_size()).convert()
            flat.fill((255, 255, 255))
            flat.blit(raw, (0, 0))
            self.sprites.append(flat)
            self.thumbs.append(pygame.transform.smoothscale(flat, (108, 108)))
            self.thumbs_black.append(make_silhouette_thumb(flat, 108))

            g = flat.copy()
            g.blit(inv, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            out = grad.copy()
            out.blit(g, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.sprites_gold.append(out)

            mask = pygame.mask.from_threshold(flat, (0, 0, 0), (200, 200, 200, 255))
            sh = mask.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
            sh = pygame.transform.smoothscale(pygame.transform.smoothscale(sh, (175, 175)), (350, 350))
            sh.fill((255, 255, 255, 105), special_flags=pygame.BLEND_RGBA_MULT)
            self.shadows.append(sh)
            gl = mask.to_surface(setcolor=(255, 190, 40, 255), unsetcolor=(255, 190, 40, 0))
            gl = pygame.transform.smoothscale(pygame.transform.smoothscale(gl, (58, 58)), (350, 350))
            gl.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.glows.append(gl)

        self.card_shadow = soft_shadow(400, 400, 20, 50, 64, 7)
        self.bg = pygame.Surface((W, H))
        self.bg.fill(BG)

    def draw_sprite(self, surf, idx, golden, x, y, fade=1.0, dy=0):
        fade = max(0.0, min(1.0, fade))
        if fade <= 0:
            return
        base = (self.sprites_gold if golden else self.sprites)[idx]
        if golden:
            gl = self.glows[idx]
            gl.set_alpha(int(255 * fade * (0.65 + 0.35 * math.sin(self.t * 4))))
            surf.blit(gl, (x, y + dy))
            gl.set_alpha(255)
        if fade < 0.999:
            base = base.copy()
            v = int(255 * (1 - fade))
            base.fill((v, v, v), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(base, (x, y + dy), special_flags=pygame.BLEND_RGB_MULT)

    def sprite_shards(self, idx, golden, ox, oy):
        src = (self.sprites_gold if golden else self.sprites)[idx]
        n, size = 7, 50
        shards = []
        for gy in range(n):
            for gx in range(n):
                tile = src.subsurface((gx * size, gy * size, size, size)).copy()
                tile.set_colorkey((255, 255, 255))
                if pygame.mask.from_surface(tile).count() < size * size * 0.7:
                    cx, cy = ox + gx * size + size / 2, oy + gy * size + size / 2
                    ang = math.atan2(cy - (oy + 175), cx - (ox + 175))
                    sp = random.uniform(3, 8)
                    shards.append(Shard(tile, cx, cy, math.cos(ang) * sp + random.uniform(-1, 1),
                                        math.sin(ang) * sp - random.uniform(2, 6)))
        return shards

    @property
    def sprite_origin(self):
        return (self.CARD.x + 25, self.CARD.y + 25)

    # ---------------- 패널 레이아웃
    def build_panel_rects(self):
        self.shop_panel = pygame.Rect(30, 110, 420, 600)
        p = self.shop_panel
        self.shop_close = pygame.Rect(p.right - 46, p.y + 12, 30, 30)
        self.shop_rows = []
        for i in range(3):
            row = pygame.Rect(p.x + 16, p.y + 64 + i * 166, p.w - 32, 154)
            buy = pygame.Rect(row.right - 210, row.bottom - 50, 194, 40)
            tog = pygame.Rect(row.x + 16, row.bottom - 43, 46, 26)
            self.shop_rows.append((row, buy, tog))
        self.set_panel = pygame.Rect(30, 150, 420, 520)
        q = self.set_panel
        self.set_close = pygame.Rect(q.right - 46, q.y + 12, 30, 30)
        self.set_fast_row = pygame.Rect(q.x + 16, q.y + 60, q.w - 32, 100)
        self.set_fast_sw = pygame.Rect(self.set_fast_row.right - 70, self.set_fast_row.y + 20, 52, 28)
        self.set_size_row = pygame.Rect(q.x + 16, q.y + 172, q.w - 32, 120)
        bw = (self.set_size_row.w - 32 - 3 * 8) // 4
        self.size_btns = [pygame.Rect(self.set_size_row.x + 16 + i * (bw + 8), self.set_size_row.bottom - 54, bw, 38)
                          for i in range(len(SCALES))]
        self.set_reset_row = pygame.Rect(q.x + 16, q.y + 304, q.w - 32, 150)
        self.reset_btn = pygame.Rect(self.set_reset_row.right - 150, self.set_reset_row.bottom - 54, 134, 40)
        self.cancel_btn = pygame.Rect(self.reset_btn.x - 130, self.reset_btn.y, 118, 40)
        self.shop_shadow = soft_shadow(420, 600, 22, 50, 70, 7)
        self.set_shadow = soft_shadow(420, 520, 22, 50, 70, 7)

    # ---------------- 게임 액션
    def toast_msg(self, s, color=INK):
        self.toast = (s, color, 1.8)

    def toggle_fast(self):
        self.st.fast = not self.st.fast
        self.st.save()

    def adjust_stone(self, d):
        """로비에서 확률석 적용 개수를 늘리거나 줄인다"""
        s = self.st
        if self.mode != "idle" or self.panel or s.stone <= 0:
            return
        cap = s.stone_cap()
        if d > 0 and cap == 0:
            if s.per >= 100:
                self.toast_msg("성공 확률이 이미 100%입니다", MUTED)
            return
        if d > 0 and s.stone_apply >= cap:
            if s.stone_apply >= STONE_MAX_USE:
                self.toast_msg(f"한 번에 최대 {STONE_MAX_USE}개까지 적용할 수 있습니다", MUTED)
            elif s.stone_apply >= s.stone:
                self.toast_msg("보유한 확률석이 부족합니다", RED)
            else:
                self.toast_msg("이미 확률이 100%에 도달했습니다", MUTED)
            return
        s.stone_apply = max(0, min(cap, s.stone_apply + d))

    def start_upgrade(self):
        s = self.st
        if self.mode != "idle" or self.panel:
            return
        if s.level >= MAX_LEVEL:
            self.toast_msg("최고 단계입니다. 판매해서 값어치를 챙기세요", GOLD_L)
            return
        if s.money < s.next_cost:
            self.toast_msg("자산이 부족합니다", RED)
            self.shake = 6
            return
        s.money -= s.next_cost
        s.attempts += 1
        # 확률석 소모 : 한 번 쓰면 사라진다
        s.clamp_stone()
        used = s.stone_apply
        self.boost = float(used * STONE_BOOST)
        if used:
            s.stone -= used
            s.stone_apply = 0
            self.floats.append(FloatText(f"확률석 ×{used}  확률 +{used * STONE_BOOST}%",
                                         self.CARD.centerx, self.CARD.y + 20, PURPLE, 22, 1.4))
        self.mode = "charging"
        self.timer = 0.0
        self.old_level, self.old_golden = s.level, s.golden
        self.ascale = 0.5 if s.fast else 1.0
        self.charge_time = CHARGE_NORMAL / (FAST_FACTOR if s.fast else 1)
        if s.next_cost:
            self.floats.append(FloatText(f"-{fmt(s.next_cost)}G", self.CARD.centerx, self.CARD.bottom + 8, RED, 20))
        s.save()

    def resolve_upgrade(self):
        s = self.st
        cx, cy = self.CARD.center
        self.rtime = 0.9 * self.ascale
        chance = min(100.0, s.per + self.boost)
        self.boost = 0.0
        if random.uniform(0, 100) <= chance:
            s.per *= PER_DECAY
            s.level += 1
            s.successes += 1
            # 판매가: 현재 단계 기준값에서만 랜덤 적용
            s.sell_value = int(
                SELL_TABLE[s.level] * random.uniform(*SELL_VALUE_RANDOM)
            )
            # 다음 강화 비용: 현재 단계 기준값의 20%
            s.next_cost = max(
                1, int(SELL_TABLE[s.level] * UPGRADE_COST_RATE)
            )
            s.best = max(s.best, s.level)
            s.golden = random.random() < GOLD_CHANCE
            new_dex, new_gold = s.touch(s.level, s.golden)
            if new_dex:
                self.toast_msg(f"도감 등록 : {display_name(s.level, s.golden)}", GOLD_D if s.golden else BLUE)
            elif new_gold:
                self.toast_msg("도감 : 황금 형민을 처음 발견했습니다!", GOLD_D)
            if s.golden:
                s.golds += 1
                self.result = "golden"
                self.golden_burst(cx, cy)
                self.banner = ("황금 형민 출현!", f"판매 값어치 ×{GOLD_SELL_MULT}", GOLD_L, 2.4)
            else:
                self.result = "success"
                self.flash = [(255, 236, 160), 150]
                self.burst_success(cx, cy)
                if s.level == MAX_LEVEL:
                    self.banner = ("대 형 민 강림!!", "최고 단계 달성", GOLD_L, 2.2)
                else:
                    self.banner = ("강화 성공", f"{s.level}Min 달성", WHITE, 1.4)
        else:
            if s.auto_protect and s.protect > 0:
                s.protect -= 1
                self.result = "protected"
                self.flash = [(150, 190, 255), 130]
                self.burst_shield(cx, cy)
                self.banner = ("파괴 방지권 발동", "형민이가 지켜졌습니다", (150, 190, 255), 1.6)
            else:
                refund = 0
                if s.auto_insurance and s.insurance > 0:
                    s.insurance -= 1
                    refund = int(s.eff_sell() * INSURANCE_REFUND)
                    s.money += refund
                s.destroyed += 1
                s.dex_add(s.level, "d")
                self.result = "destroyed"
                ox, oy = self.sprite_origin
                self.shards = self.sprite_shards(self.old_level, self.old_golden, ox, oy)
                self.flash = [(255, 110, 120), 120]
                self.shake = 20
                sub = f"보험 환급 +{fmt(refund)}G" if refund else "0단계로 돌아갑니다"
                self.banner = ("파괴됨", sub, (255, 130, 140), 1.8)
                if refund:
                    self.floats.append(FloatText(f"+{fmt(refund)}G", cx, cy + 70, GOLD_D, 30, 1.6))
                s.reset_form()
        self.mode = "result"
        self.timer = 0.0
        s.save()

    def do_sell(self):
        s = self.st
        if self.mode != "idle" or self.panel:
            return
        if s.sell_value <= 0:
            self.toast_msg("판매할 값어치가 없습니다", RED)
            return
        gain = s.eff_sell()
        s.money += gain
        s.dex_add(s.level, "s")
        self.old_level, self.old_golden = s.level, s.golden
        s.reset_form()
        s.stone_apply = 0
        self.mode = "selling"
        self.timer = 0.0
        self.ascale = 0.5 if s.fast else 1.0
        self.rtime = 0.7 * self.ascale
        cx, cy = self.CARD.center
        self.floats.append(FloatText(f"+{fmt(gain)}G", cx, cy, GOLD_D, 34, 1.4))
        for i in range(min(18, 6 + int(gain) // 40)):
            self.coins.append(Coin(cx + random.uniform(-60, 60), cy + random.uniform(-40, 40), 410, 40, i * 0.04))
        s.save()

    def buy(self, which):
        s = self.st
        price = {"protect": s.protect_price, "insurance": s.insurance_price, "stone": s.stone_price}[which]()
        if s.money < price:
            self.toast_msg("자산이 부족합니다", RED)
            self.shake = 5
            return
        s.money -= price
        if which == "protect":
            s.protect += 1
        elif which == "insurance":
            s.insurance += 1
        else:
            s.stone += 1
        self.floats.append(FloatText(f"-{fmt(price)}G", 240, 130, RED, 20, 1.0))
        s.save()

    def do_reset(self):
        try:
            os.remove(SAVE_PATH)
        except OSError:
            pass
        keep = self.st.scale_idx
        self.st = State()
        self.st.scale_idx = keep
        self.disp_money = 0.0
        self.mode, self.result, self.timer = "idle", None, 0.0
        self.boost = 0.0
        self.particles, self.shards, self.floats, self.coins = [], [], [], []
        self.flash = self.banner = self.gold_fx = None
        self.reset_confirm = False
        self.panel = None
        self.st.save()
        self.toast_msg("데이터를 초기화했습니다", INK)

    def open_panel(self, name):
        if self.mode != "idle":
            return
        self.panel = None if self.panel == name else name
        if self.panel:
            self.panel_last = name
        self.reset_confirm = False

    # ---------------- 도감 : 상태 / 입력
    DEX_COLS, DEX_CELL_W, DEX_CELL_H, DEX_GAP = 3, 136, 160, 12
    DEX_TOP = 108                         # 목록 스크롤 영역 시작 y
    DEX_CARD = pygame.Rect(40, 58, 400, 400)

    def dex_found(self, i):
        return str(i) in self.st.dex

    def dex_cell_rect(self, i):
        r, c = divmod(i, self.DEX_COLS)
        x = 24 + c * (self.DEX_CELL_W + self.DEX_GAP)
        y = self.DEX_TOP + 8 + r * (self.DEX_CELL_H + self.DEX_GAP) - self.dex_scroll
        return pygame.Rect(x, int(y), self.DEX_CELL_W, self.DEX_CELL_H)

    def dex_max_scroll(self):
        rows = math.ceil(len(TITLES) / self.DEX_COLS)
        total = rows * (self.DEX_CELL_H + self.DEX_GAP) + 16
        return max(0.0, total - (H - self.DEX_TOP))

    def dex_scroll_by(self, d):
        self.dex_scroll_t = max(0.0, min(self.dex_max_scroll(), self.dex_scroll_t + d))

    def dex_cancel_pointer(self, stop_spin=True):
        """제스처 해제. 화면 전환/포커스 이탈 때는 관성까지 정리한다."""
        self.dex_press = None
        self.dex_drag = None
        self._dex_drag_samples = []
        self._dex_drag_direction = 0
        if stop_spin:
            self.dex_spin_velocity = 0.0

    @staticmethod
    def dex_input_time(event=None):
        # 가능하면 이벤트 자체의 밀리초 타임스탬프를 사용한다.
        # 없는 pygame 버전에서는 pygame의 같은 밀리초 시계를 사용한다.
        stamp = getattr(event, "timestamp", None)
        return (stamp if stamp is not None else pygame.time.get_ticks()) / 1000.0

    def dex_sample_drag(self, x, now):
        """최근 움직임만 기록. 중간에 멈췄거나 방향을 바꾼 경우 오래된 힘을 버린다."""
        samples = self._dex_drag_samples
        if samples:
            now = max(float(now), samples[-1][0])
            dx = x - samples[-1][1]
            direction = 1 if dx > 0 else -1 if dx < 0 else 0
            if direction:
                if self._dex_drag_direction and direction != self._dex_drag_direction:
                    samples[:] = samples[-1:]
                self._dex_drag_direction = direction
            if now == samples[-1][0]:
                samples[-1] = (now, float(x))
            else:
                samples.append((now, float(x)))
        else:
            samples.append((float(now), float(x)))
        window = max(0.01, float(DEX_INERTIA_SAMPLE_TIME))
        cutoff = now - window
        # 창 경계의 위치를 보간할 수 있도록 경계 이전 샘플 하나는 남긴다.
        while len(samples) > 2 and samples[1][0] <= cutoff:
            samples.pop(0)

    def dex_release_velocity(self):
        samples = self._dex_drag_samples
        if len(samples) < 2:
            return 0.0
        end_t, end_x = samples[-1]
        start_t, start_x = samples[0]
        cutoff = end_t - max(0.01, float(DEX_INERTIA_SAMPLE_TIME))
        if start_t < cutoff:
            next_t, next_x = samples[1]
            if next_t > start_t:
                start_x = lerp(start_x, next_x, (cutoff - start_t) / (next_t - start_t))
                start_t = cutoff
        elapsed = end_t - start_t
        if elapsed <= 0:
            return 0.0
        # 같은 프레임에 몰린 이벤트/짧은 입력으로 속도가 폭증하지 않게 제한한다.
        px_per_sec = (end_x - start_x) / max(1.0 / 240.0, elapsed)
        speed = math.radians(px_per_sec * DEX_DRAG_DEGREES_PER_PIXEL)
        speed *= max(0.0, float(DEX_INERTIA_MULTIPLIER))
        limit = math.radians(max(0.0, float(DEX_INERTIA_MAX_SPEED)))
        speed = max(-limit, min(limit, speed))
        stop = math.radians(max(0.01, float(DEX_INERTIA_STOP_SPEED)))
        return speed if abs(speed) > stop else 0.0

    def dex_update_inertia(self, dt):
        if not self.dex_open or self.dex_sel is None:
            self.dex_spin_velocity = 0.0
            return
        if self.dex_drag is not None or dt <= 0:
            return
        velocity = self.dex_spin_velocity
        stop = math.radians(max(0.01, float(DEX_INERTIA_STOP_SPEED)))
        if abs(velocity) <= stop:
            self.dex_spin_velocity = 0.0
            return
        damping = max(0.01, float(DEX_INERTIA_DAMPING))
        # v(t) = v0 * exp(-마찰*t), 각도도 정확히 적분하여 FPS 영향을 없앤다.
        time_to_stop = math.log(abs(velocity) / stop) / damping
        step = min(float(dt), time_to_stop)
        decay = math.exp(-damping * step)
        self.dex_set_angle(self.dex_angle + velocity * (-math.expm1(-damping * step)) / damping)
        self.dex_spin_velocity = 0.0 if dt >= time_to_stop else velocity * decay

    def dex_set_angle(self, angle):
        # 몇 바퀴든 회전 가능. 값만 0~2π로 유지하고 시각적 회전은 끊기지 않는다.
        self.dex_angle = float(angle) % math.tau
        self.image_x_scale = math.cos(self.dex_angle)

    def dex_page_pos(self, screen_pos):
        """창 배율 + 도감 열기 애니메이션의 위치를 반영한 입력 좌표."""
        x, y = self.mpos(screen_pos)
        page_y = int((1 - ease_out(self.dex_anim)) * 40)
        return x, y - page_y

    def dex_card_hit_rect(self):
        # 회전 후 보이는 카드만 잡되, 얇은 옆면에서도 다시 집을 수 있게 폭을 보정.
        c = self.DEX_CARD
        width = min(c.w, max(int(DEX_DRAG_MIN_HIT_WIDTH),
                            int(DEX_EDGE_WIDTH), round(c.w * abs(self.image_x_scale)), 1))
        hit = pygame.Rect(0, 0, width, c.h)
        hit.center = c.center
        return hit

    def dex_pointer_down(self, pos, now=None):
        self.dex_cancel_pointer(stop_spin=False)
        if not self.dex_open:
            return
        if self.dex_sel is not None and self.dex_card_hit_rect().collidepoint(pos):
            self.dex_spin_velocity = 0.0  # 회전 중인 카드를 다시 잡으면 즉시 멈춘다.
            self.dex_drag = (pos[0], self.dex_angle)
            self.dex_sample_drag(pos[0], self.dex_input_time() if now is None else now)
        else:
            self.dex_press = [pos, self.dex_scroll_t, False]

    def dex_pointer_move(self, pos, now=None):
        if not self.dex_open:
            return
        if self.dex_drag is not None:
            if self.dex_sel is None:
                self.dex_cancel_pointer()
                return
            start_x, start_angle = self.dex_drag
            # 누른 지점부터의 거리로 계산: 프레임 수/이벤트 빈도와 무관하게 1:1 반응.
            dx = pos[0] - start_x
            self.dex_set_angle(start_angle + math.radians(dx * DEX_DRAG_DEGREES_PER_PIXEL))
            self.dex_sample_drag(pos[0], self.dex_input_time() if now is None else now)
            return
        if self.dex_press is None:
            return
        origin, scroll, moved = self.dex_press
        dx, dy = pos[0] - origin[0], pos[1] - origin[1]
        if self.dex_sel is None:
            if abs(dy) > 6:
                self.dex_press[2] = True
            if self.dex_press[2]:
                self.dex_scroll_t = max(0.0, min(self.dex_max_scroll(), scroll - dy))
        elif math.hypot(dx, dy) > 6:
            self.dex_press[2] = True   # 버튼에서 시작한 드래그는 버튼 클릭으로 처리하지 않는다.

    def dex_pointer_up(self, pos, now=None):
        if self.dex_drag is not None:
            # 최종 위치와 멈춰 있던 시간도 반영해서, 놓기 직전의 속도를 이어받는다.
            self.dex_pointer_move(pos, now)
            velocity = self.dex_release_velocity()
            self.dex_cancel_pointer()
            self.dex_spin_velocity = velocity
            return   # 카드 밖의 전환 버튼 위에 놓아도 버튼을 누르지 않는다.
        self.dex_pointer_move(pos, now)
        click = self.dex_open and self.dex_press is not None and not self.dex_press[2]
        self.dex_cancel_pointer(stop_spin=False)
        if click:
            self.dex_click(pos)

    def open_dex(self):
        if self.mode != "idle" or self.panel:
            return
        self.dex_open = True
        self.dex_sel = None
        self.dex_cancel_pointer()

    def close_dex(self):
        self.dex_open = False
        self.dex_sel = None
        self.dex_cancel_pointer()

    def dex_select(self, i):
        self.dex_cancel_pointer()
        self.dex_sel = i
        self.dex_gold_view = False
        self.dex_set_angle(0.0)
        self._dex_spin_key = None
        if i in self.st.dex_new:
            self.st.dex_new.remove(i)
            self.st.save()

    def dex_step(self, d):
        """이전 / 다음으로 발견한 형민으로 이동 (미발견은 건너뜀)"""
        if self.dex_sel is None:
            return
        i = self.dex_sel
        for _ in range(len(TITLES)):
            i = (i + d) % len(TITLES)
            if self.dex_found(i):
                self.dex_select(i)
                return

    def dex_toggle_gold(self, want=None):
        e = self.st.dex.get(str(self.dex_sel))
        if not e or e["g"] <= 0:
            self.toast_msg("황금으로는 아직 발견하지 못했습니다", MUTED)
            return
        self.dex_cancel_pointer(stop_spin=False)
        self.dex_gold_view = (not self.dex_gold_view) if want is None else want
        self._dex_spin_key = None      # 일반/황금 전환 시 회전각은 유지한다.

    def dex_click(self, pos):
        if self.dex_sel is None:
            if self.dex_close_rect.inflate(10, 10).collidepoint(pos):
                self.close_dex()
                return
            if pos[1] < self.DEX_TOP:
                return
            for i in range(len(TITLES)):
                if self.dex_cell_rect(i).collidepoint(pos):
                    if self.dex_found(i):
                        self.dex_select(i)
                    else:
                        self.toast_msg("아직 발견하지 못한 형민입니다", MUTED)
                    return
        else:
            if self.dex_back_rect.collidepoint(pos):
                self.dex_cancel_pointer()
                self.dex_sel = None
            elif self.dex_prev_rect.collidepoint(pos):
                self.dex_step(-1)
            elif self.dex_next_rect.collidepoint(pos):
                self.dex_step(+1)
            elif self.dex_pill_n.collidepoint(pos):
                self.dex_toggle_gold(False)
            elif self.dex_pill_g.collidepoint(pos):
                self.dex_toggle_gold(True)

    def dex_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT):
            self.dex_cancel_pointer()
        elif key in (pygame.K_g, pygame.K_SPACE):
            self.dex_cancel_pointer(stop_spin=False)
        if key == pygame.K_ESCAPE:
            if self.dex_sel is not None:
                self.dex_sel = None
            else:
                self.close_dex()
        elif key == pygame.K_d:
            self.close_dex()
        elif self.dex_sel is not None:
            if key == pygame.K_LEFT:
                self.dex_step(-1)
            elif key == pygame.K_RIGHT:
                self.dex_step(+1)
            elif key in (pygame.K_g, pygame.K_SPACE):
                self.dex_toggle_gold()
        else:
            if key == pygame.K_DOWN:
                self.dex_scroll_by(+90)
            elif key == pygame.K_UP:
                self.dex_scroll_by(-90)
            elif key == pygame.K_PAGEDOWN:
                self.dex_scroll_by(+500)
            elif key == pygame.K_PAGEUP:
                self.dex_scroll_by(-500)

    # ---------------- 도감 : 그리기
    def draw_dex(self, surf):
        if self.dex_anim < 0.02:
            return
        k = self.dex_anim
        page = pygame.Surface((W, H))
        page.fill(BG)
        if self.dex_sel is None:
            self.draw_dex_list(page)
        else:
            self.draw_dex_detail(page)
        page.set_alpha(int(255 * min(1.0, k * 1.2)))
        surf.blit(page, (0, int((1 - ease_out(k)) * 40)))

    def draw_dex_list(self, page):
        f = self.fonts
        s = self.st
        mouse = self.mpos()
        total = len(TITLES)
        found = sum(1 for i in range(total) if self.dex_found(i))
        golds = sum(1 for e in s.dex.values() if e.get("g", 0) > 0)
        text(page, f, "형민 도감", 26, INK, (24, 32), "midleft", True, True)
        self.draw_close(page, self.dex_close_rect, mouse)
        text(page, f, f"발견 {found} / {total}", 13, INK, (24, 66), "midleft", True)
        text(page, f, f"황금으로 발견 {golds}종", 13, GOLD_D, (W - 24, 66), "midright", True)
        bar = pygame.Rect(24, 82, W - 48, 6)
        rrect(page, LINE, bar, 3)
        fill = bar.copy()
        fill.w = max(6, int(bar.w * found / total))
        rrect(page, GOLD_D if found == total else INK, fill, 3)
        pygame.draw.line(page, LINE, (24, self.DEX_TOP - 6), (W - 24, self.DEX_TOP - 6))

        clip = pygame.Rect(0, self.DEX_TOP - 4, W, H - self.DEX_TOP + 4)
        page.set_clip(clip)
        dragging = bool(self.dex_press and self.dex_press[2])
        for i in range(total):
            r = self.dex_cell_rect(i)
            if r.bottom < self.DEX_TOP - 4 or r.top > H:
                continue
            ok = self.dex_found(i)
            e = s.dex.get(str(i))
            gold_i = ok and e["g"] > 0
            hover = ok and not dragging and clip.collidepoint(mouse) and r.collidepoint(mouse)
            rr = r.move(0, -3 if hover else 0)
            alpha_rect(page, (0, 0, 0, 34 if hover else 16), (rr.x, rr.y + 4, rr.w, rr.h), 14)
            rrect(page, WHITE if ok else (242, 242, 245), rr, 14)
            rrect(page, GOLD_L if gold_i else LINE, rr, 14, 2 if gold_i else 1)
            img = self.thumbs[i] if ok else self.thumbs_black[i]
            page.blit(img, img.get_rect(midtop=(rr.centerx, rr.y + 10)))
            text(page, f, f"No.{i + 1:02d}", 11, MUTED, (rr.centerx, rr.y + 130))
            name = TITLES[i] if ok else "? ? ?"
            name = fit_text(f.get(13, True), name, rr.w - 14)
            text(page, f, name, 13, INK if ok else MUTED, (rr.centerx, rr.y + 146), bold=True)
            if gold_i:
                pygame.draw.circle(page, GOLD_L, (rr.right - 18, rr.y + 18), 11)
                draw_star(page, (rr.right - 18, rr.y + 18), 8, WHITE)
            if i in s.dex_new:
                pill = pygame.Rect(rr.x + 8, rr.y + 8, 34, 18)
                rrect(page, RED, pill, 9)
                text(page, f, "NEW", 10, WHITE, pill.center, bold=True)
        page.set_clip(None)

        # 스크롤바
        mx = self.dex_max_scroll()
        if mx > 0:
            view = H - self.DEX_TOP
            th = max(36, int(view * view / (view + mx)))
            ty = self.DEX_TOP + int((view - th - 6) * self.dex_scroll / mx)
            rrect(page, LINE_D, (W - 11, ty, 4, th), 2)

    def build_dex_face(self, i, gold_view):
        """프레임 + 그림을 한 장으로 합쳐 가로 배율만 바꾼다. skew/원근 변형 없음."""
        ga = 60     # 멈춘 카드는 후광까지 안정적으로 유지한다.
        c = self.DEX_CARD
        P = DEX_FACE_PAD
        face = pygame.Surface((c.w + P * 2, c.h + P * 2), pygame.SRCALPHA)
        r = pygame.Rect(P, P, c.w, c.h)
        if gold_view:
            for j in range(4, 0, -1):
                alpha_rect(face, (*GOLD_L, ga // (j + 1)),
                           (r.x - j * 5, r.y - j * 5, r.w + j * 10, r.h + j * 10), 22 + j * 4)
        rrect(face, WHITE, r, 18)
        rrect(face, GOLD_L if gold_view else LINE, r, 18, 2 if gold_view else 1)
        sprite = (self.sprites_gold if gold_view else self.sprites)[i]
        face.blit(sprite, sprite.get_rect(center=r.center), special_flags=pygame.BLEND_RGB_MULT)
        if gold_view:  # 회전각에 따라 이동하는 광택. 시간이 흘러도 저절로 움직이지 않는다.
            if getattr(self, "_dex_mask", None) is None:
                self._dex_mask = pygame.Surface(c.size, pygame.SRCALPHA)
                rrect(self._dex_mask, WHITE, (0, 0, c.w, c.h), 18)
            band = pygame.Surface(c.size, pygame.SRCALPHA)
            bx = int((math.sin(self.dex_angle) + 1) / 2 * (c.w + 160) - 80)
            pygame.draw.polygon(band, (255, 236, 160, 70),
                                [(bx - 30, 0), (bx + 30, 0), (bx - 60, c.h), (bx - 120, c.h)])
            band.blit(self._dex_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            face.blit(band, r.topleft)
        return face

    def dex_card_shadow(self):
        """가로 배율/회전각만으로 크기·위치·농도를 바꾸는 2D 그림자. 셰이더 없음."""
        c = self.DEX_CARD
        side = math.sin(self.dex_angle)
        mag = abs(side)
        spread = 1.0 + max(0.0, DEX_SHADOW_SPREAD) * mag
        base = self.card_shadow
        sx = max(0.025, abs(self.image_x_scale))
        size = (max(2, round(base.get_width() * sx * spread)),
                max(2, round(base.get_height() * spread)))
        shadow = pygame.transform.smoothscale(base, size)
        fade = max(0.0, min(1.0, DEX_SHADOW_FADE))
        shadow.set_alpha(round(255 * (1.0 - fade * mag)))
        dx = -side * DEX_SHADOW_SHIFT_X
        dy = DEX_SHADOW_OFFSET_Y + mag * DEX_SHADOW_LIFT
        rect = shadow.get_rect(center=(round(c.centerx + dx), round(c.centery + dy)))
        return shadow, rect

    def draw_dex_card(self, page, i, gold_view):
        c = self.DEX_CARD
        key = (i, gold_view, self.dex_angle, c.size, DEX_FACE_PAD, DEX_MIRROR_BACK,
               DEX_EDGE_WIDTH, DEX_SHADOW_SHIFT_X, DEX_SHADOW_OFFSET_Y,
               DEX_SHADOW_LIFT, DEX_SHADOW_SPREAD, DEX_SHADOW_FADE)
        if self._dex_spin_key != key:
            face = self.build_dex_face(i, gold_view)
            image = scale_card_x(face, self.image_x_scale)
            shadow, shadow_rect = self.dex_card_shadow()
            self._dex_spin_img = (image, shadow, shadow_rect)
            self._dex_spin_key = key
        image, shadow, shadow_rect = self._dex_spin_img
        page.blit(shadow, shadow_rect)
        edge = max(1, int(DEX_EDGE_WIDTH))
        if round(c.w * abs(self.image_x_scale)) <= edge:
            # 90/270도에서 0px Surface가 되거나 그림이 번쩍이지 않게 옆면만 그린다.
            side_rect = pygame.Rect(0, 0, edge, c.h)
            side_rect.center = c.center
            rrect(page, GOLD_D if gold_view else LINE_D, side_rect, min(edge // 2, 2))
        else:
            page.blit(image, image.get_rect(center=c.center))

    def draw_dex_detail(self, page):
        f = self.fonts
        s = self.st
        i = self.dex_sel
        e = s.dex.get(str(i)) or {"n": 0, "g": 0, "d": 0, "s": 0, "dt": ""}
        has_gold = e["g"] > 0
        gold_view = self.dex_gold_view and has_gold
        mouse = self.mpos()

        # 상단 바
        for r, label, size in ((self.dex_back_rect, "‹ 목록", 15), (self.dex_prev_rect, "‹", 22),
                               (self.dex_next_rect, "›", 22)):
            hv = r.collidepoint(mouse)
            rrect(page, (238, 238, 240) if hv else WHITE, r, 16)
            rrect(page, LINE_D, r, 16, 1)
            text(page, f, label, size, INK, r.center, bold=True)
        text(page, f, f"No.{i + 1:02d} / {len(TITLES)}", 14, MUTED, (243, 32), bold=True)

        # 클릭해서 좌우로 끈 거리만큼 회전. 높이/중심은 고정하고 가로 폭만 변한다.
        self.draw_dex_card(page, i, gold_view)

        # 일반 / 황금 보기 전환
        for r, label, active, ok, col in ((self.dex_pill_n, "일반", not gold_view, True, INK),
                                          (self.dex_pill_g, "황금" if has_gold else "황금 잠김", gold_view, has_gold, GOLD_D)):
            if active:
                rrect(page, col, r, 15)
                text(page, f, label, 14, WHITE, r.center, bold=True)
            else:
                rrect(page, WHITE if ok else (240, 240, 242), r, 15)
                rrect(page, LINE_D if ok else LINE, r, 15, 1)
                text(page, f, label, 14, INK if ok else (176, 178, 188), r.center)

        # 작품명
        name = f"[{display_name(i, gold_view)}]"
        size = 24
        while size > 14 and f.get(size, True, True).size(name)[0] > W - 48:
            size -= 1
        text(page, f, name, size, GOLD_D if gold_view else INK, (W // 2, 524), bold=True, serif=True)
        sub = f"{i}Min" + (" · 최고 단계" if i == MAX_LEVEL else "") + (" · 지금 키우는 중" if s.level == i else "")
        text(page, f, sub, 13, MUTED, (W // 2, 548))

        # 데이터
        sell = SELL_TABLE[i]
        rows = [
            ("단계", f"{i}Min", INK),
            ("다음 강화 성공 확률", "-" if i >= MAX_LEVEL else f"{100 * PER_DECAY ** i:.1f}%", INK),
            ("평균 판매 값어치", f"{fmt(sell)}G", INK),
        ]
        if has_gold:
            rows.append(("황금 판매 값어치", f"{fmt(sell * GOLD_SELL_MULT)}G", GOLD_D))
        rows += [
            ("획득 횟수", f"{e['n']}회", INK),
            ("황금으로 발견", f"발견함 · {e['g']}회" if has_gold else "아직 발견하지 못함", GOLD_D if has_gold else MUTED),
            ("파괴된 횟수", f"{e['d']}회", INK),
            ("판매한 횟수", f"{e['s']}회", INK),
            ("처음 발견한 날", e.get("dt") or "-", INK),
        ]
        y = 564
        for label, val, col in rows:
            text(page, f, label, 13, MUTED, (36, y + 12), "midleft")
            text(page, f, val, 14, col, (W - 36, y + 12), "midright", True)
            pygame.draw.line(page, LINE, (28, y + 25), (W - 28, y + 25))
            y += 26
        text(page, f, "드래그 후 놓으면 관성 회전 · 다시 잡으면 정지 · ← / →", 11, (170, 172, 182), (W // 2, 810))

    # ---------------- 이펙트 생성
    def burst_success(self, cx, cy):
        cols = [GOLD_L, (255, 255, 255), GREEN, (255, 150, 90), BLUE, INK]
        for _ in range(60):
            a = random.uniform(0, math.tau)
            sp = random.uniform(3, 10)
            self.particles.append(Particle(cx, cy, math.cos(a) * sp, math.sin(a) * sp - 2,
                                           random.uniform(0.7, 1.3), random.choice(cols),
                                           random.uniform(4, 7), 0.22,
                                           random.choice(["star", "confetti", "circle"])))

    def burst_shield(self, cx, cy):
        for _ in range(36):
            a = random.uniform(0, math.tau)
            sp = random.uniform(2, 7)
            self.particles.append(Particle(cx, cy, math.cos(a) * sp, math.sin(a) * sp,
                                           random.uniform(0.5, 1.0), random.choice([BLUE, (150, 190, 255)]),
                                           random.uniform(4, 7), 0.0, "circle"))

    def golden_burst(self, cx, cy):
        self.gold_fx = 0.0
        self.flash = [(255, 214, 80), 230]
        self.shake = 12
        cols = [GOLD_L, (255, 232, 130), (255, 250, 210), GOLD_D, (255, 190, 40)]
        for _ in range(170):
            a = random.uniform(0, math.tau)
            sp = random.uniform(3, 15)
            self.particles.append(Particle(cx, cy, math.cos(a) * sp, math.sin(a) * sp - 3,
                                           random.uniform(1.0, 2.0), random.choice(cols),
                                           random.uniform(4, 9), 0.18,
                                           random.choice(["star", "star", "confetti", "circle"])))
        for _ in range(40):  # 위에서 쏟아지는 금빛
            self.particles.append(Particle(random.uniform(40, 440), random.uniform(-80, 120),
                                           random.uniform(-1, 1), random.uniform(3, 7), random.uniform(1.2, 2.2),
                                           random.choice(cols), random.uniform(3, 6), 0.1, "confetti"))

    # ---------------- 업데이트
    def update(self, dt):
        self.t += dt
        s = self.st
        self.disp_money = lerp(self.disp_money, s.money, min(1.0, dt * 8))
        if abs(self.disp_money - s.money) < 1:
            self.disp_money = s.money
        self.panel_anim = lerp(self.panel_anim, 1.0 if self.panel else 0.0, min(1.0, dt * 14))
        s.clamp_stone()

        # 도감 : 드래그 중에는 직접 조작, 놓은 뒤에는 감쇠하는 관성 회전.
        self.dex_update_inertia(dt)
        self.dex_anim = lerp(self.dex_anim, 1.0 if self.dex_open else 0.0, min(1.0, dt * 14))
        if not self.dex_open and self.dex_anim < 0.02:
            self.dex_anim = 0.0
        self.dex_scroll_t = max(0.0, min(self.dex_max_scroll(), self.dex_scroll_t))
        self.dex_scroll = lerp(self.dex_scroll, self.dex_scroll_t, min(1.0, dt * 16))
        if abs(self.dex_scroll - self.dex_scroll_t) < 0.3:
            self.dex_scroll = self.dex_scroll_t

        if self.mode == "charging":
            self.timer += dt
            k = self.timer / self.charge_time
            if random.random() < (0.6 if not s.fast else 0.9):
                a = random.uniform(0, math.tau)
                d = random.uniform(160, 215)
                cx, cy = self.CARD.center
                self.particles.append(Particle(cx + math.cos(a) * d, cy + math.sin(a) * d,
                                               -math.cos(a) * (2 + 4 * k), -math.sin(a) * (2 + 4 * k),
                                               0.45, random.choice([GOLD_L, GOLD_D, MUTED]),
                                               random.uniform(2, 4), 0.0, "circle", 1.0))
            if self.timer >= self.charge_time:
                self.resolve_upgrade()
        elif self.mode in ("result", "selling"):
            self.timer += dt
            if self.timer >= self.rtime:
                self.mode = "idle"
                self.result = None
        elif s.golden and random.random() < 0.3:  # 황금 형민 주변 반짝임
            c = self.CARD
            self.particles.append(Particle(random.uniform(c.x + 20, c.right - 20), random.uniform(c.y + 20, c.bottom - 20),
                                           random.uniform(-0.3, 0.3), random.uniform(-0.8, -0.2), 0.9,
                                           random.choice([GOLD_L, (255, 232, 130)]), random.uniform(2, 4), 0.0, "star"))

        if self.gold_fx is not None:
            self.gold_fx += dt
            if self.gold_fx > 2.4:
                self.gold_fx = None
        self.particles = [p for p in self.particles if p.update(dt)]
        self.shards = [p for p in self.shards if p.update(dt)]
        self.floats = [p for p in self.floats if p.update(dt)]
        self.coins = [c for c in self.coins if c.update(dt)]
        if self.flash:
            self.flash[1] -= 420 * dt
            if self.flash[1] <= 0:
                self.flash = None
        self.shake = max(0.0, self.shake - 45 * dt)
        if self.banner:
            t, sub, c, life = self.banner
            life -= dt
            self.banner = (t, sub, c, life) if life > 0 else None
        if self.toast:
            t, c, life = self.toast
            life -= dt
            self.toast = (t, c, life) if life > 0 else None

    # ---------------- 그리기
    def draw_header(self, surf):
        s = self.st
        f = self.fonts
        text(surf, f, "형민그레이드", 28, INK, (24, 30), "midleft", True, True)
        text(surf, f, "HYEONGMIN GRADE", 10, MUTED, (25, 51), "midleft")
        text(surf, f, "자산", 11, MUTED, (W - 24, 20), "midright")
        fit_text_width(surf, f, fmt(self.disp_money) + " G", 22, INK, (W - 24, 42),
                 220, "midright", True, True, 10)
        pygame.draw.line(surf, LINE, (24, 64), (W - 24, 64))

        lv = text(surf, f, str(s.level), 34, INK, (24, 90), "midleft", True, True)
        text(surf, f, "Min", 14, MUTED, (lv.right + 6, 98), "midleft")
        x = W - 24
        for name, n, col, on in reversed([("확률석", s.stone, PURPLE, True),
                                          ("방지권", s.protect, BLUE, s.auto_protect),
                                          ("보험", s.insurance, GOLD_D, s.auto_insurance)]):
            c = pygame.Rect(0, 76, 84, 28)
            c.right = x
            rrect(surf, WHITE, c, 14)
            rrect(surf, col if (on and n) else LINE_D, c, 14, 1)
            text(surf, f, f"{name} ×{n}", 13, INK if n else MUTED, c.center)
            x = c.left - 6

        eff = s.eff_per()
        boosted = s.stone_apply > 0
        r = text(surf, f, "성공 확률", 12, MUTED, (24, 122), "midleft")
        if boosted:
            text(surf, f, f"확률석 +{s.stone_apply * STONE_BOOST}%", 12, PURPLE, (r.right + 8, 122), "midleft", True)
        text(surf, f, f"{eff:.1f}%", 13, PURPLE if boosted else INK, (W - 24, 122), "midright", True)
        bar = pygame.Rect(24, 134, W - 48, 4)
        rrect(surf, LINE, bar, 2)
        fill = bar.copy()
        fill.w = max(4, int(bar.w * eff / 100))
        rrect(surf, PURPLE if boosted else mix(RED, INK, (s.per - 55) / 40), fill, 2)

    def draw_stone_ctrl(self, surf):
        s = self.st
        f = self.fonts
        cap = s.stone_cap()
        n = s.stone_apply
        alpha_rect(surf, (255, 255, 255, 236), self.stone_pill, 17)
        rrect(surf, PURPLE if n else LINE_D, self.stone_pill, 17, 1)
        for r, sym, ok in ((self.stone_minus, "-", n > 0), (self.stone_plus, "+", n < cap)):
            col = PURPLE if ok else LINE_D
            pygame.draw.circle(surf, col, r.center, 14, 2)
            text(surf, f, sym, 18, col, r.center, bold=True)
        label = f"확률석 {n}개 · +{n * STONE_BOOST}%" if n else f"확률석 적용 (보유 {s.stone})"
        text(surf, f, label, 13, PURPLE if n else MUTED, self.stone_pill.center, bold=bool(n))

    def draw_card(self, surf):
        s = self.st
        card = self.CARD
        f = self.fonts
        gold_now = s.golden if self.mode != "charging" else self.old_golden
        # 카드 그림자 (강화 중엔 살짝 진해짐)
        sh = self.card_shadow
        surf.blit(sh, (card.x - 50, card.y - 50 + 14))

        # 상태 후광
        glow, ga = None, 0
        if self.mode == "charging":
            k = self.timer / self.charge_time
            glow, ga = GOLD_L, int(40 + 90 * k)
        elif self.mode == "result":
            glow = {"success": GREEN, "golden": GOLD_L, "destroyed": RED, "protected": BLUE}[self.result]
            ga = int(110 * (1 - self.timer / self.rtime))
        elif s.golden:
            glow, ga = GOLD_L, int(70 + 40 * math.sin(self.t * 4))
        elif s.level == MAX_LEVEL:
            glow, ga = GOLD_L, int(60 + 30 * math.sin(self.t * 3))
        if glow:
            for i in range(5, 0, -1):
                alpha_rect(surf, (*glow, ga // (i + 1)),
                           (card.x - i * 5, card.y - i * 5, card.w + i * 10, card.h + i * 10), 22 + i * 4)
        rrect(surf, WHITE, card, 18)
        rrect(surf, GOLD_L if s.golden else LINE, card, 18, 2 if s.golden else 1)

        ox, oy = self.sprite_origin
        sc = self.ascale
        if self.mode == "charging":
            k = self.timer / self.charge_time
            amp = 1 + 8 * k * k
            self.draw_sprite(surf, self.old_level, self.old_golden,
                             ox + random.uniform(-amp, amp), oy + random.uniform(-amp, amp))
        elif self.mode == "result" and self.result in ("success", "golden"):
            k = min(1.0, self.timer / (0.4 * sc))
            self.draw_sprite(surf, s.level, s.golden, ox, oy, fade=k, dy=(1 - ease_out(k)) * -16)
            self.draw_sprite(surf, self.old_level, self.old_golden, ox, oy, fade=1 - k)
        elif self.mode == "result" and self.result == "destroyed":
            self.draw_sprite(surf, 0, False, ox, oy, fade=(self.timer - 0.5 * sc) / (0.4 * sc))
        elif self.mode == "result" and self.result == "protected":
            jx = math.sin(self.timer * 50) * 6 * (1 - self.timer / self.rtime)
            self.draw_sprite(surf, s.level, s.golden, ox + jx, oy)
        elif self.mode == "selling":
            k = min(1.0, self.timer / (0.5 * sc))
            self.draw_sprite(surf, self.old_level, self.old_golden, ox, oy, fade=1 - k, dy=-ease_out(k) * 36)
            self.draw_sprite(surf, 0, False, ox, oy, fade=k)
        else:
            self.draw_sprite(surf, s.level, s.golden, ox, oy)

        if self.mode == "result" and self.result == "protected":
            k = self.timer / self.rtime
            r = int(120 + 90 * ease_out(k * 2))
            ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*BLUE, int(200 * (1 - k))), (r + 4, r + 4), r, 5)
            surf.blit(ring, ring.get_rect(center=card.center))

        # 충전 링
        if self.mode == "charging":
            draw_ring(surf, card.center, 186, self.timer / self.charge_time, 5, GOLD_D if self.old_golden else INK)

        # 확률석 적용 컨트롤 (로비 상태 + 확률석 보유 시)
        if self.mode == "idle" and s.stone > 0:
            self.draw_stone_ctrl(surf)

        # 작품명 (명판 느낌)
        name = display_name(s.level, s.golden)
        col = GOLD_D if s.golden else INK
        text(surf, f, f"작품명 : [{name}]", 24, col, (W // 2, card.bottom + 32), bold=True, serif=True)

    def draw_stats(self, surf):
        s = self.st
        f = self.fonts
        pygame.draw.line(surf, LINE, (W // 2, 612), (W // 2, 656))
        text(surf, f, "판매 값어치", 12, MUTED, (140, 614))
        val = f"{fmt(s.eff_sell())}G"
        r = fit_text_width(surf, f, val, 24, GOLD_D if s.golden else INK, (140, 640),
                     125, bold=True, serif=True, min_size=14)
        if s.golden:
            text(surf, f, f"×{GOLD_SELL_MULT}", 12, GOLD_D, (r.right + 6, 646), "midleft", True)
        text(surf, f, "업그레이드 비용", 12, MUTED, (340, 614))
        fit_text_width(surf, f, f"{fmt(s.next_cost)}G", 24, RED if s.money < s.next_cost else INK,
                 (340, 640), 125, bold=True, serif=True, min_size=14)

    def draw_gold_fx(self, surf):
        t = self.gold_fx
        if t is None:
            return
        fx = pygame.Surface((W, H), pygame.SRCALPHA)
        cx, cy = self.CARD.center
        fade = max(0.0, 1 - t / 2.4)
        for i in range(20):
            a = t * 0.7 + i * math.tau / 20
            w = 0.05 + 0.03 * math.sin(t * 6 + i)
            p1 = (cx + math.cos(a - w) * 700, cy + math.sin(a - w) * 700)
            p2 = (cx + math.cos(a + w) * 700, cy + math.sin(a + w) * 700)
            pygame.draw.polygon(fx, (255, 214, 90, int(120 * fade)), [(cx, cy), p1, p2])
        for j in range(3):
            rt = t - j * 0.2
            if rt > 0:
                pygame.draw.circle(fx, (236, 180, 40, int(220 * max(0, 1 - rt / 1.6))), (cx, cy), int(rt * 360), 6)
        surf.blit(fx, (0, 0))

    def draw_panel_content_shop(self, surf, p, dy, mouse):
        f = self.fonts
        text(surf, f, "형민 상점", 26, INK, (p.x + 24, p.y + 30), "midleft", True, True)
        fit_text_width(surf, f, f"보유 {fmt(self.st.money)}G", 14, MUTED,
                 (p.right - 60, p.y + 30), 190, "midright", min_size=8)
        self.draw_close(surf, self.shop_close.move(0, dy), mouse)
        s = self.st
        items = [
            ("protect", "파괴 방지권", "강화 실패 시 형민이가 파괴되지 않고\n현재 단계가 유지됩니다.",
             s.protect_price(), s.protect, "auto_protect", BLUE, "1"),
            ("insurance", "파괴 보험권", f"파괴될 때 판매 값어치의 {int(INSURANCE_REFUND * 100)}%를\n돌려받습니다. (파괴 시 1장 소모)",
             s.insurance_price(), s.insurance, "auto_insurance", GOLD_D, "2"),
            ("stone", "확률석", f"업그레이드 성공 확률 +{STONE_BOOST}%\n한 번에 최대 {STONE_MAX_USE}개 · 사용하면 사라집니다.",
             s.stone_price(), s.stone, None, PURPLE, "3"),
        ]
        for i, (key, name, desc, price, owned, attr, col, hk) in enumerate(items):
            row, buy, tog = [r.move(0, dy) for r in self.shop_rows[i]]
            rrect(surf, BG, row, 14)
            rrect(surf, LINE, row, 14, 1)
            ic = pygame.Rect(row.x + 16, row.y + 16, 54, 54)
            pygame.draw.circle(surf, WHITE, ic.center, 27)
            pygame.draw.circle(surf, col, ic.center, 27, 2)
            self.draw_item_icon(surf, key, ic.center, col)
            text(surf, f, name, 20, INK, (ic.right + 14, row.y + 28), "midleft", True, True)
            text(surf, f, f"보유 ×{owned}", 13, col, (row.right - 16, row.y + 28), "midright", True)
            for j, line in enumerate(desc.split("\n")):
                text(surf, f, line, 12, MUTED, (ic.right + 14, row.y + 54 + j * 18), "midleft")
            if attr:
                on = getattr(s, attr)
                draw_switch(surf, tog, on)
                text(surf, f, "자동 사용", 12, INK if on else MUTED, (tog.right + 10, tog.centery), "midleft")
            else:
                text(surf, f, "로비에서 개수를 골라 적용", 12, MUTED, (tog.x + 2, tog.centery), "midleft")
            afford = s.money >= price
            hover = buy.collidepoint(mouse) and afford
            rrect(surf, (60, 60, 68) if hover else INK if afford else (226, 226, 230), buy, 10)
            fit_text_width(surf, f, f"{fmt(price)}G 구매", 16, WHITE if afford else (170, 172, 182),
                     buy.center, buy.w - 12, bold=True, min_size=10)
            text(surf, f, f"[{hk}]", 11, MUTED, (row.right - 16, row.y + 84), "midright")
        text(surf, f, "가격은 최고 도달 단계에 따라 오릅니다", 12, MUTED, (p.centerx, p.bottom - 20))

    def draw_panel_content_settings(self, surf, p, dy, mouse):
        f = self.fonts
        s = self.st
        text(surf, f, "설정", 26, INK, (p.x + 24, p.y + 30), "midleft", True, True)
        self.draw_close(surf, self.set_close.move(0, dy), mouse)
        row = self.set_fast_row.move(0, dy)
        rrect(surf, BG, row, 14)
        rrect(surf, LINE, row, 14, 1)
        text(surf, f, "빠른 업그레이드", 19, INK, (row.x + 18, row.y + 34), "midleft", True, True)
        text(surf, f, f"원이 차오르는 시간이 {FAST_FACTOR}배 빨라지고", 12, MUTED, (row.x + 18, row.y + 64), "midleft")
        text(surf, f, "결과 연출도 짧아집니다.", 12, MUTED, (row.x + 18, row.y + 83), "midleft")
        draw_switch(surf, self.set_fast_sw.move(0, dy), s.fast)

        row = self.set_size_row.move(0, dy)
        rrect(surf, BG, row, 14)
        rrect(surf, LINE, row, 14, 1)
        text(surf, f, "화면 크기", 19, INK, (row.x + 18, row.y + 30), "midleft", True, True)
        text(surf, f, "창 크기를 고릅니다. 모니터보다 큰 크기는 선택할 수 없어요.", 12, MUTED, (row.x + 18, row.y + 56), "midleft")
        mx = self.max_scale_idx()
        for i, br in enumerate(self.size_btns):
            br = br.move(0, dy)
            sel, ok = i == s.scale_idx, i <= mx
            if sel:
                rrect(surf, INK, br, 10)
            else:
                rrect(surf, WHITE if ok else (240, 240, 242), br, 10)
                rrect(surf, LINE_D if ok else LINE, br, 10, 1)
            text(surf, f, f"{int(SCALES[i] * 100)}%", 16, WHITE if sel else INK if ok else (176, 178, 188), br.center, bold=sel)

        row = self.set_reset_row.move(0, dy)
        rrect(surf, BG, row, 14)
        rrect(surf, LINE, row, 14, 1)
        text(surf, f, "데이터 초기화", 19, INK, (row.x + 18, row.y + 30), "midleft", True, True)
        text(surf, f, "저장된 JSON(자산·아이템·진행도)을 삭제하고", 12, MUTED, (row.x + 18, row.y + 58), "midleft")
        text(surf, f, "처음부터 다시 시작합니다. 되돌릴 수 없습니다.", 12, MUTED, (row.x + 18, row.y + 77), "midleft")
        rb = self.reset_btn.move(0, dy)
        if self.reset_confirm:
            cb = self.cancel_btn.move(0, dy)
            rrect(surf, WHITE, cb, 10)
            rrect(surf, LINE_D, cb, 10, 1)
            text(surf, f, "취소", 16, INK, cb.center)
            rrect(surf, RED, rb, 10)
            text(surf, f, "정말 초기화", 16, WHITE, rb.center, bold=True)
        else:
            hv = rb.collidepoint(mouse)
            rrect(surf, (253, 240, 241) if hv else WHITE, rb, 10)
            rrect(surf, RED, rb, 10, 1)
            text(surf, f, "초기화", 16, RED, rb.center, bold=True)
        text(surf, f, f"version : {VERSION}", 15, (190, 192, 200), (p.centerx, p.bottom - 38))

    def draw_close(self, surf, cl, mouse):
        hv = cl.collidepoint(mouse)
        pygame.draw.circle(surf, (238, 238, 240) if hv else BG, cl.center, 15)
        cx, cy = cl.center
        pygame.draw.line(surf, INK, (cx - 5, cy - 5), (cx + 5, cy + 5), 2)
        pygame.draw.line(surf, INK, (cx - 5, cy + 5), (cx + 5, cy - 5), 2)

    def draw_item_icon(self, surf, key, c, col):
        x, y = c
        if key == "protect":
            pts = [(x, y - 17), (x + 14, y - 10), (x + 12, y + 7), (x, y + 18), (x - 12, y + 7), (x - 14, y - 10)]
            pygame.draw.polygon(surf, col, pts, 2)
            pygame.draw.lines(surf, col, False, [(x - 6, y), (x - 1, y + 6), (x + 7, y - 5)], 3)
        elif key == "stone":
            pts = [(x, y - 17), (x + 14, y - 3), (x + 8, y + 15), (x - 8, y + 15), (x - 14, y - 3)]
            pygame.draw.polygon(surf, col, pts, 2)
            pygame.draw.lines(surf, col, False, [(x - 14, y - 3), (x + 14, y - 3)], 2)
            pygame.draw.lines(surf, col, False, [(x - 5, y - 3), (x, y + 15), (x + 5, y - 3)], 1)
        else:
            pygame.draw.circle(surf, col, (x, y), 15, 2)
            text(surf, self.fonts, "%", 16, col, (x, y), bold=True)

    def draw_panel(self, surf):
        if self.panel_anim < 0.02:
            return
        k = self.panel_anim
        alpha_rect(surf, (255, 255, 255, int(205 * k)), (0, 0, W, H))
        name = self.panel_last
        base = self.shop_panel if name == "shop" else self.set_panel
        p = base.copy()
        p.y += int((1 - ease_out(k)) * 50)
        dy = p.y - base.y
        shadow = self.shop_shadow if name == "shop" else self.set_shadow
        shadow.set_alpha(int(255 * k))
        surf.blit(shadow, (p.x - 50, p.y - 50 + 14))
        panel = pygame.Surface((p.w, p.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 255, 255, int(255 * k)), panel.get_rect(), border_radius=20)
        surf.blit(panel, p)
        rrect(surf, LINE, p, 20, 1)
        mouse = self.mpos()
        if name == "shop":
            self.draw_panel_content_shop(surf, p, dy, mouse)
        else:
            self.draw_panel_content_settings(surf, p, dy, mouse)

    def draw_overlay(self, surf):
        if self.banner:
            t, sub, col, life = self.banner
            a = min(1.0, life * 3)
            y = 350
            band = pygame.Surface((W, 96), pygame.SRCALPHA)
            band.fill((22, 22, 28, int(225 * a)))
            surf.blit(band, (0, y - 48))
            img = self.fonts.get(38, True, True).render(t, True, col)
            img.set_alpha(int(255 * a))
            surf.blit(img, img.get_rect(center=(W // 2, y - 8)))
            sb = self.fonts.get(16).render(sub, True, (235, 235, 240))
            sb.set_alpha(int(255 * a))
            surf.blit(sb, sb.get_rect(center=(W // 2, y + 28)))
        if self.toast:
            t, col, life = self.toast
            a = min(1.0, life * 2.5)
            img = self.fonts.get(15, True).render(t, True, WHITE)
            r = img.get_rect(center=(W // 2, 170)).inflate(34, 16)
            alpha_rect(surf, (*mix(INK, col, 0.0), int(235 * a)), r, 16)
            if col != INK:
                alpha_rect(surf, (*col, int(60 * a)), r, 16)
            img.set_alpha(int(255 * a))
            surf.blit(img, img.get_rect(center=r.center))

    def draw(self):
        world = pygame.Surface((W, H))
        world.blit(self.bg, (0, 0))
        self.draw_header(world)
        self.draw_card(world)
        self.draw_gold_fx(world)
        for sh in self.shards:
            sh.draw(world)
        for p in self.particles:
            p.draw(world)
        self.draw_stats(world)

        s = self.st
        mouse = self.mpos()
        locked = self.panel is not None or self.dex_open
        busy = self.mode != "idle" or locked
        self.btn_up.enabled = not busy and s.level < MAX_LEVEL and s.money >= s.next_cost
        self.btn_up.label = "최고 단계" if s.level >= MAX_LEVEL else "업그레이드"
        self.btn_sell.enabled = not busy and s.sell_value > 0
        self.btn_shop.enabled = self.mode == "idle"
        self.btn_dex.enabled = self.mode == "idle"
        self.btn_set.enabled = self.mode == "idle"
        m = (-1, -1) if locked else mouse
        for b in (self.btn_up, self.btn_sell, self.btn_shop, self.btn_dex, self.btn_set):
            b.draw(world, self.fonts, m, self.mouse_down and not locked)
        if s.dex_new:   # 도감 버튼 NEW 표시
            pygame.draw.circle(world, RED, (self.btn_dex.rect.right - 6, self.btn_dex.rect.y + 6), 7)
            text(world, self.fonts, "N", 9, WHITE, (self.btn_dex.rect.right - 6, self.btn_dex.rect.y + 6), bold=True)
        text(world, self.fonts, f"시도 {s.attempts} · 성공 {s.successes} · 파괴 {s.destroyed} · 황금 {s.golds}   |   최고 {s.best}Min",
             11, MUTED, (W // 2, 810))

        for c in self.coins:
            c.draw(world)
        for f in self.floats:
            f.draw(world, self.fonts)
        self.draw_panel(world)
        self.draw_dex(world)
        self.draw_overlay(world)
        if self.flash:
            col, a = self.flash
            alpha_rect(world, (*col, int(max(0, a))), (0, 0, W, H))

        off = (0, 0)
        if self.shake > 0:
            off = (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake) * 0.6)
        frame = pygame.Surface((W, H))
        frame.fill(BG)
        frame.blit(world, off)
        if self.scale == 1.0:
            self.screen.blit(frame, (0, 0))
        else:
            pygame.transform.smoothscale(frame, self.screen.get_size(), self.screen)
        pygame.display.flip()

    # ---------------- 입력
    def on_click(self, pos):
        if self.dex_open:
            return      # 도감은 마우스를 뗄 때 클릭으로 처리 (스크롤 드래그와 구분)
        if self.panel == "shop":
            if self.shop_close.collidepoint(pos) or not self.shop_panel.collidepoint(pos):
                self.panel = None
                return
            for i, (row, buy, tog) in enumerate(self.shop_rows):
                if buy.collidepoint(pos):
                    self.buy(("protect", "insurance", "stone")[i])
                elif i < 2 and tog.inflate(120, 10).collidepoint(pos):
                    attr = "auto_protect" if i == 0 else "auto_insurance"
                    setattr(self.st, attr, not getattr(self.st, attr))
                    self.st.save()
            return
        if self.panel == "settings":
            if self.set_close.collidepoint(pos) or not self.set_panel.collidepoint(pos):
                self.panel = None
                self.reset_confirm = False
                return
            if self.set_fast_sw.inflate(20, 20).collidepoint(pos):
                self.toggle_fast()
            for i, br in enumerate(self.size_btns):
                if br.collidepoint(pos) and i <= self.max_scale_idx():
                    self.apply_scale(i)
            if self.set_fast_sw.inflate(20, 20).collidepoint(pos) or any(b.collidepoint(pos) for b in self.size_btns):
                pass
            elif self.reset_confirm:
                if self.reset_btn.collidepoint(pos):
                    self.do_reset()
                elif self.cancel_btn.collidepoint(pos):
                    self.reset_confirm = False
            elif self.reset_btn.collidepoint(pos):
                self.reset_confirm = True
            return
        if self.mode == "idle" and self.st.stone > 0:
            if self.stone_minus.collidepoint(pos):
                self.adjust_stone(-1)
                return
            if self.stone_plus.collidepoint(pos):
                self.adjust_stone(+1)
                return
        if self.btn_up.rect.collidepoint(pos):
            self.start_upgrade()
        elif self.btn_sell.rect.collidepoint(pos):
            self.do_sell()
        elif self.btn_shop.rect.collidepoint(pos):
            self.open_panel("shop")
        elif self.btn_dex.rect.collidepoint(pos):
            self.open_dex()
        elif self.btn_set.rect.collidepoint(pos):
            self.open_panel("settings")

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == getattr(pygame, "WINDOWFOCUSLOST", -1) or (
                        e.type == pygame.ACTIVEEVENT and not e.gain and e.state & 6):
                    self.mouse_down = False
                    self.dex_cancel_pointer()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.mouse_down = True
                    if self.dex_open:
                        self.dex_pointer_down(self.dex_page_pos(e.pos), self.dex_input_time(e))
                    else:
                        self.on_click(self.mpos(e.pos))
                elif e.type == pygame.MOUSEMOTION and self.dex_open:
                    if not e.buttons[0]:
                        # UP 누락 중인 드래그만 안전하게 취소. 정상 관성은 hover로 멈추지 않는다.
                        self.mouse_down = False
                        if self.dex_drag is not None or self.dex_press is not None:
                            self.dex_cancel_pointer()
                    else:
                        self.dex_pointer_move(self.dex_page_pos(e.pos), self.dex_input_time(e))
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.mouse_down = False
                    if self.dex_open:
                        self.dex_pointer_up(self.dex_page_pos(e.pos), self.dex_input_time(e))
                    else:
                        self.dex_cancel_pointer()
                elif e.type == pygame.MOUSEWHEEL and self.dex_open and self.dex_sel is None:
                    self.dex_scroll_by(-e.y * 70)
                elif e.type == pygame.KEYDOWN and self.dex_open:
                    self.dex_key(e.key)
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_d:
                        self.open_dex()
                    elif e.key in (pygame.K_UP, pygame.K_SPACE):
                        self.start_upgrade()
                    elif e.key == pygame.K_DOWN:
                        self.do_sell()
                    elif e.key == pygame.K_LEFT:
                        self.adjust_stone(-1)
                    elif e.key == pygame.K_RIGHT:
                        self.adjust_stone(+1)
                    elif e.key == pygame.K_s:
                        self.open_panel("shop")
                    elif e.key == pygame.K_o:
                        self.open_panel("settings")
                    elif e.key == pygame.K_ESCAPE:
                        self.panel = None
                        self.reset_confirm = False
                    elif e.key == pygame.K_1 and self.panel == "shop":
                        self.buy("protect")
                    elif e.key == pygame.K_2 and self.panel == "shop":
                        self.buy("insurance")
                    elif e.key == pygame.K_3 and self.panel == "shop":
                        self.buy("stone")
            self.update(dt)
            self.draw()
        self.st.save()
        pygame.quit()


if __name__ == "__main__":
    Game().run()