# FURY → Blender Export Pipeline (Proof of Concept)

> GSoC 2026 proof-of-concept for [Project 4: Exporting FURY Scenes and Animations to Blender](https://github.com/fury-gl/fury/wiki/Google-Summer-of-Code-2026#project-4-exporting-fury-scenes-and-animations-to-blender-for-advanced-rendering)

## Results

| FURY (real-time rendering) | Blender (Cycles/EEVEE rendering) |
|---|---|
| ![FURY render](screenshots/fury_render.png) | ![Blender render](screenshots/blender_render.png) |

## What this demonstrates

- Extracting geometry (vertices, faces, colors) from FURY v2 (pygfx-based) scene objects
- Coordinate system transformation (pygfx Y-up → Blender Z-up)
- Recreating meshes with materials in Blender via the bpy Python API
- Camera position and FOV transfer between the two systems
- Automated rendering pipeline (headless Blender)

## How to run

### Prerequisites
- Python 3.9+
- [FURY](https://github.com/fury-gl/fury) (v2 branch)
- [Blender](https://www.blender.org/download/) 4.0+ (must be accessible via `blender` CLI command)

### Steps

**Step 1: Create the FURY scene and export geometry**
```bash
python create_fury_scene.py
```
This creates `scene_data.json` and `screenshots/fury_render.png`.

**Step 2: Import into Blender and render**
```bash
blender --background --python import_to_blender.py
```
This creates `fury_scene.blend` and `screenshots/blender_render.png`.

**Step 3 (optional): Open in Blender GUI**
```bash
blender fury_scene.blend
```

## Architecture

```
FURY Scene (pygfx)          Export Pipeline           Blender Scene
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ Scene         │     │                     │     │ Scene             │
│  ├─ Camera    │────▶│  scene_data.json    │────▶│  ├─ Camera        │
│  ├─ Sphere(s) │     │  (vertices, faces,  │     │  ├─ Mesh + Mat    │
│  ├─ Cone(s)   │     │   colors, camera,   │     │  ├─ Mesh + Mat    │
│  ├─ Cylinder  │     │   transforms)       │     │  ├─ Sun Light     │
│  ├─ Box       │     └─────────────────────┘     │  ├─ Fill Light    │
│  ├─ Arrow     │                                  │  └─ Rim Light     │
│  └─ Disk      │                                  └──────────────────┘
└──────────────┘
```

## How it works

### Geometry extraction (`create_fury_scene.py`)

FURY v2 actors are pygfx `WorldObject`s (typically `Mesh` subclasses). Each actor exposes:
- `actor.geometry.positions.data` — Nx3 vertex array (numpy)
- `actor.geometry.indices.data` — Mx3 face index array
- `actor.geometry.colors.data` — per-vertex colors
- `actor.material.color` — base material color
- `actor.local.position / .scale` — local transform

The script iterates over all actors, extracts this data, and serializes it to JSON.

### Coordinate transform

pygfx uses a **Y-up** coordinate system (like Three.js):
- X → right, Y → up, Z → toward viewer

Blender uses **Z-up**:
- X → right, Z → up, Y → into screen

Conversion: `(x, y, z)_pygfx → (x, z, -y)_blender`

### Blender import (`import_to_blender.py`)

The Blender script reads `scene_data.json` and for each actor:
1. Creates a `bpy.data.meshes` from vertices + faces
2. Assigns a Principled BSDF material with the actor's color
3. Applies position/scale transforms
4. Enables smooth shading

It also sets up camera (with Track To constraint), three-point lighting, and renders the result.

## Known limitations (POC scope)

- Static scenes only — no animation export yet
- Basic material colors only — no textures, no PBR properties
- Billboard actors (impostor spheres) are excluded — only real mesh geometry is exported
- No light export from FURY — Blender lights are manually added
- Coordinate transform may need refinement for rotations/quaternions

## What a full GSoC implementation would add

- **Animation export**: FURY keyframes → Blender F-curves
- **Material fidelity**: PBR properties, textures, opacity, emissive maps
- **Light transfer**: FURY lights → Blender lights with matching properties
- **glTF intermediate pathway**: Export to glTF first for broader compatibility
- **Batch export**: Handle scenes with 10,000+ actors efficiently
- **Round-trip support**: Import Blender scenes back into FURY
- **CLI tool**: `fury-export scene.py --format blender --output scene.blend`

## Author

**Jigyasu Rajput** — GSoC 2025 contributor (Python Software Foundation)
[GitHub](https://github.com/JigyasuRajput) | Currently contributing to fury-gl/fury (5+ PRs on v2 branch)
