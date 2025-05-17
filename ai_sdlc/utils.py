import re
import unicodedata

def slugify(name: str) -> str:
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    return slug or "idea"
