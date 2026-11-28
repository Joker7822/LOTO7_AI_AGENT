# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: 59aa4f632d8bd05225e7bbaa3d98c6d97c39fedc0dd14ff4b647bd963c7072b6
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '958fe580821cb7c5142b'
SOURCE_STATE_SHA256 = 'ac65eb4bf540c0bb3e325789d5f549d3d654a8b7f0c462e5643f4f0a2e585627'
DRAW_HISTORY_SHA256 = '59aa4f632d8bd05225e7bbaa3d98c6d97c39fedc0dd14ff4b647bd963c7072b6'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
