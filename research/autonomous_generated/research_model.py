# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION
# autonomous-research-source-rewrite-v1; input draw sha256: dd26a11d78267c8d73925700ab88f6b246b22153f06ee12a064cf19695fdcc2c
from __future__ import annotations
from autonomous_evolution_lab import prior_probabilities
CANDIDATE_ID = '4f41e60c3029bf52dd9f'
SOURCE_STATE_SHA256 = 'ff84582bd38ac2a2864bb2a43b9a33f6490da9a5b37b70c625751138e6ecf389'
DRAW_HISTORY_SHA256 = 'dd26a11d78267c8d73925700ab88f6b246b22153f06ee12a064cf19695fdcc2c'
CONFIG = {"blend":0.25,"prior":100,"window":30}
def probability_vector(prior_history):
    # Uses history strictly BEFORE the target draw.
    return prior_probabilities(prior_history, CONFIG)
