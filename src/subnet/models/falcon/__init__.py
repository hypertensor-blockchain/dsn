from subnet.models.falcon.block import WrappedFalconBlock
from subnet.models.falcon.config import DistributedFalconConfig
from subnet.models.falcon.model import (
    DistributedFalconForCausalLM,
    DistributedFalconForSequenceClassification,
    DistributedFalconModel,
)
from subnet.utils.auto_config import register_model_classes

register_model_classes(
    config=DistributedFalconConfig,
    model=DistributedFalconModel,
    model_for_causal_lm=DistributedFalconForCausalLM,
    model_for_sequence_classification=DistributedFalconForSequenceClassification,
)
