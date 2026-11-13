"""Rasterise Natural Earth low-res land polygons (public domain) into an equirectangular PNG.

    python tools/make_earth_texture.py naturalearth_lowres.shp assets/earth_land_2048.png 2048

The shapefile is Natural Earth's 1:110m countries (public domain, naturalearthdata.com).
It used to ship with geopandas (< 1.0) as geopandas/datasets/naturalearth_lowres.
"""
import struct, sys
from PIL import Image, ImageDraw, ImageFilter

shp, out, W = sys.argv[1], sys.argv[2], int(sys.argv[3])
H = W // 2
data = open(shp, "rb").read()
pos, rings = 100, []
while pos < len(data):
    _num, length = struct.unpack(">ii", data[pos:pos + 8])
    rec = data[pos + 8: pos + 8 + length * 2]
    pos += 8 + length * 2
    if struct.unpack("<i", rec[:4])[0] != 5:
        continue
    nparts, npts = struct.unpack("<ii", rec[36:44])
    parts = list(struct.unpack("<%di" % nparts, rec[44:44 + 4 * nparts])) + [npts]
    pts = struct.unpack("<%dd" % (2 * npts), rec[44 + 4 * nparts: 44 + 4 * nparts + 16 * npts])
    for a, b in zip(parts, parts[1:]):
        rings.append([(pts[2 * i], pts[2 * i + 1]) for i in range(a, b)])

def area(r):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1])) / 2

img = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(img)
for r in rings:                      # shapefile outer rings are clockwise (negative area)
    xy = [((lon + 180) / 360 * W, (90 - lat) / 180 * H) for lon, lat in r]
    d.polygon(xy, fill=255 if area(r) < 0 else 0)
img = img.filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 110 else 0)
img.save(out)
print("rings:", len(rings))
