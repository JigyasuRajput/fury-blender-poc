"""Create a molecular visualization scene in FURY and export to JSON.

Demonstrates a real-world scientific use case: ball-and-stick model of a
caffeine-like molecular structure with atoms of varying sizes and colors
(carbon, nitrogen, oxygen, hydrogen) connected by bonds.
"""

import json
import os
import sys

import numpy as np

import fury

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Atom types: (element, color_rgb, radius)
ATOM_STYLES = {
    "C": ([0.3, 0.3, 0.3], 0.4),      # Carbon — dark gray
    "N": ([0.2, 0.2, 0.9], 0.35),      # Nitrogen — blue
    "O": ([0.9, 0.15, 0.15], 0.35),    # Oxygen — red
    "H": ([0.9, 0.9, 0.9], 0.2),       # Hydrogen — white
}


def caffeine_atoms():
    """Return atom positions, elements, and bonds for a caffeine-like molecule.

    This is a simplified 3D layout inspired by caffeine (C8H10N4O2),
    not a PDB-accurate structure, but visually representative.
    """
    # Approximate 3D coordinates for a caffeine-like ring structure
    atoms = [
        # Purine-like double ring (C and N atoms)
        ("C", [0.0, 0.0, 0.0]),
        ("N", [1.2, 0.7, 0.0]),
        ("C", [2.4, 0.0, 0.1]),
        ("N", [2.4, -1.4, 0.1]),
        ("C", [1.2, -2.1, 0.0]),
        ("C", [-0.1, -1.4, 0.0]),
        ("N", [-1.3, -2.1, -0.1]),
        ("C", [-1.3, -3.5, -0.1]),
        ("N", [0.0, -4.0, 0.0]),
        ("C", [1.0, -3.4, 0.0]),
        # Oxygen atoms (carbonyl groups)
        ("O", [3.5, 0.6, 0.2]),
        ("O", [-2.3, -4.2, -0.2]),
        # Methyl groups (CH3) — simplified as single C
        ("C", [1.3, 2.1, 0.1]),    # N-methyl 1
        ("C", [-2.5, -1.4, -0.2]), # N-methyl 2
        ("C", [3.7, -2.0, 0.2]),   # N-methyl 3
        # Hydrogen atoms on methyl groups and ring
        ("H", [1.3, 2.7, 1.0]),
        ("H", [0.5, 2.6, -0.5]),
        ("H", [2.2, 2.5, -0.4]),
        ("H", [-2.5, -0.8, -1.1]),
        ("H", [-3.3, -1.0, 0.4]),
        ("H", [-2.8, -2.4, -0.3]),
        ("H", [4.1, -1.5, 1.1]),
        ("H", [4.4, -1.8, -0.5]),
        ("H", [3.5, -3.0, 0.4]),
        ("H", [1.8, -4.0, 0.0]),
    ]

    # Bonds: pairs of atom indices
    bonds = [
        (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0),  # ring 1
        (5, 6), (6, 7), (7, 8), (8, 9), (9, 4),           # ring 2
        (2, 10), (7, 11),                                    # C=O
        (1, 12), (6, 13), (3, 14),                           # N-CH3
        (12, 15), (12, 16), (12, 17),                        # methyl H
        (13, 18), (13, 19), (13, 20),
        (14, 21), (14, 22), (14, 23),
        (9, 24),                                              # ring H
    ]

    return atoms, bonds


def create_scene():
    """Build a molecular visualization scene."""
    scene = fury.window.Scene(background=(0.05, 0.05, 0.08, 1.0))
    actors = []

    atoms, bonds = caffeine_atoms()

    # Scale up the molecule so it fills the viewport nicely
    scale_factor = 1.8

    # --- Atom spheres ---
    elements = [a[0] for a in atoms]
    centers = np.array([a[1] for a in atoms], dtype=np.float32) * scale_factor
    colors = np.array([ATOM_STYLES[e][0] for e in elements], dtype=np.float32)
    radii = np.array([ATOM_STYLES[e][1] for e in elements], dtype=np.float32) * scale_factor

    # impostor=False creates real mesh geometry instead of
    # billboard SDFs, which is needed for geometry extraction
    atom_actor = fury.actor.sphere(
        centers=centers,
        colors=colors,
        radii=radii,
        impostor=False,
    )
    atom_actor.name = "atoms"
    actors.append(atom_actor)
    scene.add(atom_actor)
    print(f"  Added {len(atoms)} atoms")

    # --- Bond sticks (cylinders between bonded atom pairs) ---
    bond_centers = []
    bond_directions = []
    bond_colors = []
    bond_heights = []

    for i, j in bonds:
        p1 = centers[i]
        p2 = centers[j]
        mid = (p1 + p2) / 2.0
        diff = p2 - p1
        length = float(np.linalg.norm(diff))
        direction = diff / length if length > 1e-6 else np.array([0, 1, 0])

        bond_centers.append(mid)
        bond_directions.append(direction)
        bond_heights.append(length)
        # Use a neutral gray for bonds
        bond_colors.append([0.6, 0.6, 0.55])

    bond_actor = fury.actor.cylinder(
        centers=np.array(bond_centers, dtype=np.float32),
        directions=np.array(bond_directions, dtype=np.float32),
        colors=np.array(bond_colors, dtype=np.float32),
        height=np.mean(bond_heights),
        radii=0.08 * scale_factor,
    )
    bond_actor.name = "bonds"
    actors.append(bond_actor)
    scene.add(bond_actor)
    print(f"  Added {len(bonds)} bonds")

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

    try:
        target = [0.0, -2.0, 0.0]  # center of molecule
    except Exception:
        target = [0.0, 0.0, 0.0]

    return {
        "position": [round(v, 4) for v in pos],
        "target": [round(v, 4) for v in target],
        "fov": round(fov, 2),
    }


def main():
    print("Creating molecular visualization scene...")
    scene, actors = create_scene()

    print("Rendering screenshot...")
    screenshot_path = os.path.join(PROJECT_ROOT, "screenshots", "molecular_fury.png")

    show_m = fury.window.ShowManager(
        scene=scene, window_type="offscreen", size=(1920, 1080)
    )

    # Angled view looking at the molecule
    cam = show_m.screens[0].camera
    cam.world.position = (8, 6, 18)
    cam.look_at((0, -2, 0))
    cam.fov = 40

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
    json_path = os.path.join(PROJECT_ROOT, "scene_data", "molecular_scene_data.json")
    with open(json_path, "w") as f:
        json.dump(scene_export, f, indent=2)

    print(f"Saved {json_path} with {len(actor_data_list)} actors")
    print("Done!")


if __name__ == "__main__":
    main()
