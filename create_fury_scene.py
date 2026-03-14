"""Create a FURY scene with multiple actors and export geometry to JSON.

This script builds a scene with various primitive actors (spheres, cones,
cylinders, boxes, arrows, disks), captures a screenshot, then extracts
all mesh geometry and camera data into scene_data.json for import into Blender.
"""

import json
import os
import sys

import numpy as np

# Allow running from the fury repo checkout if fury isn't installed system-wide
FURY_REPO = os.path.expanduser("~/Documents/OSS/fury")
if os.path.isdir(FURY_REPO) and FURY_REPO not in sys.path:
    sys.path.insert(0, FURY_REPO)

import fury

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_scene():
    """Build a FURY scene with a variety of actors in a tight, visually rich layout."""
    scene = fury.window.Scene(background=(0.08, 0.08, 0.12, 1.0))
    actors = []

    # --- Spheres (real mesh, impostor=False for exportable geometry) ---
    # Arranged in a front row, large and prominent
    sphere_configs = [
        {"center": [-3.5, -0.5, 0], "color": [0.95, 0.2, 0.2], "radius": 1.5},
        {"center": [0, 2.5, -1], "color": [0.2, 0.85, 0.3], "radius": 1.2},
        {"center": [3.5, -0.5, 0.5], "color": [0.25, 0.5, 1.0], "radius": 1.4},
    ]
    for i, cfg in enumerate(sphere_configs):
        try:
            a = fury.actor.sphere(
                centers=np.array([cfg["center"]], dtype=np.float32),
                colors=np.array([cfg["color"]], dtype=np.float32),
                radii=cfg["radius"],
                impostor=False,
            )
            a.name = f"sphere_{i}"
            actors.append(a)
            scene.add(a)
        except Exception as e:
            print(f"  Warning: could not create sphere_{i}: {e}")

    print(f"  Added {sum(1 for a in actors if 'sphere' in (a.name or ''))} spheres")

    # --- Cones --- tall and visible
    cone_configs = [
        {"center": [-1.8, -2.5, 1.5], "color": [1.0, 0.85, 0.1], "direction": [0, 1, 0]},
        {"center": [2.0, -2.5, -1.5], "color": [0.1, 0.9, 0.9], "direction": [0, 1, 0]},
    ]
    cone_count = 0
    for i, cfg in enumerate(cone_configs):
        try:
            a = fury.actor.cone(
                centers=np.array([cfg["center"]], dtype=np.float32),
                colors=np.array([cfg["color"]], dtype=np.float32),
                directions=np.array([cfg["direction"]], dtype=np.float32),
                height=2.5,
                radii=1.0,
            )
            a.name = f"cone_{i}"
            actors.append(a)
            scene.add(a)
            cone_count += 1
        except Exception as e:
            print(f"  Warning: could not create cone_{i}: {e}")

    print(f"  Added {cone_count} cones")

    # --- Cylinder --- thick and prominent
    try:
        a = fury.actor.cylinder(
            centers=np.array([[0, -1.0, 2.5]], dtype=np.float32),
            colors=np.array([[0.85, 0.2, 0.85]], dtype=np.float32),
            directions=np.array([[0, 1, 0]], dtype=np.float32),
            height=3.0,
            radii=0.8,
        )
        a.name = "cylinder_0"
        actors.append(a)
        scene.add(a)
        print("  Added 1 cylinder")
    except Exception as e:
        print(f"  Warning: could not create cylinder: {e}")

    # --- Box --- large
    try:
        a = fury.actor.box(
            centers=np.array([[3.0, 2.5, -2.0]], dtype=np.float32),
            colors=np.array([[1.0, 0.55, 0.1]], dtype=np.float32),
            scales=(2.0, 1.5, 1.5),
        )
        a.name = "box_0"
        actors.append(a)
        scene.add(a)
        print("  Added 1 box")
    except Exception as e:
        print(f"  Warning: could not create box: {e}")

    # --- Arrow --- large and visible
    try:
        a = fury.actor.arrow(
            centers=np.array([[-3.0, 2.5, -1.5]], dtype=np.float32),
            colors=np.array([[0.3, 1.0, 0.5]], dtype=np.float32),
            directions=np.array([[1, 1, 0]], dtype=np.float32),
            height=3.5,
            tip_radius=0.25,
            shaft_radius=0.08,
        )
        a.name = "arrow_0"
        actors.append(a)
        scene.add(a)
        print("  Added 1 arrow")
    except Exception as e:
        print(f"  Warning: could not create arrow: {e}")

    # --- Disk --- larger
    try:
        a = fury.actor.disk(
            centers=np.array([[0, 0, -3.5]], dtype=np.float32),
            colors=np.array([[0.9, 0.85, 0.15]], dtype=np.float32),
            radii=1.5,
        )
        a.name = "disk_0"
        actors.append(a)
        scene.add(a)
        print("  Added 1 disk")
    except Exception as e:
        print(f"  Warning: could not create disk: {e}")

    return scene, actors


def extract_actor_data(actor):
    """Extract geometry and material data from a single FURY actor.

    Returns a dict with vertices, faces, color, position, and scale,
    or None if the actor has no usable mesh geometry.
    """
    geom = getattr(actor, "geometry", None)
    if geom is None:
        return None

    # Positions
    positions_buf = getattr(geom, "positions", None)
    if positions_buf is None:
        return None
    positions = positions_buf.data
    if positions is None or len(positions) == 0:
        return None

    # Indices
    indices_buf = getattr(geom, "indices", None)
    if indices_buf is not None and indices_buf.data is not None:
        indices = indices_buf.data
        # Indices could be flat (Nx1) for billboards or Nx3 for triangles
        if indices.ndim == 1:
            # Reshape flat indices into triangles if possible
            if len(indices) % 3 == 0:
                indices = indices.reshape(-1, 3)
            else:
                return None
    else:
        return None

    # Ensure we have proper triangle faces
    if indices.ndim != 2 or indices.shape[1] != 3:
        return None

    # Color — try per-vertex colors first, then material color
    color = [0.8, 0.8, 0.8, 1.0]
    try:
        colors_buf = geom.colors
        if colors_buf is not None and colors_buf.data is not None:
            c = colors_buf.data
            # Average per-vertex colors to get a single representative color
            avg = c.mean(axis=0).tolist()
            if len(avg) == 3:
                avg.append(1.0)
            color = avg
    except (AttributeError, KeyError):
        pass

    if color == [0.8, 0.8, 0.8, 1.0]:
        # Fallback to material color
        try:
            mat_color = actor.material.color
            color = [float(mat_color.r), float(mat_color.g), float(mat_color.b), 1.0]
        except (AttributeError, KeyError):
            pass

    # Transform
    try:
        pos = list(float(v) for v in actor.local.position)
    except Exception:
        pos = [0.0, 0.0, 0.0]

    try:
        scale = list(float(v) for v in actor.local.scale)
    except Exception:
        scale = [1.0, 1.0, 1.0]

    name = getattr(actor, "name", None) or type(actor).__name__

    return {
        "name": name,
        "type": "mesh",
        "vertices": positions.tolist(),
        "faces": indices.tolist(),
        "color": [round(c, 4) for c in color],
        "position": [round(p, 4) for p in pos],
        "scale": [round(s, 4) for s in scale],
    }


def extract_camera_data(show_manager):
    """Extract camera position, target, and field of view."""
    cam = show_manager.screens[0].camera
    pos = [float(v) for v in cam.world.position]
    fov = float(cam.fov)

    # Estimate the look-at target: camera looks along its forward direction.
    # After auto-fitting, the target is roughly the scene center.
    try:
        forward = np.array(cam.world.forward, dtype=np.float64)
        # The target is approximately at the scene center (origin area)
        # Use the bounding info or just assume target ~ centroid of scene
        target = [0.0, 0.0, 0.0]
    except Exception:
        target = [0.0, 0.0, 0.0]

    return {
        "position": [round(v, 4) for v in pos],
        "target": [round(v, 4) for v in target],
        "fov": round(fov, 2),
    }


def main():
    print("Creating FURY scene...")
    scene, actors = create_scene()

    # Render and capture screenshot
    print("Rendering screenshot...")
    screenshot_path = os.path.join(SCRIPT_DIR, "screenshots", "fury_render.png")

    show_m = fury.window.ShowManager(
        scene=scene, window_type="offscreen", size=(1920, 1080)
    )

    # Set a nice angled camera view (slightly elevated, looking at center)
    cam = show_m.screens[0].camera
    cam.world.position = (5, 8, 18)
    cam.look_at((0, 0, 0))
    cam.fov = 45

    show_m.render()
    show_m.window.draw()
    show_m.snapshot(screenshot_path)
    print(f"  Saved {screenshot_path}")

    # Extract geometry from all actors
    print("Extracting geometry...")
    actor_data_list = []
    for actor in actors:
        data = extract_actor_data(actor)
        if data is not None:
            actor_data_list.append(data)
            verts = len(data["vertices"])
            faces = len(data["faces"])
            print(f"  {data['name']}: {verts} vertices, {faces} faces")
        else:
            name = getattr(actor, "name", type(actor).__name__)
            print(f"  {name}: skipped (no exportable mesh geometry)")

    # Extract camera
    camera_data = extract_camera_data(show_m)
    print(f"  Camera at {camera_data['position']}, fov={camera_data['fov']}")

    # Save to JSON
    scene_export = {
        "actors": actor_data_list,
        "camera": camera_data,
    }

    json_path = os.path.join(SCRIPT_DIR, "scene_data.json")
    with open(json_path, "w") as f:
        json.dump(scene_export, f, indent=2)

    print(f"Saved scene_data.json with {len(actor_data_list)} actors")
    print("Done!")


if __name__ == "__main__":
    main()
