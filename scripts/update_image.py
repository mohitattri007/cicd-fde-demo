"""Update the first Kubernetes container image in a deployment manifest."""
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: update_image.py <deployment.yaml> <new-image:tag>")
path = Path(sys.argv[1])
new_image = sys.argv[2]
if not path.is_file():
    raise SystemExit(f"Manifest not found: {path}")
text = path.read_text(encoding="utf-8")
pattern = re.compile(r"^(\s*image:\s*).+$", re.MULTILINE)
updated, count = pattern.subn(lambda m: f"{m.group(1)}{new_image}", text, count=1)
if count != 1:
    raise SystemExit(f"Expected exactly one image field in {path}; found {count}")
path.write_text(updated, encoding="utf-8")
print(f"Updated image in {path} to {new_image}")
