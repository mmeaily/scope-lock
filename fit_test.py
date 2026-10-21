"""
Turret lock fit test pieces
===========================

Thin slices of the real hood, built by generate.py from a scope
profile, so the scope measurements can be checked on the rifle
before printing the whole lock (each slice is a few minutes).

    fit_cross   hood cut across the scope through the turrets: lower
                it over the elevation turret; checks the housing
                width and height, both turrets and the room under
                the scope for the plate
    fit_length  hood cut along the scope through the elevation
                turret: checks the housing length and the collars

Run:
    python fit_test.py scopes/<name>

Output (fit_test/ in the profile's folder):
    fit_test_plate.stl   every slice laid out flat, ready to print
    fit_<name>.stl       the same, one slice at a time

Each slice should sit on the scope with a small, even gap round the
turret housing and turrets and the collar(s) resting on the tube.
Where it binds or is loose, correct that measurement
in the profile's scope.json and run again.
"""

# Reads the profile from the command line, as when run directly.
import generate as g


OUT_DIR = g.PROFILE_DIR / "fit_test"
THICKNESS = 3.0


def slice_x(shape):
    """Slab across the scope at the turrets, laid flat (X up)."""

    slab = shape.intersect(g.box(-THICKNESS / 2.0, THICKNESS / 2.0, -g.big, g.big, -g.big, g.big))
    return g.to_bed(slab.rotate((0, 0, 0), (0, 1, 0), -90))


def slice_y(shape):
    """Slab along the scope through the elevation turret, laid flat (Y up)."""

    slab = shape.intersect(g.box(-g.big, g.big, -THICKNESS / 2.0, THICKNESS / 2.0, -g.big, g.big))
    return g.to_bed(slab.rotate((0, 0, 0), (1, 0, 0), 90))


def main():

    OUT_DIR.mkdir(exist_ok=True)

    pieces = {
        "cross": slice_x(g.hood),
        "length": slice_y(g.hood),
    }

    plate = None
    row_y = 0.0

    for name, piece in pieces.items():
        bb = piece.val().BoundingBox()
        piece = piece.translate((-bb.xmin, -bb.ymin, 0))
        g.cq.exporters.export(piece, str(OUT_DIR / f"fit_{name}.stl"))
        moved = piece.translate((0, row_y, 0))
        plate = moved if plate is None else plate.union(moved)
        row_y += bb.ylen + 6.0
        print(f"  fit_{name}: {bb.xlen:.0f} x {bb.ylen:.0f} mm")

    g.cq.exporters.export(plate, str(OUT_DIR / "fit_test_plate.stl"))
    print(f"Wrote {OUT_DIR / 'fit_test_plate.stl'} and one STL per slice")


if __name__ == "__main__":
    main()
