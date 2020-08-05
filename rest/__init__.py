import logging


__version__ = "0.0.1"
__license__ = "MIT"


logger = logging.getLogger('restj')

from .api import API            # noqa
from .endpoint import Endpoint  # noqa
from .exceptions import *       # noqa
