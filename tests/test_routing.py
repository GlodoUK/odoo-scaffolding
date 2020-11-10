import time
import uuid
from pathlib import Path

import pytest
import requests
from copier import copy
from packaging import version
from plumbum import local
from plumbum.cmd import docker_compose
