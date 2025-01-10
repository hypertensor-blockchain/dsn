from subnet.models.bloom.block import WrappedBloomBlock
from subnet.models.bloom.config import DistributedBloomConfig
from subnet.models.bloom.model import (
    DistributedBloomForCausalLM,
    DistributedBloomForCausalLMValidator,
    DistributedBloomForSequenceClassification,
    DistributedBloomModel,
)
from subnet.utils.auto_config import register_model_classes

register_model_classes(
    config=DistributedBloomConfig,
    model=DistributedBloomModel,
    model_for_causal_lm=DistributedBloomForCausalLM,
    model_for_causal_lm_validator=DistributedBloomForCausalLMValidator,
    model_for_sequence_classification=DistributedBloomForSequenceClassification,
)
