"""Create a DNA double helix scene in FURY and export to JSON.

Demonstrates a scientific visualization of a DNA-like double helix
structure with two intertwined strands of spheres connected by
streamtube backbones and horizontal rungs (base pairs).
"""

import json
import os
import sys

import numpy as np

import fury

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Color palette
STRAND_A_COLOR = [0.2, 0.5, 1.0]   # Blue strand
STRAND_B_COLOR = [1.0, 0.3, 0.2]   # Red strand
RUNG_COLOR = [0.9, 0.85, 0.3]      # Yellow rungs (base pairs)
BACKBONE_A_COLOR = [0.15, 0.35, 0.7]
BACKBONE_B_COLOR = [0.7, 0.2, 0.15]


def generate_helix_points(n_turns=4, points_per_turn=12, radius=2.0, pitch=3.0):
    """Generate two intertwined helical paths (DNA double helix).

    Parameters
    ----------
    n_turns : int
        Number of full helical turns.
    points_per_turn : int
        Number of atom positions per turn.
    radius : float
        Helix radius.
    pitch : float
        Vertical rise per full turn.

    Returns
    -------
    strand_a, strand_b : ndarray
        Nx3 arrays of atom positions for each strand.
    """
    n_points = n_turns * points_per_turn
    t = np.linspace(0, n_turns * 2 * np.pi, n_points)
    y = np.linspace(0, n_turns * pitch, n_points)

    # Strand A
    ax = radius * np.cos(t)
    az = radius * np.sin(t)
    strand_a = np.column_stack([ax, y, az]).astype(np.float32)

    # Strand B — offset by pi (180 degrees)
    bx = radius * np.cos(t + np.pi)
    bz = radius * np.sin(t + np.pi)
    strand_b = np.column_stack([bx, y, bz]).astype(np.float32)

    return strand_a, strand_b


def create_scene():
    """Build a DNA double helix visualization scene."""
    scene = fury.window.Scene(background=(0.03, 0.03, 0.06, 1.0))
    actors = []

    strand_a, strand_b = generate_helix_points(
        n_turns=5, points_per_turn=10, radius=2.0, pitch=3.5
    )
    n_atoms = len(strand_a)

    # --- Strand A atoms (blue spheres) ---
    colors_a = np.tile(STRAND_A_COLOR, (n_atoms, 1)).astype(np.float32)
    # impostor=False creates real mesh geometry instead of
    # billboard SDFs, which is needed for geometry extraction
    atoms_a = fury.actor.sphere(
        centers=strand_a, colors=colors_a, radii=0.35, impostor=False,
    )
    atoms_a.name = "strand_a_atoms"
    actors.append(atoms_a)
    scene.add(atoms_a)

    # --- Strand B atoms (red spheres) ---
    colors_b = np.tile(STRAND_B_COLOR, (n_atoms, 1)).astype(np.float32)
    atoms_b = fury.actor.sphere(
        centers=strand_b, colors=colors_b, radii=0.35, impostor=False,
    )
    atoms_b.name = "strand_b_atoms"
    actors.append(atoms_b)
    scene.add(atoms_b)

    print(f"  Added {n_atoms * 2} helix atoms ({n_atoms} per strand)")

    # --- Backbone tubes (streamtubes along helix path) ---
    # Use a denser path for smoother tubes
    strand_a_dense, strand_b_dense = generate_helix_points(
        n_turns=5, points_per_turn=40, radius=2.0, pitch=3.5
    )

    backbone_a = fury.actor.streamtube(
        [strand_a_dense], colors=BACKBONE_A_COLOR, radius=0.08,
    )
    backbone_a.name = "backbone_a"
    actors.append(backbone_a)
    scene.add(backbone_a)

    backbone_b = fury.actor.streamtube(
        [strand_b_dense], colors=BACKBONE_B_COLOR, radius=0.08,
    )
    backbone_b.name = "backbone_b"
    actors.append(backbone_b)
    scene.add(backbone_b)

    print("  Added 2 backbone tubes")

    # --- Base pair rungs (cylinders connecting strand A to strand B) ---
    # Connect every 2nd atom pair as a rung
    rung_centers = []
    rung_directions = []
    rung_colors = []
    rung_count = 0

    for i in range(0, n_atoms, 2):
        p1 = strand_a[i]
        p2 = strand_b[i]
        mid = (p1 + p2) / 2.0
        diff = p2 - p1
        length = float(np.linalg.norm(diff))
        direction = diff / length if length > 1e-6 else np.array([1, 0, 0])

        rung_centers.append(mid)
        rung_directions.append(direction)
        rung_colors.append(RUNG_COLOR)
        rung_count += 1

    rungs = fury.actor.cylinder(
        centers=np.array(rung_centers, dtype=np.float32),
        directions=np.array(rung_directions, dtype=np.float32),
        colors=np.array(rung_colors, dtype=np.float32),
        height=3.8,  # slightly less than diameter to fit between strands
        radii=0.06,
    )
    rungs.name = "base_pair_rungs"
    actors.append(rungs)
    scene.add(rungs)

    print(f"  Added {rung_count} base pair rungs")

    return scene, actors


def extract_actor_data(actor):
    """Extract geometry and material data from a single FURY actor."""
    geom = getattr(actor, "geometry", None)
    if geom is None:
        return None

    positions_buf = getattr(geom, "positions", None)
    if positions_buf is None:
        return None
    positions = positions_buf.data
    if positions is None or len(positions) == 0:
        return None

    indices_buf = getattr(geom, "indices", None)
    if indices_buf is not None and indices_buf.data is not None:
        indices = indices_buf.data
        if indices.ndim == 1:
            if len(indices) % 3 == 0:
                indices = indices.reshape(-1, 3)
            else:
                return None
    else:
        return None

    if indices.ndim != 2 or indices.shape[1] != 3:
        return None

    color = [0.8, 0.8, 0.8, 1.0]
    vertex_colors = None
    try:
        colors_buf = geom.colors
        if colors_buf is not None and colors_buf.data is not None:
            c = colors_buf.data
            vertex_colors = c.tolist()
            avg = c.mean(axis=0).tolist()
            if len(avg) == 3:
                avg.append(1.0)
            color = avg
    except (AttributeError, KeyError):
        pass

    if color == [0.8, 0.8, 0.8, 1.0]:
        try:
            mat_color = actor.material.color
            color = [float(mat_color.r), float(mat_color.g), float(mat_color.b), 1.0]
        except (AttributeError, KeyError):
            pass

    try:
        pos = list(float(v) for v in actor.local.position)
    except Exception:
        pos = [0.0, 0.0, 0.0]

    try:
        scale = list(float(v) for v in actor.local.scale)
    except Exception:
        scale = [1.0, 1.0, 1.0]

    name = getattr(actor, "name", None) or type(actor).__name__

    result = {
        "name": name,
        "type": "mesh",
        "vertices": positions.tolist(),
        "faces": indices.tolist(),
        "color": [round(c, 4) for c in color],
        "position": [round(p, 4) for p in pos],
        "scale": [round(s, 4) for s in scale],
    }
    if vertex_colors is not None:
        result["vertex_colors"] = vertex_colors
    return result


def extract_camera_data(show_manager):
    """Extract camera position, target, and field of view."""
    cam = show_manager.screens[0].camera
    pos = [float(v) for v in cam.world.position]
    fov = float(cam.fov)
    target = [0.0, 8.75, 0.0]  # center height of helix

    return {
        "position": [round(v, 4) for v in pos],
        "target": [round(v, 4) for v in target],
        "fov": round(fov, 2),
    }


def main():
    print("Creating DNA double helix scene...")
    scene, actors = create_scene()

    print("Rendering screenshot...")
    screenshot_path = os.path.join(SCRIPT_DIR, "screenshots", "helix_fury.png")

    show_m = fury.window.ShowManager(
        scene=scene, window_type="offscreen", size=(1920, 1080)
    )

    # Slightly elevated side view to show the helix twist
    cam = show_m.screens[0].camera
    cam.world.position = (12, 12, 16)
    cam.look_at((0, 8.75, 0))
    cam.fov = 42

    show_m.render()
    show_m.window.draw()
    show_m.snapshot(screenshot_path)
    print(f"  Saved {screenshot_path}")

    print("Extracting geometry...")
    actor_data_list = []
    for actor in actors:
        data = extract_actor_data(actor)
        if data is not None:
            actor_data_list.append(data)
            print(f"  {data['name']}: {len(data['vertices'])} vertices, {len(data['faces'])} faces")
        else:
            name = getattr(actor, "name", type(actor).__name__)
            print(f"  {name}: skipped")

    camera_data = extract_camera_data(show_m)
    print(f"  Camera at {camera_data['position']}, fov={camera_data['fov']}")

    scene_export = {"actors": actor_data_list, "camera": camera_data}
    json_path = os.path.join(SCRIPT_DIR, "helix_scene_data.json")
    with open(json_path, "w") as f:
        json.dump(scene_export, f, indent=2)

    print(f"Saved {json_path} with {len(actor_data_list)} actors")
    print("Done!")


if __name__ == "__main__":
    main()
