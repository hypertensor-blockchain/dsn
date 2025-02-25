import os
import platform

os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")

if platform.system() == "Darwin":
    # Necessary for forks to work properly on macOS, see https://github.com/kevlened/pytest-parallel/issues/93
    os.environ.setdefault("no_proxy", "*")
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

import hypermind
import transformers
from packaging import version

from subnet.client import *
from subnet.validator import *
from subnet.models import *
from subnet.utils import *
from subnet.utils.logging import initialize_logs as _initialize_logs

__version__ = "2.3.0.dev2"


if not os.getenv("SUBNET_IGNORE_DEPENDENCY_VERSION"):
    assert (
        version.parse("4.43.1") <= version.parse(transformers.__version__) < version.parse("4.44.0")
    ), "Please install a proper transformers version: pip install transformers>=4.43.1,<4.44.0"


def _override_bfloat16_mode_default():
    if os.getenv("USE_LEGACY_BFLOAT16") is None:
        hypermind.compression.base.USE_LEGACY_BFLOAT16 = False


_initialize_logs()
_override_bfloat16_mode_default()
