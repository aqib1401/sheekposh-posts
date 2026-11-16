"""Copy the live Sheek Posh catalogue into this repo so ChatGPT can read it.

Writes:
  catalog/products.json   one entry per postable product (or per colour, when
                          a product's variants have their own photos)
  catalog/images/*.jpg    the main photo of each entry, shrunk to 1000px JPEG

Needs Pillow (pip install pillow).
"""

import html
import io
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

STORE = "https://sheekposh.com"
REPO_RAW = "https://raw.githubusercontent.com/aqib1401/sheekposh-posts/main"
ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "catalog"
IMAGES_DIR = CATALOG_DIR / "images"
SKIP_WORDS = ("gift card", "shipping", "protection", "bundle", "test", "sample", "insurance")
UA = {"User-Agent": "Mozilla/5.0 (sheekposh-posts catalogue sync)"}


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            print(f"retry {url}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))


def fetch_products():
    products, page = [], 1
    while True:
        data = json.loads(get(f"{STORE}/products.json?limit=250&page={page}"))
        batch = data.get("products", [])
        if not batch:
            return products
        products.extend(batch)
        page += 1


def plain_text(body_html, limit=600):
    text = re.sub(r"<[^>]+>", " ", body_html or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:limit]


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def postable(p):
    hay = f"{p.get('title', '')} {p.get('product_type', '')}".lower()
    if any(w in hay for w in SKIP_WORDS):
        return False
    if not p.get("images"):
        return False
    variants = p.get("variants") or []
    return any(v.get("available") for v in variants) and any(to_float(v.get("price")) > 0 for v in variants)


def save_jpeg(raw, path, max_side=1000):
    """Shrink to max_side px on the long edge and save as a JPEG (~100-200 KB)."""
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    img.save(path, "JPEG", quality=85, optimize=True, progressive=True)


def build_entries(p):
    """One entry per product, or one per colour when variants carry their own photo."""
    variants = [v for v in p.get("variants", []) if v.get("available") and to_float(v.get("price")) > 0]
    by_image = {}
    for v in variants:
        img = (v.get("featured_image") or {}).get("src")
        if img and img not in by_image:
            by_image[img] = v

    if len(by_image) > 1:
        pairs = [(img, v, v.get("title")) for img, v in by_image.items()]
    else:
        v = variants[0]
        pairs = [(p["images"][0]["src"], v, None)]

    entries = []
    for img, v, colour in pairs:
        key = p["handle"] if not colour else f"{p['handle']}--{re.sub(r'[^a-z0-9]+', '-', colour.lower()).strip('-')}"
        url = f"{STORE}/products/{p['handle']}" + (f"?variant={v['id']}" if colour else "")
        compare = to_float(v.get("compare_at_price"))
        price = to_float(v.get("price"))
        entries.append({
            "key": key,
            "handle": p["handle"],
            "title": p.get("title"),
            "variant_title": colour,
            "product_type": p.get("product_type"),
            "tags": p.get("tags"),
            "created_at": p.get("created_at"),
            "price": price,
            "compare_at_price": compare if compare > price else None,
            "url": url,
            "description": plain_text(p.get("body_html")),
            "image_source_url": img,
            "image_file": f"catalog/images/{key}.jpg",
        })
    return entries


def main():
    products = fetch_products()
    entries = []
    for p in products:
        if postable(p):
            entries.extend(build_entries(p))
    entries.sort(key=lambda e: e["created_at"] or "", reverse=True)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    keep = set()
    for e in entries:
        path = ROOT / e["image_file"]
        keep.add(path.name)
        if not path.exists():
            try:
                save_jpeg(get(e["image_source_url"]), path)
            except Exception as err:  # noqa: BLE001
                print(f"image failed for {e['key']}: {err}", file=sys.stderr)
                e["image_file"] = None
        if e["image_file"]:
            e["image_raw_url"] = f"{REPO_RAW}/{e['image_file']}"

    for f in IMAGES_DIR.iterdir():
        if f.is_file() and f.name not in keep:
            f.unlink()

    out = {
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "store": STORE,
        "count": len(entries),
        "products": entries,
    }
    (CATALOG_DIR / "products.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(products)} products on the store, {len(entries)} postable entries saved")


if __name__ == "__main__":
    main()
