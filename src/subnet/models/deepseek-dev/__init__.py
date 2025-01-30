"""STILL IN DEVELOPMENT - THIS DOES NOT WORK - UNTESTED"""
from subnet.models.deepseek_r1.block import DeepSeekR1WrappedBlock
from subnet.models.deepseek_r1.config import DeepSeekR1Config
from subnet.models.deepseek_r1.model import (
    DeepSeekR1DistributedModel,
)
from subnet.utils.auto_config import register_model_classes

register_model_classes(
    config=DeepSeekR1Config,
    model=DeepSeekR1DistributedModel,
    model_for_causal_lm=DeepSeekR1DistributedModel,
    model_for_causal_lm_validator=DeepSeekR1DistributedModel,
    model_for_sequence_classification=None,
)
