# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: e05bea1debf088a52daedfc9ecb488ca7db11e273ac16f348f3fda19ac626637
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '1de01f1f105567e0ae6f'
SOURCE_STATE_SHA256 = '98273b53e82c3642d022951ef88be634135d4a4a66b05b50877169a832a1aa66'
DRAW_HISTORY_SHA256 = 'e05bea1debf088a52daedfc9ecb488ca7db11e273ac16f348f3fda19ac626637'
CONFIG = {"blend":0.5,"prior":300,"window":140}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
