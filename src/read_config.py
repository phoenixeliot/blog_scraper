import os
from collections import defaultdict

import yaml
import importlib


def read_config(filename):
    path = os.path.realpath(os.path.join(
        os.path.dirname(__file__), '../blog_configs', filename))
    config = defaultdict(lambda: None, yaml.load(
        open(path, encoding='utf-8').read(), Loader=yaml.FullLoader))

    filename_without_ext = os.path.splitext(filename)[0]

    config_py_path = 'blog_configs.' + filename_without_ext

    try:
        config['rewrite_post'] = importlib.import_module(
            config_py_path, 'rewrite_post').rewrite_post
    except (ModuleNotFoundError, AttributeError):
        config['rewrite_post'] = lambda x: x

    try:
        config['rewrite_toc'] = importlib.import_module(
            config_py_path, 'rewrite_toc').rewrite_toc
    except (ModuleNotFoundError, AttributeError):
        config['rewrite_toc'] = lambda x: x

    return config
