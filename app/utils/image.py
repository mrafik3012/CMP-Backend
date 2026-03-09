"""Image compression to WebP <= 150KB. FR-DOC-006."""
import io
from pathlib import Path

from PIL import Image


def compress_to_webp(image_path: str | Path, max_kb: int = 150) -> bytes:
    """Compress image to WebP, target max_kb using binary-search quality."""
    img = Image.open(image_path).convert("RGB")
    buf = io.BytesIO()
    lo, hi = 1, 100
    best = None
    while lo <= hi:
        q = (lo + hi) // 2
        buf.seek(0)
        buf.truncate(0)
        img.save(buf, "WEBP", quality=q, method=6)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= max_kb:
            best = buf.getvalue()
            lo = q + 1
        else:
            hi = q - 1
    return best or buf.getvalue()
