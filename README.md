# FURY → Blender Export Pipeline (Proof of Concept)

> GSoC 2026 proof-of-concept for [Project 4: Exporting FURY Scenes and Animations to Blender](https://github.com/fury-gl/fury/wiki/Google-Summer-of-Code-2026#project-4-exporting-fury-scenes-and-animations-to-blender-for-advanced-rendering)

## Results

### Scene 1: Primitives

| FURY | Blender (EEVEE) |
|---|---|
| ![FURY](screenshots/primitives_fury.png) | ![Blender](screenshots/primitives_blender.png) |

### Scene 2: Caffeine Molecule (Ball-and-Stick)

| FURY | Blender (EEVEE) |
|---|---|
| ![FURY](screenshots/molecular_fury.png) | ![Blender](screenshots/molecular_blender.png) |

### Scene 3: DNA Double Helix

| FURY | Blender (EEVEE) |
|---|---|
| ![FURY](screenshots/helix_fury.png) | ![Blender](screenshots/helix_blender.png) |

## What this demonstrates

- Extracting geometry (vertices, faces, per-vertex colors) from FURY v2 (pygfx-based) scene objects
- Coordinate system transformation (pygfx Y-up → Blender Z-up)
- Per-vertex color transfer via Blender's `color_attributes` API
- Recreating meshes with Principled BSDF materials in Blender via the bpy Python API
- Camera position and FOV transfer between the two systems
- Automated rendering pipeline (headless Blender)
- Scientific visualization use cases: molecular structures, DNA helix

## How to run

### Prerequisites

- Python 3.9+
- [FURY v2](https://github.com/fury-gl/fury/tree/v2) (must be installed from the `v2` branch — `pip install fury` won't work as it installs the stable VTK-based version)
  ```bash
  git clone -b v2 https://github.com/fury-gl/fury.git
  cd fury
  pip install -e ".[dev]"
  ```
- [Blender](https://www.blender.org/download/) 4.0+ (must be accessible via `blender` CLI command)
- NumPy

> **Note:** If you just want to test the Blender import without installing FURY v2, the `scene_data.json` files are pre-generated and committed. You can skip Step 1 and run only Step 2.

### Steps

**Step 1: Create FURY scenes and export geometry**
```bash
python create_fury_scene.py        # Primitives → scene_data.json
python create_molecular_scene.py   # Caffeine molecule → molecular_scene_data.json
python create_helix_scene.py       # DNA helix → helix_scene_data.json
```

**Step 2: Import into Blender and render**
```bash
blender --background --python import_to_blender.py -- scene_data.json
blender --background --python import_to_blender.py -- molecular_scene_data.json
blender --background --python import_to_blender.py -- helix_scene_data.json
```
Renders are saved to `screenshots/` and `.blend` files to `converted-blend-files/`.

**Step 3 (optional): Open in Blender GUI**
```bash
blender converted-blend-files/molecular.blend
```

## Architecture

```
FURY Scene (pygfx)          Export Pipeline           Blender Scene
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ Scene         │     │                     │     │ Scene             │
│  ├─ Camera    │────▶│  *_scene_data.json  │────▶│  ├─ Camera        │
│  ├─ Actors    │     │  (vertices, faces,  │     │  ├─ Mesh + Mat    │
│  │  (Mesh,    │     │   vertex colors,    │     │  ├─ Mesh + Mat    │
│  │   Sphere,  │     │   camera, transforms│     │  ├─ Sun Light     │
│  │   Cylinder,│     │   )                 │     │  ├─ Fill Light    │
│  │   ...)     │     └─────────────────────┘     │  └─ Rim Light     │
└──────────────┘                                   └──────────────────┘
```

## How it works

### Geometry extraction

FURY v2 actors are pygfx `WorldObject`s (typically `Mesh` subclasses). Each actor exposes:
- `actor.geometry.positions.data` — Nx3 vertex array (numpy)
- `actor.geometry.indices.data` — Mx3 face index array
- `actor.geometry.colors.data` — Nx3 per-vertex RGB colors
- `actor.material.color` — base material color (fallback)
- `actor.local.position / .scale` — local transform

> **Note:** Sphere actors are created with `impostor=False` to generate real mesh geometry instead of billboard impostors (SDFs rendered on flat quads), which cannot be exported as mesh data.

The scripts iterate over all actors, extract this data, and serialize it to JSON including per-vertex color arrays for accurate color reproduction in Blender.

### Coordinate transform

pygfx uses a **Y-up** coordinate system (like Three.js):
- X → right, Y → up, Z → toward viewer

Blender uses **Z-up**:
- X → right, Z → up, Y → into screen

Conversion: `(x, y, z)_pygfx → (x, z, -y)_blender`

### Blender import (`import_to_blender.py`)

The Blender script reads a `*_scene_data.json` and for each actor:
1. Creates a `bpy.data.meshes` from vertices + faces (with coordinate transform)
2. Applies per-vertex colors via `mesh.color_attributes` when available
3. Wires vertex colors into Principled BSDF via a `ShaderNodeVertexColor` node
4. Falls back to a flat material color when per-vertex data isn't present
5. Applies position/scale transforms and smooth shading

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
