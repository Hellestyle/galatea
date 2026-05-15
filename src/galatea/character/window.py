"""3D character window — Panda3D with GLB model + skeletal animations."""

from __future__ import annotations

import os
import sys

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    LColor,
    TextNode,
    loadPrcFileData,
)
from direct.actor.Actor import Actor
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from ..config import CharacterConfig
from ..state import AppState

# ── Paths ─────────────────────────────────────────────────────────────────────
_MODEL     = "assets/character/galatea.glb"   # main model (optional, falls back to idle.glb)
_IDLE_GLB  = "assets/character/idle.glb"      # idle animation (also used as model if no galatea.glb)
_TALK_GLB  = "assets/character/talk.glb"      # talk animation

# ── UI colours per pipeline state ─────────────────────────────────────────────
_STATUS_COLOR: dict[str, tuple[float, float, float, float]] = {
    "idle":       (0.55, 0.55, 0.72, 1),
    "listening":  (0.28, 0.90, 0.45, 1),
    "processing": (0.95, 0.78, 0.20, 1),
    "thinking":   (0.80, 0.55, 0.95, 1),
    "speaking":   (0.28, 0.65, 0.98, 1),
    "error":      (0.92, 0.28, 0.28, 1),
}
_STATUS_LABEL: dict[str, str] = {
    "idle":       "Idle",
    "listening":  "Listening…",
    "processing": "Transcribing…",
    "thinking":   "Thinking…",
    "speaking":   "Speaking",
    "error":      "Error",
}


class CharacterWindow:
    """Entry point — sets Panda3D config then hands off to ShowBase subclass."""

    def __init__(self, config: CharacterConfig, state: AppState) -> None:
        self.config = config
        self.state = state

    def run(self) -> None:
        # These MUST be set before ShowBase.__init__
        loadPrcFileData("", f"win-size {self.config.window_width} {self.config.window_height}")
        loadPrcFileData("", "win-title Galatea")
        loadPrcFileData("", "sync-video 1")          # vsync — prevents GPU from running flat out
        loadPrcFileData("", "clock-mode limited")
        loadPrcFileData("", "clock-frame-rate 30")   # cap render loop to 30 fps
        loadPrcFileData("", "framebuffer-multisample 1")
        loadPrcFileData("", "multisamples 2")        # 2× MSAA (was 4×)

        app = _GalateaApp(self.config, self.state)
        app.run()


class _GalateaApp(ShowBase):
    def __init__(self, config: CharacterConfig, state: AppState) -> None:
        ShowBase.__init__(self)

        self._state = state
        self._config = config
        self._actor: Actor | None = None
        self._current_anim: str = config.anim_idle
        self._can_talk: bool = False

        self.setBackgroundColor(0.06, 0.06, 0.16, 1)
        self.disableMouse()

        self._setup_lighting()
        self._load_character()
        self._setup_camera()
        self._setup_ui()

        self.taskMgr.add(self._update, "update")
        self.accept("escape", self._quit)

    # ── Lighting ──────────────────────────────────────────────────────────────

    def _setup_lighting(self) -> None:
        # PBR rendering makes GLB materials look correct (metallic/roughness)
        try:
            import simplepbr
            simplepbr.init(
                max_lights=3,
                enable_shadows=False,   # shadows are expensive
                use_occlusion_maps=False,
                msaa_samples=2,
            )
        except Exception as exc:
            print(f"[window] simplepbr unavailable ({exc}), using auto-shader fallback")
            self.render.setShaderAuto()

        ambient = AmbientLight("ambient")
        ambient.setColor(LColor(0.20, 0.20, 0.26, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        # Warm key light — front-right, slightly above
        key = DirectionalLight("key")
        key.setColor(LColor(1.0, 0.93, 0.84, 1))
        knp = self.render.attachNewNode(key)
        knp.setHpr(38, -42, 0)
        self.render.setLight(knp)

        # Cool fill — front-left
        fill = DirectionalLight("fill")
        fill.setColor(LColor(0.28, 0.36, 0.62, 1))
        fnp = self.render.attachNewNode(fill)
        fnp.setHpr(-55, -10, 0)
        self.render.setLight(fnp)

        # Rim — behind the character, separates it from the dark background
        rim = DirectionalLight("rim")
        rim.setColor(LColor(0.30, 0.38, 0.60, 1))
        rnp = self.render.attachNewNode(rim)
        rnp.setHpr(168, 22, 0)
        self.render.setLight(rnp)

    # ── Character model ───────────────────────────────────────────────────────

    def _load_character(self) -> None:
        has_model = os.path.exists(_MODEL)
        has_idle  = os.path.exists(_IDLE_GLB)
        has_talk  = os.path.exists(_TALK_GLB)

        if not has_model and not has_idle:
            print(
                "\n[window] No 3D character found.\n"
                "         See assets/character/SETUP.md to add one.\n"
                "         Showing placeholder sphere.\n"
            )
            self._load_placeholder()
            return

        # Use galatea.glb as the mesh source if present, else idle.glb doubles as model
        mesh_file = _MODEL if has_model else _IDLE_GLB

        # Build animation dictionary for Actor
        # Keys are the names WE use in code; values are file paths.
        # If mesh_file is idle.glb it already carries the idle animation.
        anim_dict: dict[str, str] = {}
        if has_idle and mesh_file != _IDLE_GLB:
            anim_dict[self._config.anim_idle] = _IDLE_GLB
        if has_talk:
            anim_dict[self._config.anim_talk] = _TALK_GLB

        try:
            self._actor = Actor(mesh_file, anim_dict or None)
            self._actor.reparentTo(self.render)

            # Discover what animation clips are available
            try:
                names = self._actor.getAnimNames()
                if names:
                    print(f"[window] Animations available: {names}")
                # Check if our desired animation names are present
                idle_ok = self._config.anim_idle in names
                self._can_talk = self._config.anim_talk in names

                # Play idle — fall back to first available clip if needed
                start_anim = self._config.anim_idle if idle_ok else (names[0] if names else None)
                if start_anim:
                    self._actor.loop(start_anim)
                    self._current_anim = start_anim
            except Exception as exc:
                print(f"[window] Animation discovery error (non-fatal): {exc}")
                self._can_talk = has_talk

            print(f"[window] Model loaded. Talk anim: {'yes' if self._can_talk else 'no'}")

        except Exception as exc:
            print(f"[window] Failed to load model: {exc}")
            self._load_placeholder()

    def _load_placeholder(self) -> None:
        sphere = self.loader.loadModel("models/misc/sphere")
        sphere.reparentTo(self.render)
        sphere.setScale(0.55)
        sphere.setPos(0, 5, 1.6)
        sphere.setColor(LColor(0.90, 0.76, 0.66, 1))

    # ── Camera ────────────────────────────────────────────────────────────────

    def _setup_camera(self) -> None:
        if self._actor is not None:
            b = self._actor.getBounds()
            cx, cy, cz = b.getCenter()
            r = b.getRadius()
            # Shift focus upward for a portrait/face-forward composition
            focus_z = cz + r * self._config.camera_height_offset
            dist    = r * self._config.camera_distance_factor
            self.cam.setPos(cx, cy - dist, focus_z)
            self.cam.lookAt(cx, cy, focus_z)
        else:
            self.cam.setPos(0, -3, 1.6)
            self.cam.lookAt(0, 5, 1.6)

        self.camLens.setFov(self._config.camera_fov)

    # ── 2D UI overlay ─────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        ar = self._config.window_width / self._config.window_height  # aspect ratio

        # Dark gradient panel at the bottom so text is always readable
        DirectFrame(
            frameColor=(0, 0, 0, 0.58),
            frameSize=(-ar, ar, -1.02, -0.52),
            parent=self.aspect2d,
        )

        # Status pill — centred at the top of the panel
        self._status_txt = OnscreenText(
            text="Idle",
            pos=(0, -0.58),
            scale=0.070,
            fg=(0.70, 0.70, 1.0, 1),
            shadow=(0, 0, 0, 0.9),
            shadowOffset=(0.003, 0.003),
            align=TextNode.ACenter,
            parent=self.aspect2d,
        )

        # User speech
        self._user_txt = OnscreenText(
            text="",
            pos=(-ar + 0.07, -0.70),
            scale=0.047,
            fg=(0.52, 0.92, 0.58, 1),
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.002, 0.002),
            align=TextNode.ALeft,
            wordwrap=int(ar * 22),
            parent=self.aspect2d,
        )

        # AI response
        self._ai_txt = OnscreenText(
            text="",
            pos=(-ar + 0.07, -0.83),
            scale=0.047,
            fg=(0.65, 0.65, 1.0, 1),
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.002, 0.002),
            align=TextNode.ALeft,
            wordwrap=int(ar * 22),
            parent=self.aspect2d,
        )

    # ── Per-frame update ──────────────────────────────────────────────────────

    def _update(self, task: Task) -> int:
        if not self._state.running:
            self._quit()
            return Task.done

        status = self._state.status

        # Switch animation based on pipeline state
        if self._actor is not None:
            want = (
                self._config.anim_talk
                if status == "speaking" and self._can_talk
                else self._config.anim_idle
            )
            if want != self._current_anim:
                try:
                    self._actor.loop(want)
                    self._current_anim = want
                except Exception:
                    pass

        # Update status text and colour
        self._status_txt.setText(_STATUS_LABEL.get(status, status.upper()))
        self._status_txt.setFg(_STATUS_COLOR.get(status, _STATUS_COLOR["idle"]))

        # Update conversation text
        u = self._state.user_text
        a = self._state.ai_text
        self._user_txt.setText(
            (f"You: {u[:95]}{'…' if len(u) > 95 else ''}") if u else ""
        )
        self._ai_txt.setText(
            (f"Galatea: {a[:115]}{'…' if len(a) > 115 else ''}") if a else ""
        )

        return Task.cont

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def userExit(self) -> None:
        """Called by Panda3D when the user clicks the window close button."""
        self._quit()

    def _quit(self) -> None:
        self._state.running = False
        sys.exit(0)
