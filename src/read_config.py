import os
from collections import defaultdict

import yaml
import importlib

def read_config(filename):
    path = os.path.join(os.path.dirname(__file__), '../blog_configs', filename)
    config = defaultdict(lambda: None, yaml.load(open(path, encoding='utf-8').read()))

    filename_without_ext = os.path.splitext(filename)[0]

    try:
        config_py_path = 'blog_configs.' + filename_without_ext
        rewrite_post = importlib.import_module(config_py_path, 'rewrite_post').rewrite_post
        config['rewrite_post'] = rewrite_post
    except Exception as e:
        config['rewrite_post'] = (lambda: None)

    return config

