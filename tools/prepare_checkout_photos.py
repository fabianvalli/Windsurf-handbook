"""Prepare lightweight web copies of the user's checkout reference photos."""
from pathlib import Path
import argparse
from PIL import Image, ImageOps
import json

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=ROOT / 'source' / 'checkout-photos',
                    help='Folder containing the ten original checkout photos')
SOURCE = parser.parse_args().source.expanduser().resolve()
FILES = {
    'sail.png': 'checkout-sail-id',
    'board.jpg': 'checkout-board-id',
    'tablet1.jpg': 'checkout-tablet-start',
    'tablet2.jpg': 'checkout-tablet-form',
    'tablet3.jpg': 'checkout-tablet-submit',
    'signout menu 1.jpg': 'checkout-phone-menu',
    'signout page.jpg': 'checkout-phone-login',
    'tablet4.jpg': 'checkout-return-form',
    'tablet5.jpg': 'checkout-return-damage',
    'Signouts.jpg': 'checkout-active-signouts',
}
missing = [name for name in FILES if not (SOURCE / name).is_file()]
if missing:
    parser.error('Missing original photos in ' + str(SOURCE) + ': ' + ', '.join(missing))
records = []
for name, stem in FILES.items():
    source = SOURCE / name
    dest = ROOT / 'assets' / (stem + '.webp')
    with Image.open(source) as original:
        photo = ImageOps.exif_transpose(original)
        photo.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        photo.save(dest, 'WEBP', quality=88, method=6)
    records.append(dict(source=name, asset=dest.name,
                        width=photo.width, height=photo.height,
                        source_bytes=source.stat().st_size, web_bytes=dest.stat().st_size))
(ROOT / 'editorial' / 'checkout-photo-sources.json').write_text(
    json.dumps(dict(date='2026-10-17', source='User-supplied procedure photographs',
                    preparation='EXIF orientation applied; proportionally reduced to at most 1600px; WebP quality 88; no crop or content edits; originals retained',
                    photos=records), indent=2) + '\n', encoding='utf-8')
print(json.dumps(records, indent=2))
