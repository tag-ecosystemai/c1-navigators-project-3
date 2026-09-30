"""Section-aware chunking.

Chunks never cross a section heading, so each chunk belongs to exactly one section and
can be cited precisely. Long sections are split at paragraph boundaries with a small
overlap. Each chunk also records the clause numbers it contains (e.g. "3.1", "3.2").
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

from .loaders import Block, LoadedDocument

# Numeric section clauses ("3.1 Debt-to-income...") and Navigators-style rule codes
# ("POL-ELG-001", "POL-DTI-001") — the team's real policy docs use the rule-code form.
_CLAUSE = re.compile(r"(?:^|\s)(\d+\.\d+(?:\.\d+)?)(?=\s+[A-Z(])")
_RULE_CODE = re.compile(r"\bPOL-[A-Z]{2,4}-\d{2,4}\b")


@dataclass
class Chunk:
    chunk_id: str
    text: str  # the chunk body shown to the LLM / analyst
    source: str
    title: str
    category: str
    section: str  # heading path, e.g. "3 Affordability"
    page: int | None = None
    clauses: list[str] = field(default_factory=list)

    @property
    def embed_text(self) -> str:
        """Text used for embeddings and keyword search: body prefixed with its location."""
        return f"{self.title} > {self.section}\n{self.text}"

    @property
    def citation(self) -> str:
        parts = [self.title]
        if self.section:
            parts.append(self.section)
        cite = " > ".join(parts)
        if self.clauses:
            cite += f" (clause {', '.join(self.clauses)})"
        if self.page:
            cite += f", p. {self.page}"
        return cite

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        return cls(**d)


def _make_id(source: str, section: str, idx: int) -> str:
    return hashlib.sha1(f"{source}|{section}|{idx}".encode()).hexdigest()[:16]


def _split_long_paragraph(text: str, max_chars: int) -> list[str]:
    """Split one very long paragraph at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.;:])\s+", text)
    out, cur = [], ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > max_chars:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    # hard-split anything still too long (e.g. a table dumped as one line)
    final = []
    for piece in out:
        final.extend(piece[i : i + max_chars] for i in range(0, len(piece), max_chars))
    return final


def chunk_document(doc: LoadedDocument, max_chars: int = 1200, overlap_chars: int = 150) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading_stack: list[tuple[int, str]] = []
    body: list[Block] = []

    def section_path() -> str:
        # skip the document title heading (whatever level it was promoted from) in the path
        names = [h for _, h in heading_stack if h != doc.title]
        return " > ".join(names)

    def flush_section() -> None:
        if not body:
            return
        section = section_path()
        paragraphs: list[tuple[str, int | None]] = []
        for b in body:
            for piece in _split_long_paragraph(b.text, max_chars):
                paragraphs.append((piece, b.page))

        cur: list[str] = []
        cur_page: int | None = None
        cur_len = 0
        for text, page in paragraphs:
            if cur and cur_len + len(text) + 2 > max_chars:
                _emit(cur, cur_page, section)
                # overlap: carry the tail of the previous chunk into the next one
                tail = cur[-1][-overlap_chars:] if overlap_chars else ""
                cur = [f"…{tail}"] if tail else []
                cur_len = len(tail)
                cur_page = page
            if cur_page is None:
                cur_page = page
            cur.append(text)
            cur_len += len(text) + 2
        if cur:
            _emit(cur, cur_page, section)
        body.clear()

    def _emit(parts: list[str], page: int | None, section: str) -> None:
        text = "\n\n".join(parts).strip()
        if not text:
            return
        # a chunk's own clause id is usually only in its heading (e.g. "Rule POL-ELG-001: ..."),
        # not restated in the body, so scan the section path too
        haystack = f"{section}\n{text}"
        clauses = list(dict.fromkeys(_RULE_CODE.findall(haystack) + _CLAUSE.findall(" " + haystack)))
        idx = len(chunks)
        chunks.append(
            Chunk(
                chunk_id=_make_id(doc.source, section, idx),
                text=text,
                source=doc.source,
                title=doc.title,
                category=doc.category,
                section=section,
                page=page,
                clauses=clauses,
            )
        )

    for block in doc.blocks:
        if block.heading_level:
            flush_section()
            while heading_stack and heading_stack[-1][0] >= block.heading_level:
                heading_stack.pop()
            heading_stack.append((block.heading_level, block.text))
        else:
            body.append(block)
    flush_section()
    return chunks


def chunk_documents(docs: list[LoadedDocument], max_chars: int = 1200, overlap_chars: int = 150) -> list[Chunk]:
    out: list[Chunk] = []
    for d in docs:
        out.extend(chunk_document(d, max_chars, overlap_chars))
    return out
