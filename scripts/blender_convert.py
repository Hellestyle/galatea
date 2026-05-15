"""
Convert Mixamo FBX exports to GLB files for Galatea.

Usage (from the galatea project root):
    blender --background --python scripts/blender_convert.py -- <idle.fbx> <talk.fbx> [...]

The first FBX must be the one downloaded WITH SKIN (character mesh + idle animation).
Subsequent FBXes should be downloaded WITHOUT SKIN (animation only).

Output: assets/character/idle.glb, assets/character/talk.glb, …
"""

import bpy
import json
import os
import struct
import sys

ANIM_NAMES = ["idle", "talk", "think", "listen"]
OUTPUT_DIR = "assets/character"


# ── Blender helpers ───────────────────────────────────────────────────────────

def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_fbx(path: str) -> None:
    bpy.ops.import_scene.fbx(filepath=os.path.abspath(path))


def rename_actions(name: str) -> None:
    for action in bpy.data.actions:
        action.name = name


def export_glb_raw(out_path: str) -> None:
    """Export to GLB with JPEG textures (no material changes)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.abspath(out_path),
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_morph=True,
        export_image_format="JPEG",
        export_jpeg_quality=85,
    )


# ── Post-process: strip KHR_materials_specular ───────────────────────────────
# panda3d-gltf does not implement this extension and may fall back to unlit
# rendering when it is present.  Removing it causes renderers to use the
# standard pbrMetallicRoughness pipeline, which panda3d-gltf handles correctly.

def _read_glb(path: str) -> tuple[dict, bytes]:
    """Return (json_chunk_dict, binary_chunk_bytes) from a GLB file."""
    with open(path, "rb") as f:
        magic, _version, _total = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", "Not a GLB file"

        json_len, json_type = struct.unpack("<II", f.read(8))
        assert json_type == 0x4E4F534A, "First chunk must be JSON"
        json_data = json.loads(f.read(json_len))

        bin_data = b""
        header = f.read(8)
        if len(header) == 8:
            bin_len, bin_type = struct.unpack("<II", header)
            if bin_type == 0x004E4942:
                bin_data = f.read(bin_len)

    return json_data, bin_data


def _write_glb(path: str, gltf: dict, bin_data: bytes) -> None:
    """Write (json_chunk_dict, binary_chunk_bytes) back to a GLB file."""
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    # Pad to 4-byte alignment
    if len(json_bytes) % 4:
        json_bytes += b" " * (4 - len(json_bytes) % 4)

    chunks = bytearray()
    chunks += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    if bin_data:
        if len(bin_data) % 4:
            bin_data += b"\x00" * (4 - len(bin_data) % 4)
        chunks += struct.pack("<II", len(bin_data), 0x004E4942) + bin_data

    total = 12 + len(chunks)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(chunks)


def strip_specular_extension(path: str) -> None:
    """Remove KHR_materials_specular from every material in the GLB.

    This forces panda3d-gltf to use the standard pbrMetallicRoughness
    pipeline, which correctly maps baseColorTexture and normalTexture.
    """
    gltf, bin_data = _read_glb(path)

    changed = False

    # Remove from extensionsUsed / extensionsRequired
    for key in ("extensionsUsed", "extensionsRequired"):
        if "KHR_materials_specular" in gltf.get(key, []):
            gltf[key] = [e for e in gltf[key] if e != "KHR_materials_specular"]
            if not gltf[key]:
                del gltf[key]
            changed = True

    # Remove from each material
    for mat in gltf.get("materials", []):
        if "KHR_materials_specular" in mat.get("extensions", {}):
            del mat["extensions"]["KHR_materials_specular"]
            if not mat.get("extensions"):
                del mat["extensions"]
            changed = True

    if changed:
        _write_glb(path, gltf, bin_data)
        print("      (stripped KHR_materials_specular)")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    argv = sys.argv
    if "--" not in argv:
        print(__doc__)
        sys.exit(1)

    fbx_files = argv[argv.index("--") + 1:]
    if not fbx_files:
        print("Error: no FBX files provided after '--'.")
        sys.exit(1)

    print(f"\n{'─'*54}")
    print("Galatea FBX → GLB converter  (JPEG textures + clean PBR)")
    print(f"Input : {fbx_files}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"{'─'*54}\n")

    for i, fbx_path in enumerate(fbx_files):
        anim_name = ANIM_NAMES[i] if i < len(ANIM_NAMES) else f"anim_{i}"
        out_path  = os.path.join(OUTPUT_DIR, f"{anim_name}.glb")

        print(f"[{i+1}/{len(fbx_files)}] {os.path.basename(fbx_path)}  →  {out_path}")

        clear_scene()
        import_fbx(fbx_path)
        rename_actions(anim_name)
        export_glb_raw(out_path)
        strip_specular_extension(out_path)   # post-process: clean GLTF extension

        size_mb = os.path.getsize(out_path) / 1_048_576
        print(f"      ✓  {out_path}  ({size_mb:.1f} MB)\n")

    print(f"Done!  {len(fbx_files)} file(s) converted.")
    print("Now run:  uv run galatea")


main()
