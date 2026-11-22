"""Export the case: STLs in print orientation, a STEP assembly and preview images.

    .venv/bin/python -m case.build [--key-width 6.5] [--out case/out]
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402
from build123d import Compound, Pos, Rot, export_step, export_stl  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection            # noqa: E402

from case import params as p                                       # noqa: E402
from case.parts import (board_envelope, body, front_plate, key, lid,  # noqa: E402
                        motor_envelope, to_world)

PRINTED = ('body', 'front_plate', 'lid', 'key')
COLOURS = {'body': '#4a6fa5', 'front_plate': '#c8553d', 'lid': '#6b9e5a', 'key': '#e0a030',
           'board': '#2e7d32', 'motor': '#555555'}
# Rotation of each part (world frame) onto the bed: body floor-down, lid top-down,
# plate on its outer face, key as it is (ridge down).
PRINT_ROTATION = {'body': Rot(0, 0, 0), 'lid': Rot(180, 0, 0),
                  'front_plate': Rot(0, 90, 0), 'key': Rot(0, 0, 0)}


def assembled(key_w: float = p.KEY_W) -> dict:
    """World-frame parts as assembled."""
    return {'body': to_world(body(key_w)), 'front_plate': to_world(front_plate()),
            'lid': to_world(lid()), 'key': to_world(key(key_w))}


def on_bed(part, name):
    """Rotate into print orientation and move the bounding box to x, y, z >= 0, z min = 0."""
    turned = PRINT_ROTATION[name] * part
    low = turned.bounding_box().min
    return Pos(-low.X, -low.Y, -low.Z) * turned


def _mesh(shape, tolerance=0.2, max_edge=4.0):
    """Triangles (n, 3, 3), long ones split so matplotlib's per-triangle depth sort works."""
    vertices, triangles = shape.tessellate(tolerance)
    points = np.array([[v.X, v.Y, v.Z] for v in vertices])
    tris = points[np.array(triangles)]
    while True:
        edges = np.linalg.norm(tris - np.roll(tris, -1, axis=1), axis=2)   # edge i: i -> i+1
        longest = edges.argmax(axis=1)
        split = edges.max(axis=1) > max_edge
        if not split.any():
            return tris
        keep, todo = tris[~split], tris[split]
        k = longest[split]
        a = todo[np.arange(len(todo)), k]
        b = todo[np.arange(len(todo)), (k + 1) % 3]
        c = todo[np.arange(len(todo)), (k + 2) % 3]
        mid = (a + b) / 2
        tris = np.concatenate([keep, np.stack([a, mid, c], 1), np.stack([mid, b, c], 1)])


def _faces(shape, colour, alpha):
    tris = _mesh(shape)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    light = np.array([-0.5, -0.4, 0.8]) / np.linalg.norm([-0.5, -0.4, 0.8])
    shade = 0.35 + 0.65 * np.abs(normals @ light)
    base = np.array(matplotlib.colors.to_rgb(colour))
    rgb = np.clip(shade[:, None] * base, 0, 1)
    return tris, np.c_[rgb, np.full(len(rgb), alpha)]


def _preview(path, items, elev, azim, title):
    """One collection for everything, so triangles of different parts sort against each other."""
    tris, colours = zip(*(_faces(shape, colour, alpha) for shape, colour, alpha in items))
    tris, colours = np.concatenate(tris), np.concatenate(colours)
    fig = plt.figure(figsize=(10, 8), dpi=130)
    ax = fig.add_subplot(projection='3d', computed_zorder=False)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colours, edgecolors='none'))
    low, high = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    centre, half = (low + high) / 2, (high - low).max() / 2
    for setter, c in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), centre):
        setter(c - half, c + half)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title)
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)


def build(out_dir: Path, key_w: float = p.KEY_W) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = assembled(key_w)
    written = []
    for name in PRINTED:
        path = out_dir / f'{name}.stl'
        export_stl(on_bed(parts[name], name), path, tolerance=0.01, angular_tolerance=0.1)
        written.append(path)

    for name, part in parts.items():
        part.label = name
    step = out_dir / 'case.step'
    export_step(Compound(children=list(parts.values())), step)
    written.append(step)

    board = to_world(board_envelope())
    motor = to_world(motor_envelope())
    exploded = [(Pos(0, 0, 30) * parts['lid'], COLOURS['lid'], 1.0),
                (parts['body'], COLOURS['body'], 1.0),
                (Pos(25, 0, 0) * parts['front_plate'], COLOURS['front_plate'], 1.0),
                (Pos(25, 0, 0) * motor, COLOURS['motor'], 0.35),
                (Pos(0, 0, -15) * parts['key'], COLOURS['key'], 1.0),
                (board, COLOURS['board'], 1.0)]
    iso = out_dir / 'preview-iso.png'
    _preview(iso, exploded, elev=28, azim=-60,
             title='Focuser case (exploded): lid, body, front plate + motor, key')
    rear = out_dir / 'preview-rear.png'
    closed = [(parts[name], COLOURS[name], 1.0) for name in PRINTED]
    _preview(rear, closed, elev=15, azim=205,
             title='Rear: Pico USB, 12 V jack, 3.5 mm temperature jack')
    written += [iso, rear]
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key-width', type=float, default=p.KEY_W,
                        help='width of the ridge that runs in the bracket slot (mm)')
    parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'out')
    args = parser.parse_args()
    for path in build(args.out, args.key_width):
        print(path)
    print(f'Body: pause the print at {p.PAUSE_HEIGHT} mm to drop in the 1/4"-20 nut.')


if __name__ == '__main__':
    main()
