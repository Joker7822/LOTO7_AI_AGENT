# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: ca6c245500134f8d843d0604cf5fe777d8a7c3338fdf287bc71c415beece2960
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '67373f0ae84e54d99d84'
SOURCE_STATE_SHA256 = 'ba7bc90387bbd38217af0721767b76de0581d8b237d394635e297e03280b609a'
DRAW_HISTORY_SHA256 = 'ca6c245500134f8d843d0604cf5fe777d8a7c3338fdf287bc71c415beece2960'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
