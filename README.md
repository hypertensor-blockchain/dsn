<p align="center">
    <h1>Hypertensor Subnet LLM Template</h1>
    An incentivized intelligence template for running P2P large language models within the Hypertensor network with a POI (Proof of Inference) consensus mechanism, and POS (Proof of Stake) consensus mechanism.
    <br><br>
    <a href="https://www.hypertensor.org" target="_blank">Read the whitepaper</a>
</p>
<hr/>

<a href="https://docs.hypertensor.org" target="_blank">Read the full documentation</a> to start an incentivized subnet validator node.

<h4>Getting Started</h4>

- Clone repository
- Create an `.env` file in the root directory by copying `.env.example` and fill in the variables.
- Add virtual environment (optional):
    - `python -m venv .venv`
    - `source .venv/bin/activate`
- Install: `python -m pip install .`
- Generate RSA private key (Optional): `openssl genpkey -algorithm RSA -out private_key.key -pkeyopt rsa_keygen_bits:2048`

<h4>Basic Usage</h4>

Start your own subnet:

```bash
python -m petals.cli.run_server_validator bigscience/bloom-560m --host_maddrs /ip4/0.0.0.0/tcp/{PORT} ip4/0.0.0.0/udp/{PORT}/quic --announce_maddrs ip4/{IP}/tcp/{PORT}/ip4/{IP}/udp/{PORT}/quic --new_swarm
```

Start your own subnet validator node:

```bash
python -m petals.cli.run_server_validator bigscience/bloom-560m --public_ip {IP} --port {PORT} --initial_peers {INITIAL_PEERS}
```
Instead of using `--initial_peers`, the `constants.py` file can be updated to include them. Read the full documentation or the `cli` directory for all available arguments.

<hr>

Generate text with distributed **Llama 3.1** (up to 405B), **Mixtral** (8x22B), **Falcon** (40B+) or **BLOOM** (176B) and fine‑tune them for your own tasks &mdash; right from your desktop computer or Google Colab:

```python
from transformers import AutoTokenizer
from petals import AutoDistributedModelForCausalLM

# Choose any model available at https://health.petals.dev
model_name = "meta-llama/Meta-Llama-3.1-405B-Instruct"

# Connect to a distributed network hosting model layers
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoDistributedModelForCausalLM.from_pretrained(model_name)

# Run the model as if it were on your computer
inputs = tokenizer("A cat sat", return_tensors="pt")["input_ids"]
outputs = model.generate(inputs, max_new_tokens=5)
print(tokenizer.decode(outputs[0]))  # A cat sat on a mat...
```