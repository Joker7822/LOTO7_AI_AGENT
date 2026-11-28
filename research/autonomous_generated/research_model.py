# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: 59aa4f632d8bd05225e7bbaa3d98c6d97c39fedc0dd14ff4b647bd963c7072b6
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '958fe580821cb7c5142b'
SOURCE_STATE_SHA256 = '2e72a7200e4da10ab81a96123e7a26db6195f658a9526fe41fa8ead3ba7cfcfb'
DRAW_HISTORY_SHA256 = '59aa4f632d8bd05225e7bbaa3d98c6d97c39fedc0dd14ff4b647bd963c7072b6'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
