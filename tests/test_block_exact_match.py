import random

import pytest
import torch

from subnet import AutoDistributedConfig, RemoteSequential
from subnet.server.block_functions import MAX_SHORT_INFERENCE_TOKENS
from subnet.server.from_pretrained import load_pretrained_block
from test_utils import *
RTOL = 1e-03 # relative
ATOL = 8e-01 # absolute

# pytest tests/test_block_exact_match.py::test_remote_block_exact_match -rP

@pytest.mark.forked
def test_remote_block_exact_match(atol_forward=1e-4, atol_inference=1e-3):
    config = AutoDistributedConfig.from_pretrained(MODEL_NAME, initial_peers=INITIAL_PEERS)
    # remote_sequential = RemoteSequential(config)
    remote_sequential = RemoteSequential(
        config, 
        identity_path="private_key.key",
    )

    block_index = random.randint(0, config.num_hidden_layers - 1)
    remote_block = remote_sequential[block_index]

    inputs = torch.randn(1, MAX_SHORT_INFERENCE_TOKENS + 8, config.hidden_size)
    outputs_forward = remote_block(inputs)

    outputs_inference = []
    with torch.inference_mode():
        with remote_block.inference_session(max_length=inputs.shape[1]) as sess:
            # Test long inference (unmerged inference pools)
            outputs_inference.append(sess.step(inputs[:, : MAX_SHORT_INFERENCE_TOKENS + 1, :]))

            # Test short inference (merged inference pools)
            for i in range(MAX_SHORT_INFERENCE_TOKENS + 1, inputs.shape[1]):
                outputs_inference.append(sess.step(inputs[:, i : i + 1, :]))

            # test that max length is respected
            with pytest.raises(ValueError, match=r"Maximum length exceeded") as exc_info:
                sess.step(inputs[:, -1:, :])
            assert "Maximum length exceeded" in repr(exc_info.value)
    outputs_inference = torch.cat(outputs_inference, dim=1)

    ref_block = load_pretrained_block(MODEL_NAME, block_index, torch_dtype=torch.float32)
    (outputs_local,) = ref_block(inputs)

    print("outputs_local\n", outputs_local)
    print("outputs_forward\n", outputs_forward)
    print("outputs_inference\n", outputs_inference)

    outputs_local_sum = torch.sum(outputs_local)
    outputs_forward_sum = torch.sum(outputs_forward)
    outputs_inference_sum = torch.sum(outputs_inference)
    print("outputs_local_sum\n", outputs_local_sum)
    print("outputs_forward_sum\n", outputs_forward_sum)
    print("outputs_inference_sum\n", outputs_inference_sum)

    assert torch.allclose(outputs_forward, outputs_inference, rtol=RTOL, atol=ATOL) # test

    # assert torch.allclose(outputs_local, outputs_forward, rtol=0, atol=atol_forward)
    # assert torch.allclose(outputs_local, outputs_inference, rtol=0, atol=atol_inference)
