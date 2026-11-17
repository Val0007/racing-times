"""Make contact_sheet.jpg from the stills in a folder (2 columns, half size, labelled with the time).

    python show-3d/contact_sheet.py episodes/<date>/stills
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

folder = Path(sys.argv[1])
files = sorted(f for f in folder.glob("*.jpg") if f.name != "contact_sheet.jpg")
if not files:
    sys.exit(f"no stills in {folder}")
w, h = 640, 360
sheet = Image.new("RGB", (w * 2, h * ((len(files) + 1) // 2)), (14, 13, 12))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    x, y = (i % 2) * w, (i // 2) * h
    sheet.paste(Image.open(f).convert("RGB").resize((w, h)), (x, y))
    d.rectangle((x, y, x + 90, y + 20), fill=(14, 13, 12))
    d.text((x + 6, y + 4), f.stem.split("_")[-1] + " s", fill=(244, 239, 228))
sheet.save(folder / "contact_sheet.jpg", quality=90)
print(f"{len(files)} stills -> {folder / 'contact_sheet.jpg'}")
