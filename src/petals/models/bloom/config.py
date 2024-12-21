import os
from typing import Optional, Union

from hivemind import get_logger
from transformers.models.bloom import BloomConfig
from transformers.models.bloom.modeling_bloom import BloomAttention

from petals.client.config import ClientConfig
from petals.client.lm_head import LMHeadConfig
from petals.client.ptune import PTuneConfig

from petals.validator.config import ClientConfig as ClientConfigValidator
from petals.validator.lm_head import LMHeadConfig as LMHeadConfigValidator
from petals.validator.ptune import PTuneConfig as PTuneConfigValidator

from petals.models.bloom.block import WrappedBloomBlock, WrappedBloomBlockValidator

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
        print("DistributedBloomConfig model_name_or_path", model_name_or_path)
        print("DistributedBloomConfig args", args)
        print("DistributedBloomConfig kwargs", kwargs)

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
    print("DistributedBloomConfigValidator")
    block_class = WrappedBloomBlockValidator
    attn_class = BloomAttention
    block_prefix = "h"

    num_key_value_groups = 1

    @classmethod
    def from_pretrained(
        cls, model_name_or_path: Union[str, os.PathLike, None], *args, dht_prefix: Optional[str] = None, **kwargs
    ):
        # Called from _AutoDistributedBase
        print("DistributedBloomConfigValidator model_name_or_path", model_name_or_path)
        print("DistributedBloomConfigValidator args", args)
        print("DistributedBloomConfigValidator kwargs", kwargs)

        logger.info("Make sure you follow the BLOOM terms of use: https://bit.ly/bloom-license")

        loading_from_repo = model_name_or_path is not None and not os.path.isdir(model_name_or_path)
        if loading_from_repo and dht_prefix is None:
            # We need "-petals" for backward compatibility with Petals < 1.2.0
            dht_prefix = str(model_name_or_path) + "-petals"
            dht_prefix = dht_prefix.replace(".", "-")
            logger.info(f"Using DHT prefix: {dht_prefix}")
        return super().from_pretrained(model_name_or_path, *args, dht_prefix=dht_prefix, **kwargs)
