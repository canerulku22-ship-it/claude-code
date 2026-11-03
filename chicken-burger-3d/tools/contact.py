"""Contact sheet of rendered frames: python tools/contact.py OUT.png DIR [DIR...]"""
import sys, os
from PIL import Image, ImageDraw
out = sys.argv[1]; dirs = sys.argv[2:]
ims = []
for d in dirs:
    for f in sorted(os.listdir(d)):
        if f.endswith(".png") and "tmp" not in f:
            ims.append((os.path.basename(d) + " " + f[:-4], Image.open(os.path.join(d, f)).convert("RGB")))
w, h = 270, 480
cols = min(len(ims), 7)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, h * rows), (40, 40, 40))
dr = ImageDraw.Draw(sheet)
for i, (lab, im) in enumerate(ims):
    x, y = (i % cols) * w, (i // cols) * h
    sheet.paste(im.resize((w, h)), (x, y))
    dr.text((x + 4, y + 4), lab, fill=(255, 255, 0))
sheet.save(out)
