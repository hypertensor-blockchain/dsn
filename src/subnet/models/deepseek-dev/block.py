# models/deepseek_r1/block.py

import torch
import torch.nn as nn
from petals.utils.packaging import pack_args_kwargs, unpack_args_kwargs

class DeepSeekR1TransformerLayer(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.attention = DeepSeekR1Attention(config)
        self.intermediate = DeepSeekR1Intermediate(config)
        self.output = DeepSeekR1Output(config)
        self.layer_norm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, hidden_states, attention_mask=None):
        # Self-attention
        attention_output = self.attention(hidden_states, attention_mask)
        attention_output = self.dropout(attention_output)
        hidden_states = self.layer_norm(hidden_states + attention_output)

        # Feed-forward network
        intermediate_output = self.intermediate(hidden_states)
        layer_output = self.output(intermediate_output, hidden_states)
        layer_output = self.dropout(layer_output)
        hidden_states = self.layer_norm(hidden_states + layer_output)

        return hidden_states


class DeepSeekR1Attention(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.num_attention_heads = config.num_attention_heads
        self.attention_head_size = config.hidden_size // config.num_attention_heads
        self.all_head_size = self.num_attention_heads * self.attention_head_size

        self.query = nn.Linear(config.hidden_size, self.all_head_size)
        self.key = nn.Linear(config.hidden_size, self.all_head_size)
        self.value = nn.Linear(config.hidden_size, self.all_head_size)

        self.dropout = nn.Dropout(config.attention_probs_dropout_prob)

    def forward(self, hidden_states, attention_mask=None):
        # Compute Q, K, V
        query = self.query(hidden_states)
        key = self.key(hidden_states)
        value = self.value(hidden_states)

        # Reshape and transpose for multi-head attention
        query = query.view(query.size(0), -1, self.num_attention_heads, self.attention_head_size).transpose(1, 2)
        key = key.view(key.size(0), -1, self.num_attention_heads, self.attention_head_size).transpose(1, 2)
        value = value.view(value.size(0), -1, self.num_attention_heads, self.attention_head_size).transpose(1, 2)

        # Scaled dot-product attention
        attention_scores = torch.matmul(query, key.transpose(-1, -2)) / torch.sqrt(torch.tensor(self.attention_head_size, dtype=torch.float32))
        if attention_mask is not None:
            attention_scores = attention_scores + attention_mask

        attention_probs = nn.functional.softmax(attention_scores, dim=-1)
        attention_probs = self.dropout(attention_probs)

        context = torch.matmul(attention_probs, value)
        context = context.transpose(1, 2).contiguous().view(context.size(0), -1, self.all_head_size)

        return context


class DeepSeekR1Intermediate(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.intermediate_size)
        self.intermediate_act_fn = nn.GELU()  # Assuming GELU activation

    def forward(self, hidden_states):
        hidden_states = self.dense(hidden_states)
        hidden_states = self.intermediate_act_fn(hidden_states)
        return hidden_states


class DeepSeekR1Output(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.intermediate_size, config.hidden_size)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, hidden_states, input_tensor):
        hidden_states = self.dense(hidden_states)
        hidden_states = self.dropout(hidden_states)
        return hidden_states


class DeepSeekR1WrappedBlock(nn.Module):
    """
    Wrapper for DeepSeekR1TransformerLayer to make it compatible with Petals' distributed inference.
    """

    def __init__(self, config, layer_idx):
        super().__init__()
        self.layer = DeepSeekR1TransformerLayer(config)
        self.layer_idx = layer_idx

    def forward(self, *args, **kwargs):
        # Unpack inputs (hidden_states, attention_mask, etc.)
        hidden_states, attention_mask = unpack_args_kwargs(args, kwargs)

        # Forward pass through the transformer layer
        hidden_states = self.layer(hidden_states, attention_mask)

        # Pack outputs for Petals
        outputs = pack_args_kwargs(hidden_states)
        return outputs