"""
Blender Wall Generator
------------------------
Reads walls.json (produced by the floorplan wall detector script) and
generates a 3D wall mesh inside Blender, ready to export as FBX for UE5.

HOW TO RUN:
1. Open Blender
2. Go to the "Scripting" tab (top menu bar)
3. Click "New" to create a new text block, paste this whole script in
4. Edit the CONFIG section below (especially WALLS_JSON_PATH)
5. Click the "Run Script" button (play icon, or Alt+P)
6. Check the 3D Viewport - walls should appear matching your floor plan

Units note: Blender's default unit is meters, but we're feeding it
values already in Unreal Units (cm-equivalent, since 1 UU = 1 cm).
We set the scene unit scale to match so exported FBX sizes come out
correct in UE5 without needing a manual scale fix on import.
"""

import bpy
import json
import math

# ============================================================
# CONFIG - edit these
# ============================================================

WALLS_JSON_PATH = r"E:\Humcode\Test Images\walls.json"  # full path to your walls.json

WALL_HEIGHT_UU = 300.0        # wall height in Unreal Units (cm) - e.g. 300 = 3m tall wall
DEFAULT_THICKNESS_UU = 15.0   # fallback thickness if not specified per-wall in JSON

JOIN_INTO_SINGLE_MESH = True  # True = one combined mesh object, False = keep walls separate
CLEAR_EXISTING_OBJECTS = True # True = wipe the scene before generating (avoids duplicate runs piling up)

# ============================================================
# SCRIPT
# ============================================================

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def setup_unreal_scale():
    # 1 Blender Unit = 1 cm, matching Unreal's 1 UU = 1 cm, so no rescaling is needed on import.
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.01  # 1 BU = 1 cm


def load_walls(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return data


def create_wall(wall, index):
    start = wall["start"]  # [x, y] in UU
    end = wall["end"]
    thickness = wall.get("thickness", DEFAULT_THICKNESS_UU)

    x1, y1 = start[0], start[1]
    x2, y2 = end[0], end[1]

    length = math.hypot(x2 - x1, y2 - y1)
    if length < 0.001:
        print(f"Skipping degenerate wall {index} (zero length)")
        return None

    mid_x = (x1 + x2) / 2.0
    mid_y = (y1 + y2) / 2.0
    angle = math.atan2(y2 - y1, x2 - x1)

    # Create a cube primitive; default cube is 2x2x2 (radius 1), so we scale to match dimensions.
    bpy.ops.mesh.primitive_cube_add(size=1, location=(mid_x, mid_y, WALL_HEIGHT_UU / 2.0))
    wall_obj = bpy.context.active_object
    wall_obj.name = f"Wall_{index:03d}"

    # Scale: X = length along wall, Y = thickness, Z = height
    wall_obj.scale = (length, thickness, WALL_HEIGHT_UU)

    # Rotate around Z to align with the wall direction
    wall_obj.rotation_euler = (0.0, 0.0, angle)

    # Apply the scale/rotation so exported FBX has clean transforms (not baked into object properties only)
    bpy.ops.object.select_all(action='DESELECT')
    wall_obj.select_set(True)
    bpy.context.view_layer.objects.active = wall_obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    return wall_obj


def join_all_walls(wall_objects):
    if not wall_objects:
        return None

    bpy.ops.object.select_all(action='DESELECT')
    for obj in wall_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = wall_objects[0]

    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = "HallWalls_Combined"
    return joined


def main():
    print(f"Loading walls from {WALLS_JSON_PATH}...")
    walls = load_walls(WALLS_JSON_PATH)
    print(f"  -> {len(walls)} wall segments found")

    if CLEAR_EXISTING_OBJECTS:
        clear_scene()

    setup_unreal_scale()

    wall_objects = []
    for i, wall in enumerate(walls):
        obj = create_wall(wall, i)
        if obj is not None:
            wall_objects.append(obj)

    print(f"Generated {len(wall_objects)} wall meshes.")

    if JOIN_INTO_SINGLE_MESH and wall_objects:
        joined = join_all_walls(wall_objects)
        print(f"Joined into single mesh: {joined.name}")

    print("\nDone. Check the 3D Viewport.")
    print("Next: File > Export > FBX, set Forward=-Y / Up=Z, enable 'Apply Unit Scale'.")


if __name__ == "__main__":
    main()
