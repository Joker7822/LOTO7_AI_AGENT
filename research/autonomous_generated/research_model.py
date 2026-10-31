# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: e05bea1debf088a52daedfc9ecb488ca7db11e273ac16f348f3fda19ac626637
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = 'c1be4e5f99273d0d3c0e'
SOURCE_STATE_SHA256 = 'b3da9b06be5ad439795eeda2a1dc29a15cf8bf1762618ef993722d9bf4702110'
DRAW_HISTORY_SHA256 = 'e05bea1debf088a52daedfc9ecb488ca7db11e273ac16f348f3fda19ac626637'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
