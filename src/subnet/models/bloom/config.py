import os
from typing import Optional, Union

from hypermind import get_logger
from transformers.models.bloom import BloomConfig
from transformers.models.bloom.modeling_bloom import BloomAttention

from subnet.client.config import ClientConfig
from subnet.client.lm_head import LMHeadConfig
from subnet.client.ptune import PTuneConfig

from subnet.validator.config import ClientConfig as ClientConfigValidator
from subnet.validator.lm_head import LMHeadConfig as LMHeadConfigValidator
from subnet.validator.ptune import PTuneConfig as PTuneConfigValidator

from subnet.models.bloom.block import WrappedBloomBlock, WrappedBloomBlockValidator

logger = get_logger(__name__)


class DistributedBloomConfig(BloomConfig, ClientConfig, PTuneConfig, LMHeadConfig):
    block_class = WrappedBloomBlock
    attn_class = BloomAttention
    block_prefix = "h"

    num_key_value_groups = 1

    @classmethod
    def from_pretrained(
        cls, model_name_or_path: Union[str, os.PathLike, None], *args, dht_prefix: Optional[str] = None, **kwargs
    ):
        logger.info("Make sure you follow the BLOOM terms of use: https://bit.ly/bloom-license")

        loading_from_repo = model_name_or_path is not None and not os.path.isdir(model_name_or_path)
        if loading_from_repo and dht_prefix is None:
            # We need "-petals" for backward compatibility with Petals < 1.2.0
            dht_prefix = str(model_name_or_path) + "-petals"
            dht_prefix = dht_prefix.replace(".", "-")
            logger.info(f"Using DHT prefix: {dht_prefix}")
        return super().from_pretrained(model_name_or_path, *args, dht_prefix=dht_prefix, **kwargs)

"""
VALIDATOR
"""
class DistributedBloomConfigValidator(BloomConfig, ClientConfigValidator, PTuneConfigValidator, LMHeadConfigValidator):
    block_class = WrappedBloomBlockValidator
    attn_class = BloomAttention
    block_prefix = "h"

    num_key_value_groups = 1

    @classmethod
    def from_pretrained(
        cls, model_name_or_path: Union[str, os.PathLike, None], *args, dht_prefix: Optional[str] = None, **kwargs
    ):
        # Called from _AutoDistributedBase
        logger.info("Make sure you follow the BLOOM terms of use: https://bit.ly/bloom-license")

        loading_from_repo = model_name_or_path is not None and not os.path.isdir(model_name_or_path)
        if loading_from_repo and dht_prefix is None:
            # We need "-petals" for backward compatibility with Petals < 1.2.0
            dht_prefix = str(model_name_or_path) + "-petals"
            dht_prefix = dht_prefix.replace(".", "-")
            logger.info(f"Using DHT prefix: {dht_prefix}")
        return super().from_pretrained(model_name_or_path, *args, dht_prefix=dht_prefix, **kwargs)
