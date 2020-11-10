from pathlib import Path
from typing import Union

import pytest
import yaml
from copier.main import copy
from plumbum import local
from plumbum.cmd import docker_compose
