"""
Parametric scope turret lock generator
======================================

Units: millimetres

A printed lock that closes round a riflescope's turret housing so
club members cannot turn the elevation or windage turrets (or pull
the caps off them) and move the zero.  It fits with the scope left in
its rings:

    hood    drops over the turrets from above: cups over the
            elevation and windage turrets, a box round the turret
            housing, collars resting on the tube, and a lock block on
            the left side
    plate   thin flat plate that slides in under the scope from the
            left, through a slot in the lock block, into grooves in
            the hood's walls

One bolt goes down through the lock block and through the plate, so
the plate cannot be slid back out, and the plate in its grooves stops
the hood lifting off.  The turret housing keeps the lock from sliding
along the tube and the turrets stop it turning.  Nothing presses on
the turrets.  A left knob (parallax / illumination) stays reachable
through a slot.

Requires:
    CadQuery, matplotlib (preview only)

Scope profiles:
    params.json                 lock and hardware settings, shared
    scopes/<name>/scope.json    one scope's measurements ("scope"
                                group); may also override any key
                                from params.json

Run:
    python generate.py                     every profile in scopes/
    python generate.py scopes/<name>       one profile

Output (in the profile's folder):
    <name>_hood.stl     hood
    <name>_plate.stl    sliding plate
    <name>_preview.png  assembled / exploded / part views

Both STLs are in print orientation.  The hood prints as fitted, open
side down; the ceilings inside (over the turret housing and in the
turret cups) and the top of the plate slot bridge.

Hardware: 1 x M5 x 25 socket head bolt (BOLT_LENGTH), washer under the
head and a plain hex nut.

Fitting (scope stays in its rings):
    1. Slide the nut into the slot in the left face of the lock block.
    2. Lower the hood over the turrets.
    3. Slide the plate in under the scope from the left, through the
       lock block, until it stops against the right-hand wall.
    4. Drop the bolt and washer in from the top, through the nut and
       the plate, and tighten.
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import cadquery as cq


# ============================================================
# PARAMETERS
# ============================================================

HERE = Path(__file__).parent
PARAMS_FILE = HERE / "params.json"
SCOPES_DIR = HERE / "scopes"
PROFILE_NAME = "scope.json"


def profile_dirs():

    return sorted(path.parent for path in SCOPES_DIR.glob(f"*/{PROFILE_NAME}"))


# No profile given: build each one in its own run (the build below
# runs once, at import, for one profile).
if len(sys.argv) < 2:
    if __name__ != "__main__":
        sys.exit("Name a scope profile: scopes/<name>")
    profiles = profile_dirs()
    if not profiles:
        sys.exit(f"No profiles: add {SCOPES_DIR / '<name>' / PROFILE_NAME}")
    failed = []
    for profile in profiles:
        print(f"\n##### {profile.name}")
        if subprocess.run([sys.executable, __file__, str(profile)]).returncode:
            failed.append(profile.name)
    print()
    print(f"Built {len(profiles) - len(failed)} of {len(profiles)} profiles"
          + (f"; FAILED: {', '.join(failed)}" if failed else ""))
    sys.exit(1 if failed else 0)

# fit_test.py imports this file with the same argument.
PROFILE_DIR = Path(sys.argv[1])
if PROFILE_DIR.name == PROFILE_NAME:
    PROFILE_DIR = PROFILE_DIR.parent
PROFILE_FILE = PROFILE_DIR / PROFILE_NAME


def load_params(path):
    """
    Read a grouped parameter file into a flat {name: value} dict.
    Groups and keys starting with '_' are notes and are skipped.
    """

    try:
        with open(path, encoding="utf-8") as file:
            groups = json.load(file)
    except FileNotFoundError:
        sys.exit(f"Parameter file not found: {path}")
    except json.JSONDecodeError as error:
        sys.exit(f"{path}: invalid JSON - {error}")

    flat = {}

    for group, values in groups.items():
        if group.startswith("_"):
            continue
        for name, value in values.items():
            if name.startswith("_"):
                continue
            if name in flat:
                sys.exit(f"{path}: '{name}' appears more than once")
            flat[name] = value

    return flat


# The profile's keys win over the shared ones.
_params = {**load_params(PARAMS_FILE), **load_params(PROFILE_FILE)}


def param(name):
    try:
        return _params.pop(name)
    except KeyError:
        sys.exit(f"{PROFILE_FILE}: missing parameter '{name}'")


# Scope
TUBE_DIAMETER = param("TUBE_DIAMETER")
SADDLE_LENGTH = param("SADDLE_LENGTH")
SADDLE_WIDTH = param("SADDLE_WIDTH")
SADDLE_HEIGHT = param("SADDLE_HEIGHT")
SADDLE_DROP = param("SADDLE_DROP")
ELEVATION_DIAMETER = param("ELEVATION_DIAMETER")
ELEVATION_HEIGHT = param("ELEVATION_HEIGHT")
WINDAGE_DIAMETER = param("WINDAGE_DIAMETER")
WINDAGE_WIDTH = param("WINDAGE_WIDTH")
LEFT_KNOB_DIAMETER = param("LEFT_KNOB_DIAMETER")
LEFT_KNOB_WIDTH = param("LEFT_KNOB_WIDTH")
RING_GAP = param("RING_GAP")
RECEIVER_GAP = param("RECEIVER_GAP")

# Lock
WALL = param("WALL")
CLEARANCE = param("CLEARANCE")
TUBE_CLEARANCE = param("TUBE_CLEARANCE")
COLLAR_LENGTH = param("COLLAR_LENGTH")
PLATE_THICKNESS = param("PLATE_THICKNESS")
PLATE_GAP = param("PLATE_GAP")
PLATE_CLEARANCE = param("PLATE_CLEARANCE")
GROOVE_DEPTH = param("GROOVE_DEPTH")
GROOVE_LIP = param("GROOVE_LIP")
FINGER_TAB = param("FINGER_TAB")
NUT_TRAP_FLOOR = param("NUT_TRAP_FLOOR")
LABEL = param("LABEL")
LABEL_SIZE = param("LABEL_SIZE")

# Hardware
BOLT_DIAMETER = param("BOLT_DIAMETER")
BOLT_LENGTH = param("BOLT_LENGTH")
BOLT_HOLE_CLEARANCE = param("BOLT_HOLE_CLEARANCE")
BOLT_HEAD_DIAMETER = param("BOLT_HEAD_DIAMETER")
BOLT_HEAD_HEIGHT = param("BOLT_HEAD_HEIGHT")
WASHER_DIAMETER = param("WASHER_DIAMETER")
WASHER_THICKNESS = param("WASHER_THICKNESS")
NUT_ACROSS_FLATS = param("NUT_ACROSS_FLATS")
NUT_THICKNESS = param("NUT_THICKNESS")
NUT_CLEARANCE = param("NUT_CLEARANCE")

# Output
PREVIEW = param("PREVIEW")
CHECK_CLEARANCES = param("CHECK_CLEARANCES")

OUTPUT_PREFIX = PROFILE_DIR.resolve().name
PREVIEW_FILE = f"{OUTPUT_PREFIX}_preview.png"


# A typo in a key would otherwise be silently ignored.
if _params:
    sys.exit(
        f"{PROFILE_FILE}: unknown parameter(s): "
        + ", ".join(sorted(_params))
    )

print(f"Profile: {PROFILE_FILE}")


# ============================================================
# DERIVED DIMENSIONS
# ============================================================

# Coordinates (fitted, rifle upright):
#
#   X  along the tube, +X towards the eyepiece
#   Y  across; +Y is the shooter's right (windage turret)
#   Z  up; the tube's centre line is the X axis
#
#   end view from the eyepiece:
#
#                     ┌───┐
#                     │ E │  elevation cup
#          ┌─────┬────┤   ├────┐
#          │  ●  │           │ ┌───────┐
#     lock │bolt │  ( tube ) │ │   W   │  windage cup
#    block │     │           │ │       │
#          │ ═══════════════════════════╡  plate, in grooves,
#          └─────┘                    ──┘  slides in from the left
#
# The hood comes down over the scope from above, so below the tube's
# centre line its insides are straight down (no undercuts): a plain
# box from the left wall to the end of the windage cup, open
# underneath and closed by the plate.  Where the tube passes through
# the end walls and collars they are slotted straight down.

tube_radius = TUBE_DIAMETER / 2.0
c = CLEARANCE

# Scope (from the measurements).
saddle_half_x = SADDLE_LENGTH / 2.0
saddle_half_y = SADDLE_WIDTH / 2.0
saddle_bottom = -(tube_radius + SADDLE_DROP)
saddle_top = saddle_bottom + SADDLE_HEIGHT
elevation_radius = ELEVATION_DIAMETER / 2.0
elevation_top = ELEVATION_HEIGHT - tube_radius
windage_radius = WINDAGE_DIAMETER / 2.0
windage_end = WINDAGE_WIDTH - tube_radius
has_left_knob = LEFT_KNOB_DIAMETER > 0.0
left_radius = LEFT_KNOB_DIAMETER / 2.0
left_end = LEFT_KNOB_WIDTH - tube_radius

# Hood, inside.
inner_half_x = max(saddle_half_x, windage_radius) + c   # box below the centre line
inner_left = -(saddle_half_y + c)                        # inside of the left wall
inner_right = windage_end + c                            # inside of the windage end wall
tube_slot_half = tube_radius + TUBE_CLEARANCE            # tube's path down through the ends

# Hood, outside.
outer_half_x = inner_half_x + WALL
box_half_x = saddle_half_x + c + WALL
box_half_y = saddle_half_y + c + WALL
box_top = saddle_top + c + WALL
elevation_cup = elevation_radius + c + WALL
windage_cup = windage_radius + c + WALL
collar_radius = tube_radius + TUBE_CLEARANCE
collar_outer = collar_radius + WALL
shell_half_x = inner_half_x + COLLAR_LENGTH
shell_length = 2.0 * shell_half_x

# Plate: under the lowest thing it slides past - turret housing,
# windage turret, tube or left knob.
lowest = min(saddle_bottom, -windage_radius, -tube_radius,
             -left_radius if has_left_knob else 0.0)
plate_top = lowest - PLATE_GAP
plate_bottom = plate_top - PLATE_THICKNESS
groove_top = plate_top + PLATE_CLEARANCE
groove_bottom = plate_bottom - PLATE_CLEARANCE
groove_half_x = inner_half_x + GROOVE_DEPTH
hood_bottom = groove_bottom - GROOVE_LIP

# Bolt: upright through the lock block and the plate.  Head and
# washer recessed in the top of the block, nut slid into a slot from
# the block's left face, above the plate.  The end finishes inside the
# floor under the plate.
bolt_hole_radius = (BOLT_DIAMETER + BOLT_HOLE_CLEARANCE) / 2.0
washer_radius = WASHER_DIAMETER / 2.0
counterbore_radius = washer_radius + 0.5
nut_pocket_af = NUT_ACROSS_FLATS + NUT_CLEARANCE
nut_pocket_ac = nut_pocket_af / math.cos(math.radians(30))   # across corners
pocket_radius = max(counterbore_radius, nut_pocket_ac / 2.0)

bolt_y = inner_left - 1.5 - pocket_radius
block_left = bolt_y - pocket_radius - 2.0
left_slot_half = left_radius + c
bolt_x = left_slot_half + 1.5 + pocket_radius if has_left_knob else 0.0

bolt_tip = hood_bottom + 0.5
washer_seat = bolt_tip + BOLT_LENGTH - WASHER_THICKNESS
block_top = washer_seat + BOLT_HEAD_HEIGHT + 0.5
nut_bottom = groove_top + NUT_TRAP_FLOOR
nut_top = nut_bottom + NUT_THICKNESS + NUT_CLEARANCE

plate_left = block_left - FINGER_TAB
plate_right = inner_right + GROOVE_DEPTH - PLATE_CLEARANCE
plate_half_x = groove_half_x - PLATE_CLEARANCE


# ============================================================
# SANITY CHECKS
# ============================================================

problems = []

if elevation_top <= saddle_top:
    problems.append("ELEVATION_HEIGHT must reach above the turret housing (SADDLE_HEIGHT, SADDLE_DROP)")

if windage_end <= saddle_half_y:
    problems.append("WINDAGE_WIDTH must reach past the side of the turret housing (SADDLE_WIDTH)")

if has_left_knob and left_end <= saddle_half_y:
    problems.append("LEFT_KNOB_WIDTH must reach past the side of the turret housing (SADDLE_WIDTH)")

if saddle_half_y <= tube_radius or saddle_top <= tube_radius:
    problems.append("The turret housing must be wider and taller than the tube")

if max(elevation_radius, windage_radius) > saddle_half_x + c + WALL:
    problems.append("A turret is much wider than SADDLE_LENGTH - check the measurements")

if GROOVE_DEPTH >= WALL - 0.8:
    problems.append("GROOVE_DEPTH leaves less than 0.8 mm of wall")

if bolt_x + pocket_radius + 1.5 > outer_half_x:
    problems.append("The left knob slot leaves no room for the bolt in the lock block")

if nut_top + 2.0 > washer_seat:
    problems.append("BOLT_LENGTH is too short for the lock block")

if block_top > box_top:
    problems.append("The lock block stands above the top of the hood; use a shorter bolt")

if RING_GAP > 0.0 and shell_length > RING_GAP:
    problems.append(
        f"The lock is {shell_length:.1f} long, more than RING_GAP {RING_GAP:g}; "
        "shorten COLLAR_LENGTH"
    )

below_tube = -hood_bottom - tube_radius
if RECEIVER_GAP > 0.0 and below_tube > RECEIVER_GAP:
    problems.append(
        f"The hood reaches {below_tube:.1f} below the tube, more than RECEIVER_GAP "
        f"{RECEIVER_GAP:g}; lower PLATE_THICKNESS / GROOVE_LIP / PLATE_GAP"
    )

if problems:
    print()
    for problem in problems:
        print(f"ERROR: {problem}")
    sys.exit(1)


# ============================================================
# HELPERS
# ============================================================

def box(x0, x1, y0, y1, z0, z1):

    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def cylinder_z(radius, z0, z1, x=0.0, y=0.0):

    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(z1 - z0)
        .translate((x, y, z0))
    )


def cylinder_x(radius, x0, x1):
    """Cylinder on the X axis (the tube's centre line)."""

    return cylinder_z(radius, x0, x1).rotate((0, 0, 0), (0, 1, 0), 90)


def cylinder_y(radius, y0, y1):
    """Cylinder along Y through the origin, from y0 to y1."""

    return cylinder_z(radius, -y1, -y0).rotate((0, 0, 0), (1, 0, 0), 90)


def hex_z(across_flats, x, y, z0, z1, flats_x=False):
    """Hex prism, upright.  flats_x: two flats face +-X."""

    across_corners = across_flats / math.cos(math.radians(30))
    shape = cq.Workplane("XY").polygon(6, across_corners).extrude(z1 - z0)
    if flats_x:
        shape = shape.rotate((0, 0, 0), (0, 0, 1), 30)

    return shape.translate((x, y, z0))


def rounded(shape, selector, radius, what):
    """Fillet the selected edges, or leave them sharp if OCC refuses."""

    try:
        return shape.edges(selector).fillet(radius)
    except Exception as error:
        print(f"WARNING: {what} fillet skipped: {error}")
        return shape


def to_bed(shape):
    """Move a shape so its lowest point is on z = 0."""

    bb = shape.val().BoundingBox()
    return shape.translate((0, 0, -bb.zmin))


def volume(shape):

    return sum(solid.Volume() for solid in shape.solids().vals())


# ============================================================
# SCOPE (as measured, for the checks and preview)
# ============================================================

big = 400.0


def scope_shape(length):

    tube = cylinder_x(tube_radius, -length / 2.0, length / 2.0)
    saddle = box(
        -saddle_half_x, saddle_half_x,
        -saddle_half_y, saddle_half_y,
        saddle_bottom, saddle_top
    )
    scope = tube.union(saddle).union(
        cylinder_z(elevation_radius, 0.0, elevation_top)
    ).union(
        cylinder_y(windage_radius, 0.0, windage_end)
    )
    if has_left_knob:
        scope = scope.union(cylinder_y(left_radius, -left_end, 0.0))

    return scope


def scope_shadow(length):
    """
    Everything the hood passes on its way down: the scope with each
    part carried straight down below its widest point.
    """

    shadow = scope_shape(length).union(
        box(-length / 2.0, length / 2.0, -tube_radius, tube_radius, -big, 0.0)
    ).union(
        box(-saddle_half_x, saddle_half_x, -saddle_half_y, saddle_half_y, -big, saddle_top)
    ).union(
        box(-windage_radius, windage_radius, 0.0, windage_end, -big, 0.0)
    )
    if has_left_knob:
        shadow = shadow.union(box(-left_radius, left_radius, -left_end, 0.0, -big, 0.0))

    return shadow


# ============================================================
# HOOD
# ============================================================

print("Building hood ...")

# Outside, above the centre line: box round the turret housing and
# the turret cups.  Below it: one box from the lock block to the end
# of the windage cup.  Collars at the ends, legs straight down.
housing = rounded(
    box(-box_half_x, box_half_x, -box_half_y, box_half_y, hood_bottom, box_top),
    None, WALL, "housing"
)
lower = box(-outer_half_x, outer_half_x, block_left, inner_right + WALL, hood_bottom, 0.0)
elevation = rounded(
    cylinder_z(elevation_cup, 0.0, elevation_top + c + WALL), ">Z", WALL - 0.5, "elevation cup"
)
windage = rounded(
    cylinder_y(windage_cup, 0.0, inner_right + WALL), ">Y", WALL - 0.5, "windage cup"
).intersect(box(-big, big, -big, big, 0.0, big))
collars = cylinder_x(collar_outer, -shell_half_x, shell_half_x).union(
    box(-shell_half_x, shell_half_x, -collar_outer, collar_outer, hood_bottom, 0.0)
).intersect(box(-big, big, -big, big, hood_bottom, big))
block = box(-outer_half_x, outer_half_x, block_left, inner_left + 0.01, hood_bottom, block_top)

hood = housing.union(lower).union(elevation).union(windage).union(collars).union(block)

# Inside: clearance round the scope, straight down below the centre
# line, open underneath.
cavity = box(
    -(saddle_half_x + c), saddle_half_x + c,
    -(saddle_half_y + c), saddle_half_y + c,
    -big, saddle_top + c
).union(
    box(-inner_half_x, inner_half_x, inner_left, inner_right, -big, 0.0)
).union(
    cylinder_z(elevation_radius + c, 0.0, elevation_top + c)
).union(
    cylinder_y(windage_radius + c, 0.0, inner_right)
).union(
    cylinder_x(collar_radius, -big, big)
).union(
    box(-big, big, -tube_slot_half, tube_slot_half, -big, 0.0)
)

if has_left_knob:
    cavity = cavity.union(cylinder_y(left_slot_half, -big, 0.0)).union(
        box(-left_slot_half, left_slot_half, -big, 0.0, -big, 0.0)
    )

# Plate slot through the lock block, grooves in the end walls and the
# windage end wall.
cavity = cavity.union(
    box(-groove_half_x, groove_half_x, -big, inner_right + GROOVE_DEPTH, groove_bottom, groove_top)
)

hood = hood.cut(cavity)

# Bolt hole, counterbore for the head and washer, nut slot opening on
# the block's left face.
hood = (
    hood
    .cut(cylinder_z(bolt_hole_radius, hood_bottom - 1.0, big, bolt_x, bolt_y))
    .cut(cylinder_z(counterbore_radius, washer_seat, big, bolt_x, bolt_y))
    .cut(hex_z(nut_pocket_af, bolt_x, bolt_y, nut_bottom, nut_top, flats_x=True))
    .cut(box(
        bolt_x - nut_pocket_af / 2.0, bolt_x + nut_pocket_af / 2.0,
        -big, bolt_y, nut_bottom, nut_top
    ))
)

# Label on the lock block's left face, above the nut slot.
label_fits = False

if LABEL:
    depth = 0.6
    face = cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0), normal=(0, -1, 0))
    text = cq.Workplane(face).text(
        LABEL, LABEL_SIZE, depth, combine=False, halign="center", valign="center"
    )
    bb = text.val().BoundingBox()
    room_x = 2.0 * outer_half_x - 4.0
    room_z = block_top - nut_top - 3.0
    if bb.xlen <= room_x and bb.zlen <= room_z:
        hood = hood.cut(text.translate((
            -bb.center.x,
            block_left - 0.01 - bb.ymin,
            (nut_top + block_top) / 2.0 - bb.center.z,
        )))
        label_fits = True
    else:
        print(
            f"WARNING: label skipped - '{LABEL}' is {bb.xlen:.0f} x {bb.zlen:.0f} mm, "
            f"room for {room_x:.0f} x {room_z:.0f}; lower LABEL_SIZE"
        )


# ============================================================
# PLATE
# ============================================================

print("Building plate ...")

plate = box(
    -plate_half_x, plate_half_x, plate_left, plate_right, plate_bottom, plate_top
).cut(cylinder_z(bolt_hole_radius, -big, big, bolt_x, bolt_y))
plate = rounded(plate, "|Z", 1.0, "plate")


# ============================================================
# CLEARANCE CHECK
# ============================================================

# The hood must come straight down over the scope, the plate slide in
# from the left under it, and nothing may touch once fitted.

scope = scope_shape(shell_length + 80.0)

if CHECK_CLEARANCES:
    print("Checking clearances ...")

    plate_path = box(-plate_half_x, plate_half_x, -big, plate_right, plate_bottom, plate_top)
    tests = [
        ("hood on its way down hits the scope", hood, scope_shadow(shell_length + 80.0)),
        ("plate hits the scope", plate_path, scope),
        ("plate on its way in hits the hood", plate_path, hood),
    ]
    clashes = []

    for name, a, b in tests:
        overlap = volume(a.intersect(b))
        if overlap > 0.01:
            clashes.append(f"{name} ({overlap:.2f} mm3)")

    for clash in clashes:
        print(f"WARNING: overlap - {clash}")
    if not clashes:
        print("  no overlaps")


# ============================================================
# EXPORT (print orientation)
# ============================================================

if __name__ == "__main__":

    # Hood as fitted, open side down; plate flat.
    parts = {
        "hood": to_bed(hood),
        "plate": to_bed(plate),
    }

    out_dir = PROFILE_DIR.resolve()
    written = []

    for name, shape in parts.items():
        filename = out_dir / f"{OUTPUT_PREFIX}_{name}.stl"
        cq.exporters.export(
            shape, str(filename),
            tolerance=0.02, angularTolerance=0.1
        )
        written.append(filename.name)


# ============================================================
# PREVIEW IMAGE
# ============================================================

# Renders the lock on the scope (fitted, exploded, end and side
# views) and the parts as printed to a PNG so the design can be
# checked without a slicer.  Needs matplotlib; skipped if it is missing.


def bolt_ghost(lift=0.0):
    """Bolt, washer and nut, raised by lift."""

    return (
        cylinder_z(BOLT_DIAMETER / 2.0, bolt_tip, washer_seat + WASHER_THICKNESS, bolt_x, bolt_y)
        .union(cylinder_z(washer_radius, washer_seat, washer_seat + WASHER_THICKNESS, bolt_x, bolt_y))
        .union(cylinder_z(
            BOLT_HEAD_DIAMETER / 2.0,
            washer_seat + WASHER_THICKNESS, washer_seat + WASHER_THICKNESS + BOLT_HEAD_HEIGHT,
            bolt_x, bolt_y
        ))
        .union(hex_z(NUT_ACROSS_FLATS, bolt_x, bolt_y, nut_bottom, nut_bottom + NUT_THICKNESS, flats_x=True))
        .translate((0, 0, lift))
    )


COLORS = {
    "hood": (0.85, 0.45, 0.20),
    "plate": (0.30, 0.36, 0.42),
    "scope": (0.62, 0.66, 0.70),
    "bolt": (0.55, 0.55, 0.58),
}


def mesh(shape, color):

    import numpy as np

    vertices, triangles = cq.Compound.makeCompound(shape.vals()).tessellate(0.05, 0.2)
    if not triangles:
        return np.zeros((0, 3, 3)), np.zeros((0, 3))
    xyz = np.array([(v.x, v.y, v.z) for v in vertices])
    tris = xyz[np.array(triangles, dtype=int)]

    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals = normals / np.where(lengths == 0.0, 1.0, lengths)[:, None]

    light = np.array([-0.4, -0.7, 0.6])
    light = light / np.linalg.norm(light)

    shade = 0.35 + 0.65 * np.abs(normals @ light)
    colors = shade[:, None] * np.array(color)

    return tris, colors


def render_preview(filename):

    import numpy as np
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    lift = 45.0

    fitted = [(hood, "hood"), (plate, "plate"), (bolt_ghost(), "bolt"), (scope, "scope")]
    exploded = [
        (hood.translate((0, 0, lift)), "hood"),
        (plate.translate((0, -60.0, 0)), "plate"),
        (bolt_ghost(2.0 * lift), "bolt"),
        (scope, "scope"),
    ]

    # Cut across through the turrets, seen from the eyepiece; no
    # scope, so the walls, grooves and plate show.
    keep = box(-big, 0.0, -big, big, -big, big)
    section = [(shape.intersect(keep), name) for shape, name in fitted if name != "scope"]

    views = [
        ("On the scope", fitted, 25, -60),
        ("Exploded (plate slides in from the left)", exploded, 15, -60),
        ("From below", fitted, -60, -60),
        ("Section through the turrets", section, 0, 0),
        ("Hood (as printed)", [(parts["hood"], "hood")], 35, -60),
        ("Plate (as printed)", [(parts["plate"], "plate")], 35, -60),
    ]

    fig = plt.figure(figsize=(15, 10))

    for index, (title, items, elevation, azimuth) in enumerate(views):

        ax = fig.add_subplot(2, 3, index + 1, projection="3d")

        all_tris = []
        all_colors = []
        for shape, color_name in items:
            if not shape.vals():
                continue
            tris, colors = mesh(shape, COLORS[color_name])
            all_tris.append(tris)
            all_colors.append(colors)

        tris = np.concatenate(all_tris)
        colors = np.concatenate(all_colors)

        ax.add_collection3d(
            Poly3DCollection(tris, facecolors=colors, edgecolors="none")
        )

        lo = tris.reshape(-1, 3).min(axis=0)
        hi = tris.reshape(-1, 3).max(axis=0)
        centre = (lo + hi) / 2.0
        half = (hi - lo).max() / 2.0 + 1.0

        ax.set_xlim(centre[0] - half, centre[0] + half)
        ax.set_ylim(centre[1] - half, centre[1] + half)
        ax.set_zlim(centre[2] - half, centre[2] + half)
        ax.set_box_aspect((1, 1, 1))
        ax.set_proj_type("ortho")
        ax.view_init(elev=elevation, azim=azimuth)
        ax.set_axis_off()
        ax.set_title(title, fontsize=10)

    fig.suptitle(
        f"Scope turret lock - {shell_length:.0f} mm long, "
        f"{below_tube:.1f} mm below the tube, 1 x M{BOLT_DIAMETER:g} x {BOLT_LENGTH:g}",
        fontsize=12
    )

    fig.tight_layout()
    fig.savefig(out_dir / filename, dpi=130)


if __name__ == "__main__" and PREVIEW:
    print("Rendering preview ...")
    try:
        render_preview(PREVIEW_FILE)
        written.append(PREVIEW_FILE)
    except ImportError:
        print("Preview skipped (python -m pip install matplotlib)")
    except Exception as error:
        print(f"WARNING: Preview failed: {error}")


# ============================================================
# FINAL REPORT
# ============================================================

if __name__ == "__main__":

    # Bolt end past the nut's lower face; negative = short.
    poke = nut_bottom - bolt_tip

    print()
    print("=============================================================")
    print("SUCCESS")
    print("=============================================================")
    print()
    print("Generated:")
    for name in written:
        print(f"  {name}")
    print()
    print("Geometry:")
    print(f"  Lock:           {shell_length:.1f} long, "
          f"{inner_right + WALL - block_left:.1f} wide (lock block to windage cup)")
    print(f"  Below the tube: {below_tube:.1f} mm (bottom of the hood), plate "
          f"{PLATE_THICKNESS:g} mm thick, {PLATE_GAP:g} mm under the scope")
    print(f"  Above the tube: {elevation_top + c + WALL - tube_radius:.1f} mm "
          f"(top of the elevation cup)")
    print(f"  Right of tube:  {inner_right + WALL - tube_radius:.1f} mm "
          f"(end of the windage cup)")
    print(f"  Left of tube:   {-block_left - tube_radius:.1f} mm (lock block)")
    if has_left_knob:
        print("  Left knob:      reachable through a slot")
    print(f"  Label:          {LABEL if label_fits else '(none)'}")
    print()
    print(f"Hardware: 1 x M{BOLT_DIAMETER:g} x {BOLT_LENGTH:g} socket head bolt, washer under the "
          "head, plain hex nut")
    if poke < 0.0:
        state = f"WARNING: stops {-poke:.1f} mm short of the nut"
    else:
        state = f"through the nut and the plate, end {bolt_tip - hood_bottom:.1f} mm above the bottom"
    print(f"  lock bolt       {state}")
    print()
    print("Lower the hood over the turrets, slide the plate in from the left,")
    print("then bolt down through the lock block.")
    print("=============================================================")
