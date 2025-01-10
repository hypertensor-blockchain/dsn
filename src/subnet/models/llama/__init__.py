from subnet.models.llama.block import WrappedLlamaBlock
from subnet.models.llama.config import DistributedLlamaConfig
from subnet.models.llama.model import (
    DistributedLlamaForCausalLM,
    DistributedLlamaForCausalLMValidator,
    DistributedLlamaForSequenceClassification,
    DistributedLlamaModel,
)
from subnet.models.llama.speculative_model import DistributedLlamaForSpeculativeGeneration
from subnet.utils.auto_config import register_model_classes

register_model_classes(
    config=DistributedLlamaConfig,
    model=DistributedLlamaModel,
    model_for_causal_lm=DistributedLlamaForCausalLM,
    model_for_speculative=DistributedLlamaForSpeculativeGeneration,
    model_for_causal_lm_validator=DistributedLlamaForCausalLMValidator,
    model_for_sequence_classification=DistributedLlamaForSequenceClassification,
)
