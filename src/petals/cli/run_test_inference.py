"""
python -m petals.cli.run_test_inference
"""
import argparse
import logging
import pprint
from typing import List, Union

import torch

from petals.utils.auto_config import AutoDistributedModelForCausalLM, AutoDistributedModelForCausalLMValidator
from transformers import AutoTokenizer
from transformers import AutoTokenizer, PreTrainedModel, PreTrainedTokenizer

logger = logging.getLogger(__name__)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# python -m petals.cli.run_test_inference 

def safe_decode(tokenizer: PreTrainedTokenizer, outputs: Union[torch.Tensor, List[int]]) -> str:
    # Workaround to make SentencePiece .decode() keep leading spaces in a token
    fake_token = tokenizer("^")["input_ids"][0]
    outputs = outputs.tolist() if isinstance(outputs, torch.Tensor) else outputs
    result = tokenizer.decode([fake_token] + outputs)

    # We use .lstrip() since SentencePiece may add leading spaces, e.g. if the outputs are "</s>"
    return result.lstrip()[1:]

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
  # model_name = "bigscience/bloom-560m"  # This one is fine-tuned Llama 2 (70B)
  # model_name = "NousResearch/Hermes-3-Llama-3.2-3B"
  model_name = "NousResearch/Llama-3.2-1B"
  
  print(model_name)
  # Connect to a distributed network hosting model layers
  tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    # add_bos_token=False, 
    # use_fast=False,
  )

  # Run the model as if it were on your computer
#   inputs = tokenizer("A cat sat", return_tensors="pt")["input_ids"]
  # inputs = tokenizer("what is 2+2?", return_tensors="pt")["input_ids"]

  inputs = "what is 2+2?"

  # inputs = "What is 9 plus 2?<|eot_id|><|start_header_id|>assistant<|end_header_id|>"

  # inputs = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>You are a helpful assistant<|eot_id|><|start_header_id|>user<|end_header_id|>What is 9 plus 2?<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
  # inputs = "What is 2 plus 2?<|eot_id|><|start_header_id|>assistant<|end_header_id|>"

  # """Client"""
  model = AutoDistributedModelForCausalLM.from_pretrained(
     model_name,
     initial_peers=['/ip4/172.18.250.110/tcp/31330/p2p/12D3KooWBF38f6Y9NE4tMUQRfQ7Yt2HS26hnqUTB88isTZF8bwLs'],
     identity_path="private_key.key"
  ).to(DEVICE)

  terminators = [
    tokenizer.eos_token_id,
    tokenizer.convert_tokens_to_ids("<|eot_id|>")
  ]
  # terminators = [
  #   tokenizer.eos_token_id,
  #   tokenizer.convert_tokens_to_ids("<|end_of_text|>")
  # ]

  extra_stop_sequences = ["\n", "\n\n", "<|end_of_text|>", "<|eot_id|>", "128009"]
  max_length = 2048
  with model.inference_session(max_length=max_length) as session:
    while True:
      inputs = tokenizer(inputs, return_tensors="pt")["input_ids"].to(DEVICE)
      n_input_tokens = inputs.shape[1]

      # cont_token = tokenizer("<|eot_id|>", return_tensors="pt")["input_ids"].to(DEVICE)
      cont_token = tokenizer("<|end_of_text|>", return_tensors="pt")["input_ids"].to(DEVICE)

      all_outputs = ""
      delta_q = []
      stop = False

      while not stop:
        outputs = model.generate(
          inputs=inputs,
          do_sample=1,
          temperature=.6,
          top_p=0.9,
          max_length=max_length,
          session=session,
          pad_token_id=tokenizer.eos_token_id,
          eos_token_id=terminators
        )
        delta = outputs[0, n_input_tokens:].tolist()
        outputs = safe_decode(tokenizer, delta_q + delta)
        inputs = None  # Inputs are passed only for the 1st token of the bot's response
        n_input_tokens = 0
        combined = all_outputs + outputs
        print("combined")
        pprint.pprint(combined)
        print("session.last_token_id", session.last_token_id)
        # if combined.endswith("<|eot_id|>") or combined.endswith("\n"):
        # if combined.endswith("<|eot_id|>"):
        #   print("combined.endswith")
        #   stop = True
        #   session.last_token_id = cont_token
        if combined.endswith("\n"):
          print("ends with it")

        if extra_stop_sequences is not None:
          for seq in extra_stop_sequences:
            if combined.endswith(seq):
              print("combined.endswith")
              stop = True
              session.last_token_id = cont_token

        if not stop and outputs[-10:].find("\ufffd") > -1:
          delta_q = delta_q + delta
        else:
          print("we in else?")
          all_outputs = combined
          token_count = len(delta_q + delta)
          delta_q = []
          print("in else", {"outputs": outputs, "stop": stop, "token_count": token_count})

        print("token_count", token_count)
        print("all_outputs")
        pprint.pprint(all_outputs)

  # with model.inference_session(max_length=512) as sess:
  #   while True:
  #       print("before user_phrase")
  #       user_phrase = input()
  #       print("len(user_phrase)", len(user_phrase))
  #       # if len(user_phrase) == 0:
  #       #   print("len(user_phrase) == 0")
  #       #   break
  #       inputs = tokenizer([inputs], return_tensors='pt')['input_ids'].to(DEVICE)
  #       while True:
  #           outputs = model.generate(
  #               inputs,
  #               temperature=.6,
  #               do_sample=True,
  #               # top_k=TOP_K,
  #               max_new_tokens=1,
  #               pad_token_id=tokenizer.eos_token_id,
  #               session=sess,
  #           )
  #           print("outputs", outputs)
  #           answer_token = tokenizer.decode(outputs[0, -1:])
  #           print("answer_token", answer_token)
  #           print(answer_token, end="", flush=True)
  #           if answer_token == "<|eot_id|>":
  #             print("answer_token == <|eot_id|>")
  #             break
  #           inputs = None

  # max_length = 512
  # with model.inference_session(max_length=max_length) as session:
  #   while True:
  #     inputs = inputs

  #     if inputs is not None:
  #       # inputs = tokenizer(inputs, return_tensors="pt")["input_ids"].to(DEVICE)
  #       inputs = tokenizer(inputs, return_tensors="pt")["input_ids"]
  #       n_input_tokens = inputs.shape[1]
  #     else:
  #       n_input_tokens = 0

  #     all_outputs = ""
  #     delta_q = []
  #     stop = False

  #     while not stop:
  #         outputs = model.generate(
  #             inputs=inputs,
  #             do_sample=1,
  #             temperature=.6,
  #             # top_k=None,
  #             # top_p=None,
  #             # repetition_penalty=None,
  #             max_length=max_length,
  #             # max_new_tokens=None,
  #             session=session,
  #             # eos_token_id=terminators,
  #             pad_token_id=tokenizer.eos_token_id
  #         )
  #         delta = outputs[0, n_input_tokens:].tolist()
  #         outputs = safe_decode(tokenizer, delta_q + delta)
  #         inputs = None  # Inputs are passed only for the 1st token of the bot's response
  #         n_input_tokens = 0
  #         combined = all_outputs + outputs
  #         pprint.pprint("pprint", combined)

  # outputs = model.generate(
  #   inputs, 
  #   # max_length=512,
  #   max_new_tokens=1,
  #   pad_token_id=tokenizer.eos_token_id
  # )

  # pprint.pprint(outputs)

  # pprint.pprint(tokenizer.decode(outputs[0])) 

  """Validator"""
#   model = AutoDistributedModelForCausalLMValidator.from_pretrained(model_name)
#   print("model", model)

#   peer_spans = [
#      {
#         'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
#         'start':0,
#         'end':1,
#      },
#       {
#         'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
#         'start':1,
#         'end':2,
#      },
#      {
#         'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
#         'start':2,
#         'end':3,
#      },
#      {
#         'peer_id':"12D3KooWByn5SC2anUgfHYiyFempbDhUyx1k9jVP7QApNC5PVCwn",
#         'start':3,
#         'end':4,
#      },
#      {
#         'peer_id':"12D3KooWGMq35p86Q4zd574hq4MyHzx7boJZ6hQcuKJF9cp3Qdhw",
#         'start':4,
#         'end':5,
#      },
#   ]

#   inference_session_data, outputs = model.generate_tensors(
#       inputs, 
#       peers=peer_spans,
#       max_new_tokens=5,
#       # cached_server_sessions=cached_server_sessions
#   )

#   print("outputs\n")
#   pprint.pprint(outputs)
#   print("inference_session_data\n")
#   pprint.pprint(inference_session_data)

#   pprint.pprint(tokenizer.decode(outputs[0]))  # A cat sat on a mat...

#   print("Running second inference sequence\n")

#   cached_server_sessions = []

#   for data in inference_session_data:
#     if data["server_idx"] == 4:
#       print("found server_idx 4")
#       cached_server_sessions.append(data)

#   print("cached_server_sessions\n")
#   pprint.pprint(cached_server_sessions)

#   inference_session_data, outputs = model.generate_tensors(
#       inputs, 
#       peers=peer_spans,
#       max_new_tokens=5,
#       cached_server_sessions=cached_server_sessions
#   )

#   print("cached_server_sessions\n")
#   print("last output\n")
#   pprint.pprint(tokenizer.decode(outputs[0]))  # A cat sat on a mat...


if __name__ == "__main__":
    main()