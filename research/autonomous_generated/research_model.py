# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: fa6ee78c6350e9b979597107a8650dae16399f91fba0d1c22149d4717e3116d6
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '3f16bdf7f2ea9003ae09'
SOURCE_STATE_SHA256 = '36c2cdf33f4693cb7a27214ff18205641bfc9e1784a5447395d58b8a95f1810a'
DRAW_HISTORY_SHA256 = 'fa6ee78c6350e9b979597107a8650dae16399f91fba0d1c22149d4717e3116d6'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
