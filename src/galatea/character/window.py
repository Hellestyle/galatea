"""Pygame window: draws the Galatea character and conversation UI."""

from __future__ import annotations

import math
import random
import time

import pygame

from ..config import CharacterConfig
from ..state import AppState
from .lipsync import Lipsync, MouthState

# ── Palette ──────────────────────────────────────────────────────────────────
BG_TOP    = (12,  12,  32)
BG_BOT    = (28,  28,  68)
SKIN      = (255, 210, 175)
SKIN_SH   = (230, 180, 145)   # shadow / ears
HAIR      = (48,  28,  18)
EYE_WHITE = (248, 250, 255)
IRIS      = (70,  130, 200)
IRIS_RIM  = (40,   80, 155)
PUPIL     = (12,   12,  20)
LIP       = (210,  88,  88)
LIP_DRK   = (168,  55,  55)
TEETH     = (252, 250, 242)
MOUTH_DRK = (38,   15,  15)
CHEEK     = (255, 155, 155, 55)   # rgba

STATUS_COLOR: dict[str, tuple[int, int, int]] = {
    "idle":       (90,  90, 115),
    "listening":  (70, 210,  95),
    "processing": (220, 185,  50),
    "thinking":   (200, 150, 240),
    "speaking":   (70, 145, 225),
    "error":      (225,  70,  70),
}

STATUS_LABEL: dict[str, str] = {
    "idle":       "Idle",
    "listening":  "Listening…",
    "processing": "Transcribing…",
    "thinking":   "Thinking…",
    "speaking":   "Speaking",
    "error":      "Error",
}


class CharacterWindow:
    def __init__(self, config: CharacterConfig, state: AppState) -> None:
        self.cfg = config
        self.state = state
        self.lipsync = Lipsync(config.mouth_anim_fps)

        # Character face anchor
        self.cx = config.window_width // 2
        self.cy = 168

        # Blink state
        self._blink_next = time.monotonic() + random.uniform(2.5, 5.0)
        self._blink_start: float | None = None
        self._blink_dur = 0.16

        # Cached surfaces (created after pygame.init)
        self._bg: pygame.Surface | None = None
        self._cheek_surf: pygame.Surface | None = None

    # ── Public entry point ───────────────────────────────────────────────────

    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption("Galatea")
        screen = pygame.display.set_mode((self.cfg.window_width, self.cfg.window_height))
        clock = pygame.time.Clock()

        font_sm = pygame.font.SysFont("sans", 15)
        font_md = pygame.font.SysFont("sans", 18, bold=True)

        self._bg = self._make_gradient()
        self._cheek_surf = self._make_cheek_surf()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state.running = False
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state.running = False
                    pygame.quit()
                    return

            status = self.state.status
            amplitude = self.state.amplitude
            speaking = status == "speaking"

            mouth = self.lipsync.update(speaking, amplitude)
            eye_open = self._update_blink()

            screen.blit(self._bg, (0, 0))  # type: ignore[arg-type]
            self._draw_character(screen, mouth, eye_open, status)
            self._draw_status_bar(screen, font_md, font_sm, status)
            self._draw_conversation(screen, font_sm)

            pygame.display.flip()
            clock.tick(self.cfg.fps)

    # ── Background ───────────────────────────────────────────────────────────

    def _make_gradient(self) -> pygame.Surface:
        surf = pygame.Surface((self.cfg.window_width, self.cfg.window_height))
        h = self.cfg.window_height
        for y in range(h):
            t = y / h
            r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
            g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
            b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (self.cfg.window_width, y))
        return surf

    def _make_cheek_surf(self) -> pygame.Surface:
        surf = pygame.Surface((52, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, CHEEK, (0, 0, 52, 26))
        return surf

    # ── Blink ────────────────────────────────────────────────────────────────

    def _update_blink(self) -> float:
        """Returns eye openness 0.0 (closed) – 1.0 (fully open)."""
        now = time.monotonic()
        if self._blink_start is not None:
            elapsed = now - self._blink_start
            half = self._blink_dur / 2
            if elapsed < half:
                return max(0.0, 1.0 - elapsed / half)
            elif elapsed < self._blink_dur:
                return max(0.0, (elapsed - half) / half)
            else:
                self._blink_start = None
                self._blink_next = now + random.uniform(2.5, 5.5)
                return 1.0
        elif now >= self._blink_next:
            self._blink_start = now
        return 1.0

    # ── Character drawing ────────────────────────────────────────────────────

    def _draw_character(
        self,
        screen: pygame.Surface,
        mouth: MouthState,
        eye_open: float,
        status: str,
    ) -> None:
        cx, cy = self.cx, self.cy

        # ── Ears ──
        pygame.draw.ellipse(screen, SKIN_SH, (cx - 97, cy - 22, 22, 32))
        pygame.draw.ellipse(screen, SKIN_SH, (cx + 75,  cy - 22, 22, 32))

        # ── Head ──
        pygame.draw.ellipse(screen, SKIN, (cx - 88, cy - 108, 176, 216))

        # ── Hair (top polygon) ──
        hair_poly = [
            (cx - 88, cy - 62),
            (cx - 84, cy - 100),
            (cx - 60, cy - 118),
            (cx - 28, cy - 124),
            (cx,      cy - 127),
            (cx + 28, cy - 124),
            (cx + 60, cy - 118),
            (cx + 84, cy - 100),
            (cx + 88, cy - 62),
            (cx + 76, cy - 88),
            (cx + 48, cy - 112),
            (cx,      cy - 120),
            (cx - 48, cy - 112),
            (cx - 76, cy - 88),
        ]
        pygame.draw.polygon(screen, HAIR, hair_poly)
        # Side hair strands
        pygame.draw.ellipse(screen, HAIR, (cx - 98, cy - 68, 26, 90))
        pygame.draw.ellipse(screen, HAIR, (cx + 72,  cy - 68, 26, 90))

        # ── Eyebrows ──
        for ex in (cx - 33, cx + 33):
            pts = [(ex - 20, cy - 58), (ex, cy - 65), (ex + 20, cy - 58)]
            pygame.draw.lines(screen, HAIR, False, pts, 3)

        # ── Eyes ──
        self._draw_eye(screen, cx - 33, cy - 38, eye_open)
        self._draw_eye(screen, cx + 33, cy - 38, eye_open)

        # ── Nose ──
        pygame.draw.ellipse(screen, SKIN_SH, (cx - 6, cy + 2, 12, 9))

        # ── Cheeks ──
        screen.blit(self._cheek_surf, (cx - 82, cy + 14))  # type: ignore[arg-type]
        screen.blit(self._cheek_surf, (cx + 30,  cy + 14))  # type: ignore[arg-type]

        # ── Mouth ──
        self._draw_mouth(screen, cx, cy + 55, mouth)

        # ── Listening pulse ring around head ──
        if status == "listening":
            t = time.monotonic()
            pulse = (math.sin(t * 5) + 1) / 2  # 0→1
            alpha = int(80 + 80 * pulse)
            radius = int(95 + 8 * pulse)
            ring_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(
                ring_surf,
                (70, 210, 95, alpha),
                (0, 0, ring_surf.get_width(), ring_surf.get_height()),
                3,
            )
            screen.blit(ring_surf, (cx - radius - 2, cy - radius - 2))

    def _draw_eye(self, screen: pygame.Surface, ex: int, ey: int, eye_open: float) -> None:
        EW, EH = 36, 28

        if eye_open < 0.07:
            # Closed: single curved line
            pygame.draw.arc(
                screen, (25, 15, 10),
                (ex - EW // 2, ey - 4, EW, 12),
                0, math.pi, 3,
            )
            return

        # White of eye
        pygame.draw.ellipse(screen, EYE_WHITE, (ex - EW // 2, ey - EH // 2, EW, EH))

        # Iris (height scales with eye_open)
        IR = 13
        ih = max(3, int(IR * 2 * min(1.0, eye_open * 1.4)))
        pygame.draw.ellipse(screen, IRIS, (ex - IR, ey - ih // 2, IR * 2, ih))
        pygame.draw.ellipse(screen, IRIS_RIM, (ex - IR, ey - ih // 2, IR * 2, ih), 2)

        # Pupil
        PR = 8
        ph = max(2, int(PR * 2 * min(1.0, eye_open * 1.4)))
        pygame.draw.ellipse(screen, PUPIL, (ex - PR, ey - ph // 2, PR * 2, ph))

        # Highlights
        if eye_open > 0.25:
            ofs = int(4 * eye_open)
            pygame.draw.circle(screen, (255, 255, 255), (ex - 4, ey - ofs), 4)
            pygame.draw.circle(screen, (200, 220, 255), (ex + 5, ey + 2), 2)

        # Upper eyelash arc
        pygame.draw.arc(
            screen, (18, 12, 10),
            (ex - EW // 2 - 2, ey - EH // 2 - 3, EW + 4, EH + 2),
            0.05, math.pi - 0.05, 4,
        )

        # Lower lid line
        pygame.draw.arc(
            screen, (120, 90, 85),
            (ex - EW // 2, ey - EH // 4, EW, EH // 2),
            math.pi, 2 * math.pi, 1,
        )

    def _draw_mouth(self, screen: pygame.Surface, mx: int, my: int, state: MouthState) -> None:
        if state == MouthState.CLOSED:
            # Gentle smile curve
            pygame.draw.arc(screen, LIP_DRK, (mx - 22, my - 8, 44, 20), math.pi, 2 * math.pi, 3)
            pygame.draw.arc(screen, LIP,     (mx - 22, my - 14, 44, 18), math.pi + 0.25, 2 * math.pi - 0.25, 2)

        elif state == MouthState.SLIGHTLY_OPEN:
            pygame.draw.ellipse(screen, LIP_DRK, (mx - 18, my - 6, 36, 14))
            pygame.draw.ellipse(screen, MOUTH_DRK, (mx - 13, my - 3, 26, 7))
            pygame.draw.arc(screen, LIP, (mx - 18, my - 10, 36, 14), math.pi, 2 * math.pi, 3)

        elif state == MouthState.OPEN:
            pygame.draw.ellipse(screen, LIP_DRK, (mx - 22, my - 10, 44, 22))
            pygame.draw.ellipse(screen, MOUTH_DRK, (mx - 17, my - 6, 34, 15))
            pygame.draw.rect(screen, TEETH, (mx - 15, my - 5, 30, 7))
            pygame.draw.arc(screen, LIP, (mx - 22, my - 14, 44, 16), math.pi, 2 * math.pi, 3)

        elif state == MouthState.WIDE_OPEN:
            pygame.draw.ellipse(screen, LIP_DRK, (mx - 26, my - 13, 52, 28))
            pygame.draw.ellipse(screen, MOUTH_DRK, (mx - 21, my - 9, 42, 22))
            pygame.draw.rect(screen, TEETH, (mx - 18, my - 6, 36, 8))
            pygame.draw.rect(screen, (232, 230, 220), (mx - 15, my + 4, 30, 4))
            pygame.draw.arc(screen, LIP, (mx - 26, my - 17, 52, 18), math.pi, 2 * math.pi, 3)

    # ── Status bar ───────────────────────────────────────────────────────────

    def _draw_status_bar(
        self,
        screen: pygame.Surface,
        font_bold: pygame.font.Font,
        font_sm: pygame.font.Font,
        status: str,
    ) -> None:
        color = STATUS_COLOR.get(status, STATUS_COLOR["idle"])
        bar_y = 308

        # Separator line
        pygame.draw.line(screen, (50, 50, 80), (20, bar_y), (self.cfg.window_width - 20, bar_y), 1)

        # Pulsing dot
        if status in ("listening", "speaking"):
            t = time.monotonic()
            pulse = (math.sin(t * 6) + 1) / 2
            dot_r = int(5 + 3 * pulse)
        else:
            dot_r = 6

        pygame.draw.circle(screen, color, (28, bar_y + 18), dot_r)

        label = STATUS_LABEL.get(status, status)
        surf = font_bold.render(label, True, color)
        screen.blit(surf, (44, bar_y + 8))

        # Model hint in idle
        if status == "idle":
            hint = font_sm.render("Press Ctrl+C to quit  |  ESC to close", True, (60, 60, 90))
            screen.blit(hint, (44, bar_y + 28))

    # ── Conversation text ────────────────────────────────────────────────────

    def _draw_conversation(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        W = self.cfg.window_width
        max_w = W - 32
        y = 360

        user_text = self.state.user_text
        ai_text = self.state.ai_text

        if user_text:
            y = self._draw_bubble(screen, font, "You", user_text,
                                  (130, 210, 140), (170, 240, 175), y, max_w)
            y += 10

        if ai_text:
            self._draw_bubble(screen, font, "Galatea", ai_text,
                              (140, 140, 225), (185, 185, 248), y, max_w)

    def _draw_bubble(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        speaker: str,
        text: str,
        label_color: tuple[int, int, int],
        text_color: tuple[int, int, int],
        y: int,
        max_w: int,
    ) -> int:
        label_surf = font.render(f"{speaker}:", True, label_color)
        screen.blit(label_surf, (16, y))
        y += 20

        for line in self._wrap(text, font, max_w):
            if y > self.cfg.window_height - 18:
                break
            surf = font.render(line, True, text_color)
            screen.blit(surf, (16, y))
            y += 18

        return y

    @staticmethod
    def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        cur = ""
        for word in words:
            test = (cur + " " + word).lstrip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines
