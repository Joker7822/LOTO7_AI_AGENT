"""AUTO-GENERATED RESEARCH MODEL. NOT PRODUCTION. DO NOT IMPORT IN OOS."""
import json
from open_ended_evolution_agent import inclusion
GENERATION = 57752
GENOME = json.loads('{"alpha":0.99,"left":{"alpha":0.65489,"left":{"alpha":0.19977,"left":{"alpha":0.74645,"left":{"op":"gap","scale":41.98272},"op":"blend","right":{"child":{"child":{"half_life":13.58362,"op":"decay"},"exponent":2.30693,"op":"power"},"exponent":2.16673,"op":"power"}},"op":"blend","right":{"alpha":0.12536,"left":{"alpha":0.24202,"left":{"alpha":0.86498,"left":{"half_life":122.33941,"op":"decay"},"op":"blend","right":{"half_life":101.4379,"op":"decay"}},"op":"blend","right":{"alpha":0.07882,"left":{"op":"uniform"},"op":"blend","right":{"op":"frequency","prior":25.85091,"window":37}}},"op":"blend","right":{"alpha":0.66082,"left":{"child":{"op":"uniform"},"exponent":1.77195,"op":"power"},"op":"blend","right":{"alpha":0.1953,"left":{"op":"pair","prior":194.89904,"window":214},"op":"blend","right":{"op":"uniform"}}}}},"op":"blend","right":{"op":"uniform"}},"op":"blend","right":{"alpha":0.36933,"left":{"op":"uniform"},"op":"blend","right":{"child":{"op":"gap","scale":6.79959},"exponent":1.42997,"op":"power"}}}')
def predict_inclusion_probability(prior_history):
    return inclusion(prior_history, GENOME)
