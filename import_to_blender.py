"""Import FURY scene geometry into Blender from scene_data.json.

Run with:
    blender --background --python import_to_blender.py

This script:
  1. Clears the default Blender scene
  2. Loads mesh data from scene_data.json
  3. Creates Blender mesh objects with materials
  4. Sets up camera and lighting
  5. Renders to screenshots/blender_render.png
  6. Saves the .blend file
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def clear_scene():
    """Remove all default objects from the Blender scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Also remove orphan data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)
    for cam in bpy.data.cameras:
        bpy.data.cameras.remove(cam)
    for light in bpy.data.lights:
        bpy.data.lights.remove(light)


def fury_to_blender_coords(pos):
    """Convert FURY/pygfx coordinates (Y-up) to Blender coordinates (Z-up).

    pygfx: X-right, Y-up, Z-toward-viewer
    Blender: X-right, Z-up, Y-into-screen

    Mapping: (x, y, z)_pygfx -> (x, z, -y)_blender
    """
    x, y, z = pos
    return (x, z, -y)


def create_mesh_object(actor_data):
    """Create a Blender mesh object from exported actor data.

    Parameters
    ----------
    actor_data : dict
        Dict with keys: name, vertices, faces, color, position, scale.

    Returns
    -------
    bpy.types.Object
        The created Blender object.
    """
    name = actor_data["name"]
    verts = actor_data["vertices"]
    faces = actor_data["faces"]
    color = actor_data["color"]
    position = actor_data.get("position", [0, 0, 0])
    scale = actor_data.get("scale", [1, 1, 1])

    # Convert vertex coordinates from pygfx (Y-up) to Blender (Z-up)
    blender_verts = [fury_to_blender_coords(v) for v in verts]

    # Create mesh data
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(blender_verts, [], faces)
    mesh.update()
    mesh.validate()

    # Create object
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # Set transform (position is already baked into vertices for FURY actors,
    # but apply the actor's local transform if non-zero)
    bpos = fury_to_blender_coords(position)
    obj.location = bpos
    obj.scale = (scale[0], scale[2], scale[1])  # swap Y/Z for scale too

    # Apply per-vertex colors if available
    vcols = actor_data.get("vertex_colors")
    has_vcols = vcols is not None and len(vcols) == len(verts)

    if has_vcols:
        color_attr = mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="POINT")
        for i, vc in enumerate(vcols):
            r, g, b = vc[0], vc[1], vc[2]
            a = vc[3] if len(vc) > 3 else 1.0
            color_attr.data[i].color = (r, g, b, a)

    # Create material
    mat = bpy.data.materials.new(name + "_material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]

    if has_vcols:
        # Wire vertex colors into the Principled BSDF base color
        vcol_node = nodes.new(type="ShaderNodeVertexColor")
        vcol_node.layer_name = "Color"
        links.new(vcol_node.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        r, g, b = color[0], color[1], color[2]
        a = color[3] if len(color) > 3 else 1.0
        bsdf.inputs["Base Color"].default_value = (r, g, b, a)

    bsdf.inputs["Roughness"].default_value = 0.4
    bsdf.inputs["Metallic"].default_value = 0.05

    obj.data.materials.append(mat)

    # Enable smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

    return obj


def setup_camera(camera_data):
    """Create and configure the camera from exported camera data."""
    cam_pos = fury_to_blender_coords(camera_data["position"])
    cam_target = fury_to_blender_coords(camera_data["target"])
    fov = camera_data.get("fov", 50)

    # Create camera
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(fov)
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0

    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = cam_pos

    # Point camera at target using Track To constraint
    target_empty = bpy.data.objects.new("CameraTarget", None)
    target_empty.location = cam_target
    target_empty.empty_display_size = 0.1
    bpy.context.collection.objects.link(target_empty)

    constraint = cam_obj.constraints.new(type="TRACK_TO")
    constraint.target = target_empty
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    # Set as active camera
    bpy.context.scene.camera = cam_obj

    return cam_obj


def setup_lighting():
    """Add a sun light and a fill light to the scene."""
    # Key light — sun
    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.98, 0.95)
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    sun_obj.location = (5, 5, 8)
    sun_obj.rotation_euler = (math.radians(40), math.radians(15), math.radians(-30))
    bpy.context.collection.objects.link(sun_obj)

    # Fill light — area
    area_data = bpy.data.lights.new("FillLight", type="AREA")
    area_data.energy = 50.0
    area_data.size = 4.0
    area_data.color = (0.85, 0.9, 1.0)
    area_obj = bpy.data.objects.new("FillLight", area_data)
    area_obj.location = (-4, -3, 5)
    bpy.context.collection.objects.link(area_obj)

    # Rim light — point
    rim_data = bpy.data.lights.new("RimLight", type="POINT")
    rim_data.energy = 100.0
    rim_data.color = (1.0, 0.95, 0.9)
    rim_obj = bpy.data.objects.new("RimLight", rim_data)
    rim_obj.location = (0, 6, 3)
    bpy.context.collection.objects.link(rim_obj)

    # World background — subtle dark gray
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.05, 0.05, 0.07, 1.0)
        bg_node.inputs["Strength"].default_value = 1.0


def configure_render():
    """Configure render settings for a quality output."""
    scene = bpy.context.scene

    # Try EEVEE first (fast), fall back to Cycles
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except TypeError:
            scene.render.engine = "CYCLES"

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"

    # If Cycles, set reasonable samples
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True


def main():
    # Accept optional JSON filename via: blender --background --python import_to_blender.py -- myfile.json
    json_file = "scene_data.json"
    if "--" in sys.argv:
        args_after = sys.argv[sys.argv.index("--") + 1:]
        if args_after:
            json_file = args_after[0]

    json_path = os.path.join(SCRIPT_DIR, "scene_data", json_file)
    print(f"Loading {json_path}...")

    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found. Run create_fury_scene.py first.")
        sys.exit(1)

    with open(json_path) as f:
        scene_data = json.load(f)

    # Clear scene
    print("Clearing default Blender scene...")
    clear_scene()

    # Create mesh objects
    actors = scene_data.get("actors", [])
    created = 0
    for actor_data in actors:
        try:
            obj = create_mesh_object(actor_data)
            vcount = len(actor_data["vertices"])
            fcount = len(actor_data["faces"])
            print(f"  Created {obj.name}: {vcount} verts, {fcount} faces")
            created += 1
        except Exception as e:
            print(f"  Warning: failed to create {actor_data.get('name', '?')}: {e}")

    print(f"Created {created} mesh objects")

    # Camera
    camera_data = scene_data.get("camera", {})
    if camera_data:
        setup_camera(camera_data)
        print(f"  Camera at {camera_data['position']}, fov={camera_data.get('fov', 50)}")
    else:
        print("  Warning: no camera data found, using default")

    # Lighting
    setup_lighting()
    print("  Added Sun + FillLight + RimLight")

    # Render settings
    configure_render()

    # Derive short prefix from JSON name (e.g. molecular_scene_data.json -> molecular)
    base = os.path.splitext(json_file)[0]
    prefix = base.replace("_scene_data", "").replace("scene_data", "primitives")
    if not prefix:
        prefix = "primitives"

    # Render
    render_path = os.path.join(SCRIPT_DIR, "screenshots", f"{prefix}_blender.png")
    bpy.context.scene.render.filepath = render_path
    print(f"Rendering to {render_path}...")
    bpy.ops.render.render(write_still=True)
    print(f"  Saved {render_path}")

    # Save .blend file
    blend_dir = os.path.join(SCRIPT_DIR, "converted-blend-files")
    os.makedirs(blend_dir, exist_ok=True)
    blend_path = os.path.join(blend_dir, f"{prefix}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"  Saved {blend_path}")

    print("Done!")


if __name__ == "__main__":
    main()
