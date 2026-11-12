"""Landmark library and automatic beat calculation.

A landmark "beat" is the fold where the stack first reaches a real-world
reference. The fold is found from the material's thickness, so every
material gets its own beats automatically:

    beat fold = first n where thickness x 2^n >= match x reference height

`match` is 1.0 for "pass" landmarks (the stack must really be taller: Big
Ben, the Moon...) and 0.65 for "about the size of" comparisons (notebook,
phone, person), where a stack 65-100% of the size reads as comparable.

For 0.1 mm paper this gives exactly the series' canonical beats:
  7 notebook, 10 phone, 14 person, 20 Big Ben, 23 Burj Khalifa,
  27 Everest & planes, 32 Space Station, 42 the Moon.

Positions are in metres relative to the foot of the stack (x to the right,
y away from the camera, z up). Landmarks stand to the left of the stack so
the right edge stays clear of TikTok's buttons.
"""

import math

# Fields:
#   height_m        reference height used to find the beat
#   match           fraction of height_m the stack must reach (see above)
#   kind            "pass" landmarks appear as the beat fold starts, so the
#                   stack visibly overtakes them; "compare" ones pop in after
#   labels          (model part, name, value) callouts drawn by the overlay
#   pos             (x, y) of the model's base in metres
#   width_m         footprint width, used to retire it before the (always
#                   screen-readable) column grows into it
#   frame_h/frame_w height and left-hand width (metres) the camera must show
#   lead_folds      appear this many folds early (for far-away objects)
LIBRARY = [
    dict(id="notebook", height_m=0.015, match=0.65, kind="compare",
         labels=[("main", "THICK NOTEBOOK", "~15 mm")],
         pos=(-0.024, 0.128), width_m=0.148, frame_h=0.070, frame_w=0.030),
    dict(id="phone", height_m=0.147, match=0.65, kind="compare",
         labels=[("main", "PHONE", "~15 cm")],
         pos=(-0.064, 0.010), width_m=0.0715, frame_h=0.150, frame_w=0.105),
    dict(id="person", height_m=1.75, match=0.65, kind="compare",
         labels=[("main", "PERSON", "1.75 m")],
         pos=(-0.62, 0.20), width_m=0.50, frame_h=1.80, frame_w=0.90),
    dict(id="big_ben", height_m=96.0, match=1.0, kind="pass",
         labels=[("main", "BIG BEN", "96 m")],
         pos=(-34.0, 14.0), width_m=15.0, frame_h=100.0, frame_w=44.0),
    dict(id="burj_khalifa", height_m=828.0, match=1.0, kind="pass",
         labels=[("main", "BURJ KHALIFA", "828 m")],
         pos=(-250.0, 90.0), width_m=120.0, frame_h=860.0, frame_w=320.0),
    dict(id="everest_planes", height_m=11000.0, match=1.0, kind="pass",
         labels=[("main", "EVEREST", "8,849 m"), ("plane", "PLANES", "~11 km")],
         pos=(-5200.0, 15000.0), width_m=16000.0, frame_h=11500.0, frame_w=7000.0),
    dict(id="space_station", height_m=408000.0, match=1.0, kind="pass",
         labels=[("main", "SPACE STATION", "408 km")],
         pos=(-140000.0, 0.0), width_m=1.0, frame_h=420000.0, frame_w=190000.0),
    dict(id="moon", height_m=384_400_000.0, match=1.0, kind="pass", lead_folds=2,
         labels=[("main", "THE MOON", "384,400 km")],
         pos=(0.0, 0.0), width_m=1.0, frame_h=400_000_000.0, frame_w=170_000_000.0,
         headline="PAST THE MOON!"),
]

LIBRARY_BY_ID = {lm["id"]: lm for lm in LIBRARY}

HOLD_S = 2.6          # pause at a landmark (before scaling to the duration)
FINAL_HOLD_S = 4.2    # pause after the final fold


def beat_fold(thickness_mm, landmark):
    """First fold count n where the stack reaches the landmark (may be <= 0)."""
    t0 = thickness_mm / 1000.0
    target = landmark["match"] * landmark["height_m"]
    n = math.ceil(math.log2(target / t0) - 1e-9)
    return n


def compute_beats(thickness_mm, folds, allowed="auto"):
    """Return {fold_number: landmark_dict} for this material.

    Landmarks that would land before fold 1 or after the last fold are
    skipped. If two landmarks land on the same fold the bigger one wins.
    """
    beats = {}
    for lm in LIBRARY:
        if allowed != "auto" and lm["id"] not in allowed:
            continue
        n = beat_fold(thickness_mm, lm)
        if 1 <= n <= folds:
            beats[n] = dict(lm, fold=n)   # later (bigger) entries overwrite
    return dict(sorted(beats.items()))
