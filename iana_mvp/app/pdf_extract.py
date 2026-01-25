from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

import fitz

_ws = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    s = s.lower()
    s = _ws.sub(" ", s).strip()
    return s


@dataclass
class TextBlock:
    page: int
    bbox: list
    text: str
    text_norm: str


def extract_text_blocks(pdf_path: str) -> List[TextBlock]:
    doc = fitz.open(pdf_path)
    blocks: List[TextBlock] = []
    for i, page in enumerate(doc):
        raw = page.get_text("blocks")
        for b in raw:
            x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], b[4]
            if not txt or not txt.strip():
                continue
            tnorm = normalize_text(txt)
            blocks.append(
                TextBlock(page=i + 1, bbox=[x0, y0, x1, y1], text=txt.strip(), text_norm=tnorm)
            )
    doc.close()
    return blocks
