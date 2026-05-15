"""
Convert Mixamo FBX exports to GLB files for Galatea.

Usage (from the galatea project root):
    blender --background --python scripts/blender_convert.py -- <idle.fbx> <talk.fbx> [think.fbx …]

The first FBX must be the one downloaded WITH SKIN (character mesh + idle animation).
Subsequent FBXes should be downloaded WITHOUT SKIN (animation only).

Output files land in assets/character/:
    idle.fbx  →  assets/character/idle.glb
    talk.fbx  →  assets/character/talk.glb
    …

Animation clips inside each GLB are renamed to match the filename
(idle, talk, think, …) so Galatea's loader finds them automatically.
"""

import bpy
import os
import sys


ANIM_NAMES = ["idle", "talk", "think", "listen"]
OUTPUT_DIR = "assets/character"


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_fbx(path: str) -> None:
    bpy.ops.import_scene.fbx(filepath=os.path.abspath(path))


def rename_actions(name: str) -> None:
    """Rename all actions in the blend file to the given name."""
    for action in bpy.data.actions:
        action.name = name


def export_glb(out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.abspath(out_path),
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_morph=True,
    )


def main() -> None:
    argv = sys.argv
    if "--" not in argv:
        print(__doc__)
        sys.exit(1)

    fbx_files = argv[argv.index("--") + 1:]
    if not fbx_files:
        print("Error: no FBX files given after '--'.")
        print(__doc__)
        sys.exit(1)

    print(f"\n{'─' * 50}")
    print(f"Galatea FBX → GLB converter")
    print(f"Input files : {fbx_files}")
    print(f"Output dir  : {OUTPUT_DIR}/")
    print(f"{'─' * 50}\n")

    for i, fbx_path in enumerate(fbx_files):
        anim_name = ANIM_NAMES[i] if i < len(ANIM_NAMES) else f"anim_{i}"
        out_name  = f"{anim_name}.glb"
        out_path  = os.path.join(OUTPUT_DIR, out_name)

        print(f"[{i+1}/{len(fbx_files)}] {fbx_path} → {out_path}  (anim: '{anim_name}')")

        clear_scene()
        import_fbx(fbx_path)
        rename_actions(anim_name)
        export_glb(out_path)

        print(f"      ✓ Written: {out_path}")

    print(f"\nDone! {len(fbx_files)} file(s) converted.")
    print(f"Now run:  uv run galatea")


main()
