"""Lossless archive of the RGB pixels used by WebJudge, deduplicated by tile."""

import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from PIL import Image

TILE = 128


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pack(folder, bundle):
    manifest = {}
    seen = set()
    with ZipFile(bundle, "w", compression=ZIP_STORED) as archive:
        for path in sorted(folder.glob("*.png")):
            with Image.open(path) as src:
                img = src.convert("RGB")
            ids = []
            for top in range(0, img.height, TILE):
                for left in range(0, img.width, TILE):
                    tile = img.crop(
                        (
                            left,
                            top,
                            min(img.width, left + TILE),
                            min(img.height, top + TILE),
                        )
                    )
                    ident = digest(
                        tile.width.to_bytes(2, "big")
                        + tile.height.to_bytes(2, "big")
                        + tile.tobytes()
                    )
                    ids.append(ident)
                    if ident not in seen:
                        buf = io.BytesIO()
                        tile.save(buf, format="WEBP", lossless=True, method=3)
                        archive.writestr("tiles/" + ident, buf.getvalue())
                        seen.add(ident)
            manifest[path.name] = [img.width, img.height, digest(img.tobytes()), ids]
        archive.writestr("manifest.json", json.dumps(manifest))


def unpack(bundle, folder):
    folder.mkdir(parents=True, exist_ok=True)
    with ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for name, (width, height, sha, ids) in manifest.items():
            if Path(name).name != name or not name.endswith(".png"):
                raise ValueError("Unsafe frame name")
            dest = folder / name
            if dest.exists():
                with Image.open(dest) as old:
                    if digest(old.convert("RGB").tobytes()) != sha:
                        raise ValueError("Existing frame mismatch")
                continue
            img = Image.new("RGB", (width, height))
            keys = iter(ids)
            for top in range(0, height, TILE):
                for left in range(0, width, TILE):
                    with Image.open(
                        io.BytesIO(archive.read("tiles/" + next(keys)))
                    ) as tile:
                        img.paste(tile, (left, top))
            if next(keys, None) is not None or digest(img.tobytes()) != sha:
                raise ValueError("Pixel manifest mismatch")
            tmp = dest.with_suffix(".reconstruct")
            img.save(tmp, format="PNG", compress_level=1)
            tmp.replace(dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("pack", "unpack"))
    parser.add_argument("folder", type=Path)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    if args.mode == "pack":
        pack(args.folder, args.bundle)
    else:
        unpack(args.bundle, args.folder)
