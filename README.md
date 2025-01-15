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
- Generate Ed25519 private key (Required for validator node): `python -m subnet.cli.crypto.keygen`

<h4>Basic Usage</h4>

Start your own subnet:

```bash
python -m subnet.cli.run_server_validator bigscience/bloom-560m --host_maddrs /ip4/0.0.0.0/tcp/{PORT} ip4/0.0.0.0/udp/{PORT}/quic --announce_maddrs ip4/{IP}/tcp/{PORT}/ip4/{IP}/udp/{PORT}/quic --identity_path {PRIVATE_KEY_PATH} --new_swarm
```

Start your own subnet validator node:

```bash
python -m subnet.cli.run_server_validator bigscience/bloom-560m --public_ip {IP} --port {PORT} --initial_peers {INITIAL_PEERS} --identity_path {PRIVATE_KEY_PATH}
```
Instead of using `--initial_peers`, the `constants.py` file can be updated to include them. Read the full documentation or the `cli` directory for all available arguments.