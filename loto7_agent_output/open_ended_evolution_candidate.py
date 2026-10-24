"""AUTO-GENERATED RESEARCH MODEL. NOT PRODUCTION. DO NOT IMPORT IN OOS."""
import json
from open_ended_evolution_agent import inclusion
GENERATION = 3823
GENOME = json.loads('{"alpha":0.10065,"left":{"child":{"op":"frequency","prior":23.25951,"window":26},"exponent":2.32582,"op":"power"},"op":"blend","right":{"op":"uniform"}}')
def predict_inclusion_probability(prior_history):
    return inclusion(prior_history, GENOME)
