from typing import Optional
from urllib.parse import urlparse

import subnet
import pydantic.v1 as pydantic


@pydantic.dataclasses.dataclass
class ModelInfo(subnet.data_structures.ModelInfo):
    dht_prefix: Optional[str] = None
    official: bool = True
    limited: bool = False

    @property
    def name(self) -> str:
        return urlparse(self.repository).path.lstrip("/")

    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1]
