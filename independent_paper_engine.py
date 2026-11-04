#!/usr/bin/env python3
"""Original offline paper-to-math research adapter; no inference API.

This engine extracts only method statements *actually present* in an
open-access paper's full text, maps explicitly evidenced signal types to the
repository's sandboxed feature grammar, and proposes a bounded adaptation.
It cannot faithfully implement arbitrary algorithms or prove the paper's
original experiments were replicated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

VERSION = "independent-fulltext-rule-engine-v1"

# Every mapping is a local, documented algorithmic interpretation. No paper
# text can create a Python identifier or code fragment.
SIGNALS = (
    ("decay", (r"\bexponential(?:ly)?[- ]weight(?:ed|ing)?\b",
               r"\bexponential smoothing\b", r"\bdecay\b",
               r"\bewma\b", r"\bforgetting factor\b")),
    ("gap", (r"\btime since\b", r"\binter[- ]arrival\b",
              r"\brecency\b", r"\bwaiting time\b",
              r"\btime gap\b")),
    ("pair", (r"\bco[- ]occurrenc(?:e|es)\b", r"\bpairwise\b",
               r"\bjoint frequenc(?:y|ies)\b",
               r"\binteraction(?:s)?\b")),
    ("hot20", (r"\brecent frequenc(?:y|ies)\b", r"\bshort[- ]term frequenc(?:y|ies)\b",
                r"\bfrequency count(?:s)?\b", r"\brelative frequenc(?:y|ies)\b")),
    ("hot80", (r"\blong[- ]term frequenc(?:y|ies)\b",
                r"\blong[- ]term average\b",
                r"\bmoving average\b", r"\bhistorical average\b")),
    ("cold20", (r"\binverse frequenc(?:y|ies)\b",
                 r"\brare events?\b", r"\bunderrepresented\b")),
)

# Statements must describe a method and a combination of at least TWO
# distinct signals. A passing paper title or bibliography alone is insufficient.
METHOD = re.compile(
    r"\b(?:we propose|we present|we introduce|we combine|our method|"
    r"our algorithm|our model|the algorithm|forecasting model|"
    r"predictive model|estimator|prediction method|ensemble method|"
    r"weighted model)\b", re.I)
COMBINE = re.compile(
    r"\b(?:combine|combining|combined|aggregation|aggregate|"
    r"mixture|ensemble|weighted|jointly|joint|interaction|"
    r"integrate|integrating)\b", re.I)
INJECTION = re.compile(
    r"(?:ignore (?:all |the |previous )?instructions|"
    r"system prompt|developer message|api key|access token|"
    r"send (?:data|secrets) to)", re.I)
BREAK = re.compile(r"(?<=[.;!?])\s+")


@dataclass(frozen=True)
class Evidence:
    quote: str
    signals: tuple[str, ...]
    offset: int
    score: int


def _detected_signals(sentence: str) -> tuple[str, ...]:
    located: list[tuple[int, str]] = []
    for name, patterns in SIGNALS:
        indices = [m.start() for pattern in patterns
                   for m in re.finditer(pattern, sentence, re.I)]
        if indices:
            located.append((min(indices), name))
    return tuple(name for _, name in sorted(located))


def _quote(sentence: str) -> str:
    """Ground output in literal consecutive bytes of the normalized fulltext."""
    snippet = sentence.strip()
    if len(snippet) > 150:
        snippet = snippet[:150]
        if " " in snippet:
            snippet = snippet.rsplit(" ", 1)[0]
    return snippet


def infer_from_fulltext(text: str, paper: dict) -> dict:
    """Find a concrete supported paper method, else refuse to infer one.

    This is a deterministic extractor + algorithm-template compiler, not an
    external pretrained language model. Terms must occur in one or two
    adjacent sentences; unsupported ideas are rejected rather than invented.
    """
    if not isinstance(text, str) or len(text) < 1500:
        raise ValueError("full-text body is too short for local method analysis")
    if not isinstance(paper, dict) or not paper.get("doi"):
        raise ValueError("paper identity is required")
    sentences = [s.strip() for s in BREAK.split(text) if len(s.strip()) >= 20]
    possibilities: list[Evidence] = []
    offset = 0
    for i, s in enumerate(sentences):
        context = s
        # One sentence is preferred; a second sentence may explicitly define
        # the signals used by an immediately preceding proposed method.
        for width in (1, 2):
            if width == 2 and i + 1 < len(sentences):
                context = s + " " + sentences[i + 1]
            if INJECTION.search(context):
                continue
            signals = _detected_signals(context)
            if (len(signals) < 2 or not METHOD.search(context)
                    or not COMBINE.search(context)):
                continue
            quote = _quote(context)
            if not 20 <= len(quote) <= 150 or quote not in text:
                continue
            score = 10 * len(signals) + int(bool(re.search(
                r"\b(?:we propose|we introduce|we combine)\b", context, re.I))) * 3
            possibilities.append(Evidence(quote, signals, offset, score))
        offset += len(s) + 1

    if not possibilities:
        raise ValueError(
            "paper has no locally supported, explicitly combined algorithm "
            "features with attributable full-text evidence"
        )
    picked = sorted(possibilities, key=lambda x: (-x.score, x.offset))[0]
    # The local compiler uses a fixed, safe grammar. The coefficients are a
    # declared design choice for a lottery-domain *adaptation*, not copied
    # from the original paper or claimed as its exact empirical procedure.
    first, second = picked.signals[:2]
    expression = f"({first} + 0.5 * {second})"
    method = "Local deterministic combined-signal adaptation: " + first + " + " + second
    return {
        "method": method,
        "exact_quote": picked.quote,
        "expression": expression,
        "limitation": (
            "Offline evidence-grounded feature mapping; the 0.5 coefficient "
            "is a local adaptation, not a coefficient proven by the paper. "
            "Original publication experiments and arbitrary novel algorithms "
            "are not reproduced."
        ),
    }
