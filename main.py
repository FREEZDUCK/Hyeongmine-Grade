# -*- coding: utf-8 -*-
"""형민그레이드 - 검 강화하기 스타일 강화 게임 (pygame)

조작
  Space / ↑ : 업그레이드       ↓ : 형민 판매
  S : 상점     O : 설정 (빠른 업그레이드 · 화면 크기 · 데이터 초기화)
  1 / 2 / 3 : (상점에서) 방지권 / 보험권 / 확률석 구매      Esc : 창 닫기
  ← / → : 확률석 적용 개수 줄이기 / 늘리기 (로비)
  M : 박물관으로 (형민중앙박물관 : 작품 배치 · 상점. Esc = 뒤로, 마우스 휠 / 드래그 = 스크롤)
  박물관 : 배치한 작품이 평균 판매가에 비례해 주기적으로 자동 수입을 만든다.
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
VERSION = "2.0.0v"
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
SELL_POWER = 1.0307               # 판매 값어치 지수
SELL_RAND = (1.1, 1.4)            # 판매 값어치 랜덤 배율
COST_POWER = 1.075                 # 업그레이드 비용 지수

START_MONEY = 100                # 새 게임 시작 자금
UPGRADE_COST_RATE = 0.17         # 현재 단계 판매 기준값의 20%를 강화비로 사용
SELL_VALUE_RANDOM = (0.9, 1.1)   # 단계별 기준 판매가에서 ±10% 변동


# ---- 황금 형민
GOLD_CHANCE = 1               # 업그레이드 성공 시 황금이 될 확률 (1%)
GOLD_SELL_MULT = 2                # 황금 판매 값어치 배율

# ---- 상점 가격 (가격 = max(최소가, 최고 도달 단계의 평균 판매가 × 비율))
PROTECT_PRICE_RATE = 0.1         # 파괴 방지권 : 판매가 대비 비율  ← 오르는 정도 조절
PROTECT_MIN_PRICE = 60            # 파괴 방지권 : 최소 가격
INSURANCE_PRICE_RATE = 0.04       # 파괴 보험권 : 판매가 대비 비율  ← 오르는 정도 조절
INSURANCE_MIN_PRICE = 30          # 파괴 보험권 : 최소 가격
INSURANCE_REFUND = 0.8            # 파괴 시 판매 값어치의 80% 환급

# ---- 확률석
STONE_PRICE_RATE = 0.08           # 확률석 : 판매가 대비 비율  ← 오르는 정도 조절
STONE_MIN_PRICE = 100             # 확률석 : 최소 가격
STONE_BOOST = 15                  # 확률석 1개당 성공 확률 증가량 (%p)
STONE_MAX_USE = 5                 # 한 번의 업그레이드에 적용할 수 있는 최대 개수

# ---- 업그레이드 연출 시간
CHARGE_NORMAL = 1.0               # 원이 다 차는 시간(초)
FAST_FACTOR = 10                  # 빠른 업그레이드 배율

# ---- 미발견 형민(검은 실루엣) 흐림 정도
SILHOUETTE_BLUR = 5               # 흐림 반경(px, 108px 썸네일 기준). 0 = 선명한 실루엣 / 클수록 형태가 뭉개짐
SILHOUETTE_ALPHA = 255            # 실루엣 진하기 (0~255). 낮출수록 옅어짐
SILHOUETTE_COLOR = (22, 22, 26)   # 실루엣 색

# ---- 형민중앙박물관 (자동 수입)
MU_START_SLOTS = 1                # 처음 전시 슬롯 수
MU_MAX_SLOTS = 24                 # 전시 슬롯 최대 개수
MU_INCOME_RATE = 0.01             # 한 번에 들어오는 돈 = 작품 평균 판매가 × 이 비율 (최소 1G)  ← 수입 규모 조절
MU_BASE_INTERVAL = 5.0            # 기본 수입 주기(초)
MU_PROMO_STEP = 0.05               # 홍보 1회당 줄어드는 주기(초)
MU_MIN_INTERVAL = 0.3             # 주기 하한(초)
MU_SLOT_BASE_PRICE = 10000         # 슬롯 확장 첫 가격. 가격 = 기본가 × 증가율^(현재 슬롯 수 - 1)
MU_SLOT_GROWTH = 5.2              # 슬롯 확장 가격 증가율  ← 오르는 정도 조절
MU_PROMO_BASE_PRICE = 20000        # 홍보하기 첫 가격. 가격 = 기본가 × 증가율^(홍보 횟수)
MU_PROMO_GROWTH = 4.2             # 홍보하기 가격 증가율  ← 오르는 정도 조절

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

# ---- 형민중앙박물관 색상 (검은 배경)
MU_BG = (0, 0, 0)
MU_CARD = (20, 20, 25)
MU_CARD_HI = (32, 32, 39)
MU_LINE = (58, 58, 68)
MU_TEXT = (240, 240, 244)
MU_MUTED = (140, 142, 154)


def sell_table():
    """평균 배율로 계산한 단계별 판매가 - 상점 가격 기준"""
    mid = sum(SELL_RAND) / 2
    t, sv = [0], 0
    for _ in range(MAX_LEVEL):
        sv = int((sv + 5) ** SELL_POWER * mid)
        t.append(sv)
    return t


SELL_TABLE = sell_table()


def museum_income(level):
    """작품 1점이 한 번에 벌어다 주는 돈 (평균 판매가에 비례, 판매가가 0인 0단계는 수입 없음)"""
    base = SELL_TABLE[max(0, min(level, MAX_LEVEL))]
    return max(1, int(base * MU_INCOME_RATE)) if base > 0 else 0


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
        elif self.kind == "special":       # 박물관 버튼 : 금빛
            fill, border, tc = (GOLD_L if not hover else (246, 208, 100)), GOLD_D, (58, 38, 0)
        else:
            fill, border, tc = (WHITE if not hover else (244, 244, 246)), LINE_D, INK
        rrect(surf, fill, r, 8)
        rrect(surf, border, r, 8, 1)
        fit_text_width(surf, fonts, self.label, 20 if r.h >= 52 else 17, tc, r.center, r.w - 12,
                       bold=(self.kind in ("primary", "special")), min_size=11)


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
        # 작품 기록(구 도감) : {"단계": {"n": 획득 횟수(=박물관 stack), "g": 황금 횟수, "d": 파괴 횟수, "s": 판매 횟수, "dt": 처음 발견한 날}}
        self.dex = {}
        # 형민중앙박물관 : slots[i] = 그 슬롯에 전시한 작품 단계 (-1 = 빈 슬롯)
        self.slots = [-1] * MU_START_SLOTS
        self.promo = 0            # 홍보하기 구매 횟수
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
        return new, gold_new

    def dex_add(self, level, key):
        self._entry(level)[key] += 1

    # ---- 박물관
    def stack(self, level):
        """지금까지 얻은(발견한) 횟수 = 전시에 쓸 수 있는 작품 총수"""
        e = self.dex.get(str(level))
        return int(e.get("n", 0)) if isinstance(e, dict) else 0

    def placed(self, level, gold=False):
        code = level + (MAX_LEVEL + 1 if gold else 0)
        return sum(1 for v in self.slots if v == code)

    def avail(self, level, gold=False):
        if gold:
            e = self.dex.get(str(level), {})
            total = int(e.get("g", 0)) if isinstance(e, dict) else 0
            return max(0, total - self.placed(level, True))
        return max(0, self.stack(level) - self.placed(level, False))

    @staticmethod
    def slot_info(value):
        if value < 0:
            return -1, False
        gold = value > MAX_LEVEL
        return (value - (MAX_LEVEL + 1) if gold else value), gold

    def used_slots(self):
        return sum(1 for v in self.slots if v >= 0)

    def slot_price(self):
        return int(MU_SLOT_BASE_PRICE * MU_SLOT_GROWTH ** (len(self.slots) - 1))

    def promo_max(self):
        return int(round((MU_BASE_INTERVAL - MU_MIN_INTERVAL) / MU_PROMO_STEP))

    def promo_price(self):
        return int(MU_PROMO_BASE_PRICE * MU_PROMO_GROWTH ** self.promo)

    def interval_at(self, promo):
        return round(max(MU_MIN_INTERVAL, MU_BASE_INTERVAL - MU_PROMO_STEP * promo), 2)

    def interval(self):
        return self.interval_at(self.promo)

    def tick_income(self):
        total = 0
        for value in self.slots:
            lv, gold = self.slot_info(value)
            if lv >= 0:
                total += museum_income(lv) * (GOLD_SELL_MULT if gold else 1)
        return total

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
            # 박물관 : 슬롯 / 홍보 정리 (예전 세이브엔 없으므로 기본값 유지)
            slots = []
            if isinstance(self.slots, list):
                for v in self.slots[:MU_MAX_SLOTS]:
                    try:
                        v = int(v)
                    except (TypeError, ValueError):
                        v = -1
                    slots.append(v if 0 <= v <= MAX_LEVEL * 2 + 1 else -1)
            self.slots = slots or [-1] * MU_START_SLOTS
            used = {}
            for i, v in enumerate(self.slots):      # 가진 수보다 많이 배치돼 있으면 초과분은 비운다
                if v >= 0:
                    lv, gold = self.slot_info(v)
                    key = (lv, gold)
                    used[key] = used.get(key, 0) + 1
                    e = self.dex.get(str(lv), {})
                    owned = int(e.get("g", 0)) if gold and isinstance(e, dict) else self.stack(lv)
                    if used[key] > owned:
                        self.slots[i] = -1
            self.promo = max(0, min(self.promo_max(), int(self.promo)))
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
        self.museum_frame = None
        for frame_path in (os.path.join(BASE, "frame.png"), os.path.join(IMG_DIR, "frame.png")):
            if os.path.isfile(frame_path):
                self.museum_frame = pygame.image.load(frame_path).convert_alpha()
                break

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
        self.btn_sell = Button((40, 748, 86, 48), "형민 판매")
        self.btn_shop = Button((134, 748, 78, 48), "상점")
        self.btn_museum = Button((220, 748, 134, 48), "박물관으로", "special")
        self.btn_set = Button((362, 748, 78, 48), "설정")

        # 형민중앙박물관 화면
        self.mu_open = False
        self.mu_anim = 0.0
        self.mu_view = "main"         # main(슬롯 목록) / place(작품 배치 목록) / slot(배치할 슬롯 고르기)
        self.mu_scroll = {"grid": 0.0, "place": 0.0}
        self.mu_scroll_t = {"grid": 0.0, "place": 0.0}
        self.mu_press = None          # [누른 위치, 그때의 스크롤, 드래그 중인지]
        self.mu_item = None           # 배치 확인 팝업에 띄운 작품 단계
        self.mu_item_gold = False      # 황금 작품 선택 여부
        self.mu_pick = None           # 슬롯을 고르는 중인 작품 단계
        self.mu_recall = None         # 회수 팝업에 띄운 슬롯 번호
        self.mu_panel = None          # None / shop
        self.mu_floats = []
        self.income_t = 0.0           # 수입 주기 타이머
        self.autosave_t = 0.0
        self.mu_back = pygame.Rect(18, 16, 112, 32)
        self.mu_btn_shop = pygame.Rect(40, 744, 194, 54)
        self.mu_btn_place = pygame.Rect(246, 744, 194, 54)
        self.mu_shop_panel = pygame.Rect(30, 150, 420, 430)
        sp = self.mu_shop_panel
        self.mu_shop_close = pygame.Rect(sp.right - 46, sp.y + 12, 30, 30)
        self.mu_shop_rows = []
        for i in range(2):
            row = pygame.Rect(sp.x + 16, sp.y + 64 + i * 166, sp.w - 32, 154)
            self.mu_shop_rows.append((row, pygame.Rect(row.right - 210, row.bottom - 50, 194, 40)))
        self.mu_item_panel = pygame.Rect(40, 130, 400, 550)
        ip = self.mu_item_panel
        self.mu_item_cancel = pygame.Rect(ip.x + 20, ip.bottom - 64, 170, 44)
        self.mu_item_ok = pygame.Rect(ip.right - 190, ip.bottom - 64, 170, 44)
        self.mu_recall_panel = pygame.Rect(24, 72, W - 48, H - 144)
        rp = self.mu_recall_panel
        self.mu_recall_cancel = pygame.Rect(rp.x + 18, rp.bottom - 58, 150, 42)
        self.mu_recall_ok = pygame.Rect(rp.right - 168, rp.bottom - 58, 150, 42)
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
        self.thumbs, self.thumbs_black, self.thumbs_s = [], [], []   # 작품 목록용 작은 이미지 / 검은 실루엣 / 슬롯용
        self.big_cache = {}
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
            self.thumbs_s.append(pygame.transform.smoothscale(flat, (96, 96)))
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
                self.toast_msg(f"신규 작품 입수 : {display_name(s.level, s.golden)}", GOLD_D if s.golden else BLUE)
            elif new_gold:
                self.toast_msg("황금 형민을 처음 발견했습니다!", GOLD_D)
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
        self.mu_open = False
        self.mu_anim = 0.0
        self.mu_reset_ui()
        self.mu_floats = []
        self.mu_scroll = {"grid": 0.0, "place": 0.0}
        self.mu_scroll_t = {"grid": 0.0, "place": 0.0}
        self.income_t = 0.0
        self.st.save()
        self.toast_msg("데이터를 초기화했습니다", INK)

    def open_panel(self, name):
        if self.mode != "idle":
            return
        self.panel = None if self.panel == name else name
        if self.panel:
            self.panel_last = name
        self.reset_confirm = False

# ---------------- 형민중앙박물관 : 상태 / 입력
    MU_COLS, MU_CELL_W, MU_GAP = 3, 136, 12
    MU_SLOT_H, MU_PLACE_H = 150, 160
    MU_TOP = 140                      # 목록 스크롤 영역 시작 y
    MU_NAV_Y = 732                    # 메인 화면 하단 버튼 영역 시작 y

    def mu_key(self):
        return "place" if self.mu_view == "place" else "grid"

    def mu_cell_h(self):
        return self.MU_PLACE_H if self.mu_view == "place" else self.MU_SLOT_H

    def mu_clip_bottom(self):
        return self.MU_NAV_Y - 2 if self.mu_view == "main" else H

    def mu_count(self):
        return len(TITLES) * 2 if self.mu_view == "place" else len(self.st.slots)

    def mu_cell_rect(self, i):
        r, c = divmod(i, self.MU_COLS)
        x = 24 + c * (self.MU_CELL_W + self.MU_GAP)
        y = self.MU_TOP + 8 + r * (self.mu_cell_h() + self.MU_GAP) - self.mu_scroll[self.mu_key()]
        return pygame.Rect(x, int(y), self.MU_CELL_W, self.mu_cell_h())

    def mu_max_scroll(self):
        rows = math.ceil(self.mu_count() / self.MU_COLS)
        total = rows * (self.mu_cell_h() + self.MU_GAP) + 16
        return max(0.0, total - (self.mu_clip_bottom() - self.MU_TOP))

    def mu_scroll_by(self, d):
        key = self.mu_key()
        self.mu_scroll_t[key] = max(0.0, min(self.mu_max_scroll(), self.mu_scroll_t[key] + d))

    def mu_modal(self):
        return self.mu_item is not None or self.mu_recall is not None or self.mu_panel is not None

    def mu_reset_ui(self):
        self.mu_view = "main"
        self.mu_item = None
        self.mu_item_gold = False
        self.mu_pick = None
        self.mu_recall = None
        self.mu_panel = None
        self.mu_press = None

    def open_museum(self):
        if self.mode != "idle" or self.panel or self.mu_open:
            return
        self.mu_open = True
        self.mu_reset_ui()

    def close_museum(self):
        self.mu_open = False
        self.mu_reset_ui()

    def mu_back_action(self):
        """한 단계 뒤로 (팝업 → 슬롯 선택 → 배치 목록 → 박물관 메인 → 게임)"""
        if self.mu_item is not None:
            self.mu_item = None
        elif self.mu_recall is not None:
            self.mu_recall = None
        elif self.mu_panel is not None:
            self.mu_panel = None
        elif self.mu_view == "slot":
            self.mu_view = "place"
            self.mu_pick = None
        elif self.mu_view == "place":
            self.mu_view = "main"
        else:
            self.close_museum()

    def mu_page_pos(self, screen_pos):
        """창 배율 + 박물관 열기 애니메이션의 위치를 반영한 입력 좌표"""
        x, y = self.mpos(screen_pos)
        return x, y - int((1 - ease_out(self.mu_anim)) * 40)

    def mu_pointer_down(self, pos):
        self.mu_press = [pos, self.mu_scroll_t[self.mu_key()], False]

    def mu_pointer_move(self, pos):
        if self.mu_press is None:
            return
        origin, start, _ = self.mu_press
        dx, dy = pos[0] - origin[0], pos[1] - origin[1]
        if math.hypot(dx, dy) > 6:
            self.mu_press[2] = True
        if self.mu_press[2] and not self.mu_modal():
            self.mu_scroll_t[self.mu_key()] = max(0.0, min(self.mu_max_scroll(), start - dy))

    def mu_pointer_up(self, pos):
        self.mu_pointer_move(pos)
        press, self.mu_press = self.mu_press, None
        if press is not None and not press[2]:
            self.mu_click(pos)

    def mu_key_event(self, key):
        free = not self.mu_modal()
        if key == pygame.K_ESCAPE:
            self.mu_back_action()
        elif key == pygame.K_m and free and self.mu_view == "main":
            self.close_museum()
        elif key == pygame.K_s and self.mu_view == "main" and (free or self.mu_panel == "shop"):
            self.mu_panel = None if self.mu_panel else "shop"
        elif free and key == pygame.K_DOWN:
            self.mu_scroll_by(+90)
        elif free and key == pygame.K_UP:
            self.mu_scroll_by(-90)
        elif free and key == pygame.K_PAGEDOWN:
            self.mu_scroll_by(+500)
        elif free and key == pygame.K_PAGEUP:
            self.mu_scroll_by(-500)

    def mu_click(self, pos):
        s = self.st
        # ---- 팝업이 떠 있으면 팝업만 상대한다
        if self.mu_panel == "shop":
            if self.mu_shop_close.collidepoint(pos) or not self.mu_shop_panel.collidepoint(pos):
                self.mu_panel = None
                return
            for i, (_, buy) in enumerate(self.mu_shop_rows):
                if buy.collidepoint(pos):
                    self.mu_buy(("slot", "promo")[i])
            return
        if self.mu_item is not None:
            lv = self.mu_item
            toggle_rect = pygame.Rect(self.mu_item_panel.x + 35, self.mu_item_panel.y + 365, self.mu_item_panel.w - 70, 34)
            if self.mu_item_cancel.collidepoint(pos) or not self.mu_item_panel.collidepoint(pos):
                self.mu_item = None
                self.mu_item_gold = False
            elif toggle_rect.collidepoint(pos) and int(s.dex.get(str(lv), {}).get("g", 0)) > 0:
                self.mu_item_gold = not self.mu_item_gold
            elif self.mu_item_ok.collidepoint(pos):
                if s.avail(lv, self.mu_item_gold) <= 0:
                    self.toast_msg("배치할 수 있는 작품이 남아 있지 않습니다", RED)
                else:
                    self.mu_pick = (lv, self.mu_item_gold)
                    self.mu_item = None
                    self.mu_item_gold = False
                    self.mu_view = "slot"
            return
        if self.mu_recall is not None:
            idx = self.mu_recall
            if self.mu_recall_cancel.collidepoint(pos) or not self.mu_recall_panel.collidepoint(pos):
                self.mu_recall = None
            elif self.mu_recall_ok.collidepoint(pos):
                if 0 <= idx < len(s.slots) and s.slots[idx] >= 0:
                    lv, gold = s.slot_info(s.slots[idx])
                    name = display_name(lv, gold)
                    s.slots[idx] = -1
                    s.save()
                    self.toast_msg(f"[{name}] 회수했습니다", MU_MUTED)
                self.mu_recall = None
            return

        if self.mu_back.collidepoint(pos):
            self.mu_back_action()
            return
        in_grid = self.MU_TOP <= pos[1] < self.mu_clip_bottom()

        if self.mu_view == "main":
            if self.mu_btn_shop.collidepoint(pos):
                self.mu_panel = "shop"
            elif self.mu_btn_place.collidepoint(pos):
                self.mu_view = "place"
            elif in_grid:
                for i, lv in enumerate(s.slots):
                    if self.mu_cell_rect(i).collidepoint(pos):
                        if lv >= 0:
                            self.mu_recall = i
                        else:
                            self.toast_msg("'작품 배치'로 작품을 전시해 보세요", MU_MUTED)
                        return
        elif self.mu_view == "place":
            if in_grid:
                for item_i in range(len(TITLES) * 2):
                    if self.mu_cell_rect(item_i).collidepoint(pos):
                        i, gold_item = item_i % len(TITLES), item_i >= len(TITLES)
                        if str(i) not in s.dex or (gold_item and int(s.dex.get(str(i), {}).get("g", 0)) <= 0):
                            self.toast_msg("아직 발견하지 못한 작품입니다", MU_MUTED)
                        elif s.avail(i, gold_item) <= 0:
                            self.toast_msg("남은 작품이 없습니다 (모두 전시 중)", MU_MUTED)
                        else:
                            self.mu_item = i
                            self.mu_item_gold = gold_item
                        return
        elif self.mu_view == "slot":
            if in_grid:
                for i in range(len(s.slots)):
                    if self.mu_cell_rect(i).collidepoint(pos):
                        self.place_work(i, self.mu_pick)
                        return

    def place_work(self, idx, selection):
        s = self.st
        if selection is None or not (0 <= idx < len(s.slots)):
            return
        level, gold = selection if isinstance(selection, tuple) else (selection, False)
        code = level + (MAX_LEVEL + 1 if gold else 0)
        if s.slots[idx] == code:
            self.toast_msg("이미 같은 작품이 전시되어 있습니다", MU_MUTED)
            return
        if s.avail(level, gold) <= 0:
            self.toast_msg("배치할 수 있는 작품이 남아 있지 않습니다", RED)
            self.mu_view, self.mu_pick = "place", None
            return
        s.slots[idx] = code
        s.save()
        self.mu_view, self.mu_pick = "place", None
        self.toast_msg(f"슬롯 {idx + 1}에 [{display_name(level, gold)}] 전시", GOLD_L)

    def mu_buy(self, which):
        s = self.st
        if which == "slot":
            if len(s.slots) >= MU_MAX_SLOTS:
                self.toast_msg("더 이상 슬롯을 늘릴 수 없습니다", MU_MUTED)
                return
            price = s.slot_price()
        else:
            if s.promo >= s.promo_max():
                self.toast_msg("이미 최대로 홍보했습니다", MU_MUTED)
                return
            price = s.promo_price()
        if s.money < price:
            self.toast_msg("자산이 부족합니다", RED)
            return
        s.money -= price
        if which == "slot":
            s.slots.append(-1)
            self.toast_msg(f"전시 슬롯이 {len(s.slots)}칸이 되었습니다", GOLD_L)
        else:
            s.promo += 1
            self.toast_msg(f"수입 주기가 {s.interval():.1f}초가 되었습니다", GOLD_L)
        self.mu_floats.append(FloatText(f"-{fmt(price)}G", W // 2, self.mu_shop_panel.y - 14, RED, 20, 1.0))
        s.save()

    # ---------------- 형민중앙박물관 : 자동 수입
    def museum_tick(self, dt):
        s = self.st
        interval = s.interval()
        self.income_t += dt
        n = 0
        while self.income_t >= interval and n < 10:
            self.income_t -= interval
            n += 1
            gain = s.tick_income()
            if gain > 0:
                s.money += gain
                self.mu_income_fx()
        if n >= 10:
            self.income_t = 0.0

    def mu_income_fx(self):
        """수입이 들어올 때 보이는 슬롯 위에 +금액 표시"""
        if not self.mu_open or self.mu_anim < 0.5 or self.mu_view == "place" or self.mu_modal():
            return
        n = 0
        for i, value in enumerate(self.st.slots):
            lv, gold = self.st.slot_info(value)
            if lv < 0:
                continue
            r = self.mu_cell_rect(i)
            if r.top < self.MU_TOP or r.bottom > self.mu_clip_bottom():
                continue
            self.mu_floats.append(FloatText(f"+{fmt(museum_income(lv) * (GOLD_SELL_MULT if gold else 1))}", r.centerx, r.y + 58, GOLD_L, 15, 0.9))
            n += 1
            if n >= 12:
                break

    # ---------------- 형민중앙박물관 : 그리기
    def big_sprite(self, level, size=168):
        key = (level, size)
        if key not in self.big_cache:
            self.big_cache[key] = pygame.transform.smoothscale(self.sprites[level], (size, size))
        return self.big_cache[key]

    def mu_btn(self, surf, rect, label, kind, mouse, size=17):
        hv = rect.collidepoint(mouse)
        if kind == "gold":
            fill, border, tc = (246, 208, 100) if hv else GOLD_L, GOLD_D, (58, 38, 0)
        elif kind == "off":
            fill, border, tc = (34, 34, 40), MU_LINE, (104, 106, 116)
        else:
            fill, border, tc = (MU_CARD_HI if hv else MU_CARD), (96, 98, 110), MU_TEXT
        rrect(surf, fill, rect, 10)
        rrect(surf, border, rect, 10, 1)
        fit_text_width(surf, self.fonts, label, size, tc, rect.center, rect.w - 14,
                       bold=(kind == "gold"), min_size=10)

    def draw_mu_close(self, surf, cl, mouse):
        hv = cl.collidepoint(mouse)
        pygame.draw.circle(surf, (48, 48, 56) if hv else (30, 30, 36), cl.center, 15)
        cx, cy = cl.center
        pygame.draw.line(surf, MU_TEXT, (cx - 5, cy - 5), (cx + 5, cy + 5), 2)
        pygame.draw.line(surf, MU_TEXT, (cx - 5, cy + 5), (cx + 5, cy - 5), 2)

    def draw_mu_scrollbar(self, page):
        mx = self.mu_max_scroll()
        if mx <= 0:
            return
        view = self.mu_clip_bottom() - self.MU_TOP
        th = max(36, int(view * view / (view + mx)))
        ty = self.MU_TOP + int((view - th - 6) * self.mu_scroll[self.mu_key()] / mx)
        rrect(page, (74, 76, 86), (W - 11, ty, 4, th), 2)

    def draw_mu_header(self, page, mouse):
        f = self.fonts
        s = self.st
        view = self.mu_view
        label = {"main": "‹ 돌아가기", "place": "‹ 박물관", "slot": "‹ 취소"}[view]
        self.mu_btn(page, self.mu_back, label, "outline", mouse, 15)
        text(page, f, "자산", 11, MU_MUTED, (W - 24, 20), "midright")
        fit_text_width(page, f, fmt(self.disp_money) + " G", 20, MU_TEXT, (W - 24, 40), 220,
                       "midright", True, True, 10)
        title = {"main": "형민중앙박물관", "place": "작품 배치", "slot": "슬롯 선택"}[view]
        text(page, f, title, 30 if view == "main" else 26, MU_TEXT, (W // 2, 84), bold=True, serif=True)
        pygame.draw.line(page, GOLD_D, (W // 2 - 50, 106), (W // 2 + 50, 106), 2)
        if view == "main":
            info = f"{s.interval():.1f}초마다 +{fmt(s.tick_income())}G  ·  전시 {s.used_slots()}/{len(s.slots)}칸"
            fit_text_width(page, f, info, 14, GOLD_L, (W // 2, 124), W - 48, bold=True, min_size=10)
        elif view == "place":
            text(page, f, f"전시 {s.used_slots()}/{len(s.slots)}칸  ·  작품을 눌러 배치", 13, MU_MUTED, (W // 2, 124))
        else:
            selection = self.mu_pick if self.mu_pick is not None else (0, False)
            lv, gold = selection if isinstance(selection, tuple) else (selection, False)
            fit_text_width(page, f, f"[{display_name(lv, gold)}] 을(를) 전시할 슬롯을 고르세요", 14, GOLD_L,
                           (W // 2, 124), W - 48, bold=True, min_size=10)
        pygame.draw.line(page, MU_LINE, (24, self.MU_TOP - 6), (W - 24, self.MU_TOP - 6))

    def draw_mu_slots(self, page, mouse, picking):
        f = self.fonts
        s = self.st
        clip = pygame.Rect(0, self.MU_TOP - 4, W, self.mu_clip_bottom() - self.MU_TOP + 4)
        page.set_clip(clip)
        dragging = bool(self.mu_press and self.mu_press[2])
        for i, value in enumerate(s.slots):
            lv, gold = s.slot_info(value)
            r = self.mu_cell_rect(i)
            if r.bottom < self.MU_TOP - 4 or r.top > clip.bottom:
                continue
            hover = not dragging and clip.collidepoint(mouse) and r.collidepoint(mouse)
            rr = r.move(0, -3 if hover else 0)
            rrect(page, MU_CARD_HI if hover else MU_CARD, rr, 14)
            rrect(page, GOLD_L if picking else (GOLD_L if gold and lv >= 0 else GOLD_D if lv >= 0 else MU_LINE), rr, 14, 1)
            plate = pygame.Rect(0, 0, 104, 104)
            plate.midtop = (rr.centerx, rr.y + 10)
            if lv >= 0:
                rrect(page, WHITE, plate, 10)
                if gold:
                    gold_thumb = pygame.transform.smoothscale(self.sprites_gold[lv], (96, 96))
                    page.blit(gold_thumb, gold_thumb.get_rect(center=plate.center))
                    pygame.draw.rect(page, GOLD_L, plate, 3, border_radius=10)
                else:
                    page.blit(self.thumbs_s[lv], self.thumbs_s[lv].get_rect(center=plate.center))
            else:
                rrect(page, (10, 10, 13), plate, 10)
                rrect(page, MU_LINE, plate, 10, 1)
                text(page, f, "+", 40, (70, 72, 82), plate.center, bold=True)
            pill = pygame.Rect(rr.x + 8, rr.y + 8, 24, 18)
            rrect(page, (0, 0, 0), pill, 9)
            rrect(page, MU_LINE, pill, 9, 1)
            text(page, f, str(i + 1), 11, MU_TEXT, pill.center, bold=True)
            if lv >= 0:
                name = fit_text(f.get(12, True), display_name(lv, gold), rr.w - 14)
                text(page, f, name, 12, MU_TEXT, (rr.centerx, rr.y + 126), bold=True)
                text(page, f, f"+{fmt(museum_income(lv) * (GOLD_SELL_MULT if gold else 1))}G", 12, GOLD_L, (rr.centerx, rr.y + 141), bold=True)
            else:
                text(page, f, "빈 슬롯", 12, MU_MUTED, (rr.centerx, rr.y + 126), bold=True)
                text(page, f, "선택하기" if picking else "비어 있음", 12,
                     GOLD_L if picking else (96, 98, 108), (rr.centerx, rr.y + 141))
        page.set_clip(None)
        self.draw_mu_scrollbar(page)

    def draw_mu_place(self, page, mouse):
        f = self.fonts
        s = self.st
        clip = pygame.Rect(0, self.MU_TOP - 4, W, H - self.MU_TOP + 4)
        page.set_clip(clip)
        dragging = bool(self.mu_press and self.mu_press[2])
        for item_i in range(len(TITLES) * 2):
            i = item_i % len(TITLES)
            gold_item = item_i >= len(TITLES)
            r = self.mu_cell_rect(item_i)
            if r.bottom < self.MU_TOP - 4 or r.top > H:
                continue
            ok = str(i) in s.dex and (not gold_item or int(s.dex.get(str(i), {}).get("g", 0)) > 0)
            hover = ok and not dragging and clip.collidepoint(mouse) and r.collidepoint(mouse)
            rr = r.move(0, -3 if hover else 0)
            av, pl = s.avail(i, gold_item), s.placed(i, gold_item)
            rrect(page, MU_CARD_HI if hover else MU_CARD, rr, 14)
            rrect(page, GOLD_L if gold_item and pl > 0 else GOLD_D if pl > 0 else MU_LINE, rr, 14, 1)
            plate = pygame.Rect(0, 0, 116, 116)
            plate.midtop = (rr.centerx, rr.y + 8)
            if ok:
                rrect(page, WHITE, plate, 12)
                page.blit(self.thumbs[i], self.thumbs[i].get_rect(center=plate.center))
                if gold_item:
                    pygame.draw.rect(page, GOLD_L, plate, 3, border_radius=12)
                # 이미지 오른쪽 아래 : stack (사용 가능한 작품 수)
                label = str(av)
                fnt = f.get(13, True)
                pill = pygame.Rect(0, 0, max(28, fnt.size(label)[0] + 16), 22)
                pill.bottomright = (plate.right - 5, plate.bottom - 5)
                rrect(page, (14, 14, 18) if av > 0 else (84, 86, 96), pill, 11)
                rrect(page, GOLD_L if av > 0 else MU_LINE, pill, 11, 1)
                text(page, f, label, 13, GOLD_L if av > 0 else (200, 202, 210), pill.center, bold=True)
                name = fit_text(f.get(13, True), display_name(i, gold_item), rr.w - 14)
                text(page, f, name, 13, MU_TEXT, (rr.centerx, rr.y + 134), bold=True)
                inc = museum_income(i) * (GOLD_SELL_MULT if gold_item else 1)
                sub = "수입 없음" if inc <= 0 else f"+{fmt(inc)}G" + (f" · 전시 {pl}" if pl else "")
                sub = fit_text(f.get(11), sub, rr.w - 12)
                text(page, f, sub, 11, GOLD_L if inc > 0 else MU_MUTED, (rr.centerx, rr.y + 150))
            else:
                rrect(page, (236, 236, 240), plate, 12)
                page.blit(self.thumbs_black[i], self.thumbs_black[i].get_rect(center=plate.center))
                text(page, f, "? ? ?", 13, MU_MUTED, (rr.centerx, rr.y + 134), bold=True)
                text(page, f, f"No.{i + 1:02d}", 11, (96, 98, 108), (rr.centerx, rr.y + 150))
        page.set_clip(None)
        self.draw_mu_scrollbar(page)

    def draw_mu_item_popup(self, page, mouse):
        f = self.fonts
        s = self.st
        lv = self.mu_item
        alpha_rect(page, (0, 0, 0, 200), (0, 0, W, H))
        p = self.mu_item_panel
        rrect(page, MU_CARD, p, 20)
        rrect(page, GOLD_D, p, 20, 1)
        plate = pygame.Rect(0, 0, 184, 184)
        plate.midtop = (p.centerx, p.y + 22)
        rrect(page, WHITE, plate, 14)
        big = pygame.transform.smoothscale((self.sprites_gold if self.mu_item_gold else self.sprites)[lv], (168, 168))
        page.blit(big, big.get_rect(center=plate.center))
        name = display_name(lv, self.mu_item_gold)
        size = 22
        while size > 13 and f.get(size, True, True).size(name)[0] > p.w - 40:
            size -= 1
        text(page, f, name, size, MU_TEXT, (p.centerx, p.y + 232), bold=True, serif=True)
        text(page, f, f"No.{lv + 1:02d}  ·  {lv}Min", 12, MU_MUTED, (p.centerx, p.y + 256))
        inc = museum_income(lv) * (GOLD_SELL_MULT if self.mu_item_gold else 1)
        owned = int(s.dex.get(str(lv), {}).get("g", 0)) if self.mu_item_gold else s.stack(lv)
        rows = [("보유 작품", f"{owned}개"),
                ("전시 중", f"{s.placed(lv, self.mu_item_gold)}개"),
                ("배치 가능", f"{s.avail(lv, self.mu_item_gold)}개"),
                ("수입", "없음" if inc <= 0 else f"+{fmt(inc)}G / {s.interval():.1f}초")]
        y = p.y + 266
        for label, val in rows:
            text(page, f, label, 13, MU_MUTED, (p.x + 28, y + 12), "midleft")
            text(page, f, val, 14, GOLD_L if label == "수입" and inc > 0 else MU_TEXT,
                 (p.right - 28, y + 12), "midright", True)
            pygame.draw.line(page, MU_LINE, (p.x + 22, y + 25), (p.right - 22, y + 25))
            y += 22
        toggle = pygame.Rect(p.x + 35, p.y + 365, p.w - 70, 34)
        has_gold = int(s.dex.get(str(lv), {}).get("g", 0)) > 0
        self.mu_btn(page, toggle, "황금 작품 보기 · ×2 수입" if not self.mu_item_gold else "일반 작품 보기", "gold" if self.mu_item_gold else "outline", mouse, 13)
        self.mu_btn(page, self.mu_item_cancel, "취소", "outline", mouse)
        self.mu_btn(page, self.mu_item_ok, "배치", "gold" if s.avail(lv, self.mu_item_gold) > 0 else "off", mouse, 19)
        if not has_gold:
            text(page, f, "황금 작품을 아직 발견하지 못했습니다", 10, MU_MUTED, (toggle.centerx, toggle.bottom + 12))

    def draw_mu_recall_popup(self, page, mouse):
        f = self.fonts
        s = self.st
        idx = self.mu_recall
        value = s.slots[idx] if 0 <= idx < len(s.slots) else -1
        lv, gold = s.slot_info(value)
        # 거의 화면 전체를 덮는 전시 감상 패널
        alpha_rect(page, (0, 0, 0, 232), (0, 0, W, H))
        p = pygame.Rect(24, 72, W - 48, H - 144)  # 화면의 약 80%
        rrect(page, (5, 5, 7), p, 8)
        rrect(page, GOLD_D if gold else (72, 62, 48), p, 8, 1)
        text(page, f, "형민중앙박물관  ·  특별 전시" if gold else "형민중앙박물관  ·  소장 작품", 13,
             GOLD_L if gold else MU_MUTED, (p.centerx, p.y + 28), bold=True, serif=True)
        if lv < 0:
            self.mu_btn(page, self.mu_recall_cancel, "닫기", "outline", mouse)
            return
        name = display_name(lv, gold)
        # 검은 전시 벽 + 위쪽 스포트라이트 원뿔
        art_area = pygame.Rect(p.x + 18, p.y + 54, p.w - 36, p.h - 170)
        pygame.draw.rect(page, (0, 0, 0), art_area)
        light = pygame.Surface((W, H), pygame.SRCALPHA)
        cx, top = art_area.centerx, art_area.y + 2
        tint = (255, 206, 94) if gold else (255, 244, 218)
        pygame.draw.polygon(light, (*tint, 24 if gold else 18),
                            [(cx - 10, top), (cx + 10, top), (cx + 150, art_area.bottom - 8), (cx - 150, art_area.bottom - 8)])
        pygame.draw.ellipse(light, (*tint, 20 if gold else 14),
                            (cx - 150, art_area.y + 35, 300, art_area.h - 25))
        page.blit(light, (0, 0))
        # frame.png is drawn as an overlay around the artwork
        frame_size = min(art_area.w - 34, art_area.h - 38, 300)
        frame_rect = pygame.Rect(0, 0, frame_size, frame_size)
        frame_rect.center = (art_area.centerx, art_area.centery + 8)
        img = pygame.transform.smoothscale((self.sprites_gold if gold else self.sprites)[lv], (frame_size - 34, frame_size - 34))
        if gold:
            glow = pygame.Surface((frame_size, frame_size), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 190, 45, 42), (frame_size // 2, frame_size // 2), frame_size // 2 - 4)
            page.blit(glow, frame_rect)
        page.blit(img, img.get_rect(center=frame_rect.center))
        if self.museum_frame is not None:
            frame = pygame.transform.smoothscale(self.museum_frame, frame_rect.size)
            page.blit(frame, frame_rect)
        else:
            pygame.draw.rect(page, GOLD_D if gold else (112, 86, 54), frame_rect, 8)
            pygame.draw.rect(page, GOLD_L if gold else (170, 140, 94), frame_rect.inflate(-12, -12), 2)
        title_y = art_area.bottom - 20
        fit_text_width(page, f, name, 24, GOLD_L if gold else MU_TEXT, (p.centerx, title_y), p.w - 36, bold=True, serif=True, min_size=13)
        income = museum_income(lv) * (GOLD_SELL_MULT if gold else 1)
        text(page, f, f"No.{lv + 1:02d}  ·  작품 가치 {fmt(SELL_TABLE[lv] * (GOLD_SELL_MULT if gold else 1))}G", 12,
             MU_MUTED, (p.centerx, title_y + 28))
        text(page, f, f"자동 수입  +{fmt(income)}G / {s.interval():.1f}초", 13,
             GOLD_L, (p.centerx, title_y + 50), bold=True)
        # 버튼은 화면 하단에 정돈
        self.mu_btn(page, self.mu_recall_cancel, "닫기", "outline", mouse)
        self.mu_btn(page, self.mu_recall_ok, "회수", "gold", mouse, 18)

    def draw_mu_shop(self, page, mouse):
        f = self.fonts
        s = self.st
        alpha_rect(page, (0, 0, 0, 200), (0, 0, W, H))
        p = self.mu_shop_panel
        rrect(page, MU_CARD, p, 20)
        rrect(page, GOLD_D, p, 20, 1)
        text(page, f, "박물관 상점", 26, MU_TEXT, (p.x + 24, p.y + 30), "midleft", True, True)
        fit_text_width(page, f, f"보유 {fmt(s.money)}G", 14, MU_MUTED, (p.right - 60, p.y + 30), 190, "midright", min_size=8)
        self.draw_mu_close(page, self.mu_shop_close, mouse)

        n = len(s.slots)
        slot_max = n >= MU_MAX_SLOTS
        promo_max = s.promo >= s.promo_max()
        items = [
            ("slot", "전시 슬롯 늘리기",
             f"전시할 수 있는 작품이 1점 늘어납니다.\n현재 {n}칸 → " + ("최대" if slot_max else f"{n + 1}칸"),
             f"{n} / {MU_MAX_SLOTS}칸", s.slot_price(), slot_max),
            ("promo", "홍보하기",
             f"수입이 들어오는 주기가 {MU_PROMO_STEP:.1f}초 짧아집니다.\n현재 {s.interval():.1f}초 → "
             + ("최소" if promo_max else f"{s.interval_at(s.promo + 1):.1f}초"),
             f"{s.promo} / {s.promo_max()}회", s.promo_price(), promo_max),
        ]
        for i, (key, name, desc, status, price, maxed) in enumerate(items):
            row, buy = self.mu_shop_rows[i]
            rrect(page, (28, 28, 34), row, 14)
            rrect(page, MU_LINE, row, 14, 1)
            ic = pygame.Rect(row.x + 16, row.y + 16, 54, 54)
            pygame.draw.circle(page, (10, 10, 13), ic.center, 27)
            pygame.draw.circle(page, GOLD_L, ic.center, 27, 2)
            cx, cy = ic.center
            if key == "slot":      # 액자 + 플러스
                pygame.draw.rect(page, GOLD_L, (cx - 13, cy - 13, 26, 26), 2, border_radius=3)
                pygame.draw.line(page, GOLD_L, (cx - 6, cy), (cx + 6, cy), 2)
                pygame.draw.line(page, GOLD_L, (cx, cy - 6), (cx, cy + 6), 2)
            else:                  # 시계 (주기)
                pygame.draw.circle(page, GOLD_L, (cx, cy), 14, 2)
                pygame.draw.line(page, GOLD_L, (cx, cy), (cx, cy - 8), 2)
                pygame.draw.line(page, GOLD_L, (cx, cy), (cx + 6, cy + 3), 2)
            text(page, f, name, 19, MU_TEXT, (ic.right + 14, row.y + 28), "midleft", True, True)
            text(page, f, status, 13, GOLD_L, (row.right - 16, row.y + 28), "midright", True)
            for j, line in enumerate(desc.split("\n")):
                text(page, f, line, 12, MU_MUTED, (ic.right + 14, row.y + 54 + j * 18), "midleft")
            afford = s.money >= price
            if maxed:
                self.mu_btn(page, buy, "최대", "off", mouse, 16)
            else:
                hover = buy.collidepoint(mouse) and afford
                if afford:
                    rrect(page, (246, 208, 100) if hover else GOLD_L, buy, 10)
                else:
                    rrect(page, (40, 40, 48), buy, 10)
                fit_text_width(page, f, f"{fmt(price)}G 구매", 16, (58, 38, 0) if afford else (110, 112, 122),
                               buy.center, buy.w - 12, bold=True, min_size=10)
        text(page, f, "가격은 구매할 때마다 크게 오릅니다", 12, MU_MUTED, (p.centerx, p.bottom - 18))

    def draw_museum(self, surf):
        if self.mu_anim < 0.02:
            return
        k = self.mu_anim
        page = pygame.Surface((W, H))
        page.fill(MU_BG)
        real = self.mu_page_pos(pygame.mouse.get_pos())
        modal = self.mu_modal()
        m = (-1, -1) if modal else real
        view = self.mu_view
        self.draw_mu_header(page, m)
        if view == "place":
            self.draw_mu_place(page, m)
        else:
            self.draw_mu_slots(page, m, view == "slot")
        if view == "main":
            pygame.draw.line(page, MU_LINE, (24, self.MU_NAV_Y - 6), (W - 24, self.MU_NAV_Y - 6))
            self.mu_btn(page, self.mu_btn_shop, "상점", "outline", m, 20)
            self.mu_btn(page, self.mu_btn_place, "작품 배치", "gold", m, 20)
        for fl in self.mu_floats:
            fl.draw(page, self.fonts)
        if self.mu_panel == "shop":
            self.draw_mu_shop(page, real)
        elif self.mu_item is not None:
            self.draw_mu_item_popup(page, real)
        elif self.mu_recall is not None:
            self.draw_mu_recall_popup(page, real)
        page.set_alpha(int(255 * min(1.0, k * 1.2)))
        surf.blit(page, (0, int((1 - ease_out(k)) * 40)))    # ---------------- 이펙트 생성
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

        # 형민중앙박물관 : 열기/닫기 애니메이션, 스크롤, 자동 수입
        self.mu_anim = lerp(self.mu_anim, 1.0 if self.mu_open else 0.0, min(1.0, dt * 14))
        if not self.mu_open and self.mu_anim < 0.02:
            self.mu_anim = 0.0
        key = self.mu_key()
        self.mu_scroll_t[key] = max(0.0, min(self.mu_max_scroll(), self.mu_scroll_t[key]))
        self.mu_scroll[key] = lerp(self.mu_scroll[key], self.mu_scroll_t[key], min(1.0, dt * 16))
        if abs(self.mu_scroll[key] - self.mu_scroll_t[key]) < 0.3:
            self.mu_scroll[key] = self.mu_scroll_t[key]
        self.mu_floats = [p for p in self.mu_floats if p.update(dt)]
        self.museum_tick(dt)
        self.autosave_t += dt
        if self.autosave_t >= 5.0:
            self.autosave_t = 0.0
            s.save()

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
            if self.mu_open:      # 검은 박물관 배경 위에서도 보이도록 테두리
                pygame.draw.rect(surf, (96, 98, 110), r, 1, border_radius=16)
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
        locked = self.panel is not None or self.mu_open
        busy = self.mode != "idle" or locked
        self.btn_up.enabled = not busy and s.level < MAX_LEVEL and s.money >= s.next_cost
        self.btn_up.label = "최고 단계" if s.level >= MAX_LEVEL else "업그레이드"
        self.btn_sell.enabled = not busy and s.sell_value > 0
        self.btn_shop.enabled = self.mode == "idle"
        self.btn_museum.enabled = self.mode == "idle"
        self.btn_set.enabled = self.mode == "idle"
        m = (-1, -1) if locked else mouse
        for b in (self.btn_up, self.btn_sell, self.btn_shop, self.btn_museum, self.btn_set):
            b.draw(world, self.fonts, m, self.mouse_down and not locked)
        text(world, self.fonts, f"시도 {s.attempts} · 성공 {s.successes} · 파괴 {s.destroyed} · 황금 {s.golds}   |   최고 {s.best}Min",
             11, MUTED, (W // 2, 810))

        for c in self.coins:
            c.draw(world)
        for f in self.floats:
            f.draw(world, self.fonts)
        self.draw_panel(world)
        self.draw_museum(world)
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
        elif self.btn_museum.rect.collidepoint(pos):
            self.open_museum()
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
                    self.mu_press = None
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.mouse_down = True
                    if self.mu_open:
                        self.mu_pointer_down(self.mu_page_pos(e.pos))
                    else:
                        self.on_click(self.mpos(e.pos))
                elif e.type == pygame.MOUSEMOTION and self.mu_open:
                    if not e.buttons[0]:
                        self.mouse_down = False
                        self.mu_press = None
                    else:
                        self.mu_pointer_move(self.mu_page_pos(e.pos))
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.mouse_down = False
                    if self.mu_open:
                        self.mu_pointer_up(self.mu_page_pos(e.pos))
                elif e.type == pygame.MOUSEWHEEL and self.mu_open:
                    if not self.mu_modal() and self.mu_view != "main" or (
                            self.mu_view == "main" and not self.mu_modal()):
                        self.mu_scroll_by(-e.y * 70)
                elif e.type == pygame.KEYDOWN and self.mu_open:
                    self.mu_key_event(e.key)
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_m:
                        self.open_museum()
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