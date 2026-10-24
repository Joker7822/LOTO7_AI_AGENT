"""AUTO-GENERATED RESEARCH MODEL. NOT PRODUCTION. DO NOT IMPORT IN OOS."""
import json
from open_ended_evolution_agent import inclusion
GENERATION = 1820
GENOME = json.loads('{"op":"frequency","prior":443.61324,"window":35}')
def predict_inclusion_probability(prior_history):
    return inclusion(prior_history, GENOME)
