# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: 9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '817a89de13a12ffa46d2'
SOURCE_STATE_SHA256 = '58e7cde5e685a3c821f7aa012a860ad7c195fc84727d9230df7deb3f41ce114a'
DRAW_HISTORY_SHA256 = '9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
