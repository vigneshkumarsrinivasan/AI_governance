"""Shared helpers for PDF-sourced parsers (NIST / OWASP / UK / DPDP)."""

from __future__ import annotations

import re
from typing import List

import pymupdf

_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
              "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-",
              "—": "-", " ": " ", "﻿": ""}


def page_texts(raw: bytes) -> List[str]:
    doc = pymupdf.open(stream=raw, filetype="pdf")
    return [doc[i].get_text() for i in range(doc.page_count)]


def clean(text) -> str:
    if not text:
        return ""
    text = str(text)
    for k, v in _LIGATURES.items():
        text = text.replace(k, v)
    # de-hyphenate words split across line breaks: "inte-\ngrated" -> "integrated"
    text = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", text)
    # collapse intra-paragraph newlines to spaces, keep blank-line paragraph breaks
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def strip_headers_footers(pages: List[str], markers: List[str]) -> str:
    out = []
    for p in pages:
        lines = [ln for ln in p.splitlines()
                 if not any(m.lower() in ln.lower() for m in markers)
                 and not re.fullmatch(r"\s*\d{1,4}\s*", ln)]
        out.append("\n".join(lines))
    return "\n".join(out)
