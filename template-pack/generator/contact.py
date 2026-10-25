import sys, glob, os
from PIL import Image
fs = sorted(glob.glob("_preview/*-1.png"), key=lambda f: f)
order = [l.split("|")[0] for l in open("_preview/order.txt").read().split("\n") if l]
fs = [f"_preview/{i}-1.png" for i in order if os.path.exists(f"_preview/{i}-1.png")]
per, tw = int(sys.argv[2]), int(sys.argv[3])
chunk = fs[int(sys.argv[1]) * per:(int(sys.argv[1]) + 1) * per]
ims = [Image.open(f) for f in chunk]
ims = [i.resize((tw, round(i.height * tw / i.width))) for i in ims]
cols = max(1, min(len(ims), 3 if per <= 6 else 4))
rows = (len(ims) + cols - 1) // cols
rh = max(i.height for i in ims)
sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (rh + 8) + 8), "#888")
for k, im in enumerate(ims): sheet.paste(im, (8 + (k % cols) * (tw + 8), 8 + (k // cols) * (rh + 8)))
sheet.save(f"_preview/sheet{sys.argv[1]}.png"); print(sheet.size, [os.path.basename(f) for f in chunk])
