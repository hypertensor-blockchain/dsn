"""
python -m petals.cli.run_test_inference
"""
import argparse
import logging
import pprint

from petals.utils.auto_config import AutoDistributedModelForCausalLM, AutoDistributedModelForCausalLMValidator
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

def main():
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      "--peer",
      nargs="*",
      help="Multiaddrs of the peers that will welcome you into the existing DHT. "
      "Example: /ip4/203.0.113.1/tcp/31337/p2p/XXXX /ip4/203.0.113.2/tcp/7777/p2p/YYYY",
  )
  args = parser.parse_args()

  # Choose any model available at dashboard.hypertensor.org
  model_name = "bigscience/bloom-560m"  # This one is fine-tuned Llama 2 (70B)
  
  print(model_name)
  # Connect to a distributed network hosting model layers
  tokenizer = AutoTokenizer.from_pretrained(model_name)
  print("tokenizer", tokenizer)

  # Run the model as if it were on your computer
  inputs = tokenizer("A cat sat", return_tensors="pt")["input_ids"]

  # """Client"""
  # model = AutoDistributedModelForCausalLM.from_pretrained(model_name)
  # print("model", model)

  # outputs = model.generate(inputs, max_new_tokens=5)

  # pprint.pprint(tokenizer.decode(outputs[0])) 

  """Validator"""
  model = AutoDistributedModelForCausalLMValidator.from_pretrained(model_name)
  print("model", model)

  peer_spans = [
     {
        'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
        'start':0,
        'end':1,
     },
      {
        'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
        'start':1,
        'end':2,
     },
     {
        'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
        'start':2,
        'end':3,
     },
     {
        'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
        'start':3,
        'end':4,
     },
     {
        'peer_id':"12D3KooWGMq35p86Q4zd574hq4MyHzx7boJZ6hQcuKJF9cp3Qdhw",
        'start':4,
        'end':5,
     },
  ]

  inference_session_data, outputs = model.generate_tensors(
      inputs, 
      peers=peer_spans,
      max_new_tokens=5,
      # cached_server_sessions=cached_server_sessions
  )

  print("outputs\n")
  pprint.pprint(outputs)
  print("inference_session_data\n")
  pprint.pprint(inference_session_data)

  pprint.pprint(tokenizer.decode(outputs[0]))  # A cat sat on a mat...

  print("Running second inference sequence\n")

  cached_server_sessions = []

  for data in inference_session_data:
    if data["server_idx"] == 4:
      print("found server_idx 4")
      cached_server_sessions.append(data)

  print("cached_server_sessions\n")
  pprint.pprint(cached_server_sessions)

  inference_session_data, outputs = model.generate_tensors(
      inputs, 
      peers=peer_spans,
      max_new_tokens=5,
      cached_server_sessions=cached_server_sessions
  )

  print("cached_server_sessions\n")
  print("last output\n")
  pprint.pprint(tokenizer.decode(outputs[0]))  # A cat sat on a mat...


if __name__ == "__main__":
    main()