# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: 9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '817a89de13a12ffa46d2'
SOURCE_STATE_SHA256 = 'b77c3208f6d518da6b8abf18b043d6a6c180d7c3eb53af443499e2e64361d630'
DRAW_HISTORY_SHA256 = '9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
