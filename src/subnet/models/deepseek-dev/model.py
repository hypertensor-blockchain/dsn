# models/deepseek_r1/model.py

import torch
import torch.nn as nn
from petals.client import RemoteSequential
from petals.utils.packaging import pack_args_kwargs, unpack_args_kwargs
from .config import DeepSeekR1Config
from .block import DeepSeekR1WrappedBlock

class DeepSeekR1Model(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config

        # Embedding layers
        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)
        self.embed_positions = nn.Embedding(config.max_position_embeddings, config.hidden_size)

        # Final layer norm
        self.final_layer_norm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        """Initialize the weights."""
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)

    def forward(self, input_ids, attention_mask=None):
        # Get input embeddings
        batch_size, seq_length = input_ids.shape
        position_ids = torch.arange(seq_length, dtype=torch.long, device=input_ids.device).unsqueeze(0)

        input_embeds = self.embed_tokens(input_ids)
        position_embeds = self.embed_positions(position_ids)
        hidden_states = input_embeds + position_embeds

        # Apply final layer norm
        hidden_states = self.final_layer_norm(hidden_states)

        return hidden_states


class DeepSeekR1DistributedModel(nn.Module):
    """
    Distributed version of DeepSeekR1Model for Petals' P2P infrastructure.
    """

    def __init__(self, config, dht=None, initial_peers=None):
        super().__init__()
        self.config = config

        # Embedding layers (executed locally)
        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)
        self.embed_positions = nn.Embedding(config.max_position_embeddings, config.hidden_size)

        # Distributed transformer blocks (executed remotely)
        self.transformer_blocks = RemoteSequential(
            config,
            block_specs=[DeepSeekR1WrappedBlock(config, layer_idx=i) for i in range(config.num_hidden_layers)],
            dht=dht,
            initial_peers=initial_peers,
        )

        # Final layer norm (executed locally)
        self.final_layer_norm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        """Initialize the weights."""
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)

    def forward(self, input_ids, attention_mask=None):
        # Get input embeddings (executed locally)
        batch_size, seq_length = input_ids.shape
        position_ids = torch.arange(seq_length, dtype=torch.long, device=input_ids.device).unsqueeze(0)

        input_embeds = self.embed_tokens(input_ids)
        position_embeds = self.embed_positions(position_ids)
        hidden_states = input_embeds + position_embeds

        # Apply distributed transformer blocks (executed remotely)
        hidden_states = self.transformer_blocks(hidden_states, attention_mask)

        # Apply final layer norm (executed locally)
        hidden_states = self.final_layer_norm(hidden_states)

        return hidden_states