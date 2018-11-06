import os
from collections import defaultdict

import yaml


def read_config(filename):
    path = os.path.join(os.path.dirname(__file__), '../blog_configs', filename)
    config = defaultdict(lambda: None, yaml.load(open(path)))
    return config

