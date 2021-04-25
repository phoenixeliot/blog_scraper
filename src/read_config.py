import os
from collections import defaultdict

import yaml
import importlib


def noop(post, *args):
    return post


def read_config(filename):
    path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "../blog_configs", filename)
    )
    config = defaultdict(
        lambda: None,
        yaml.load(open(path, encoding="utf-8").read(), Loader=yaml.FullLoader),
    )

    filename_without_ext = os.path.splitext(filename)[0]
    config_py_path = "blog_configs." + filename_without_ext

    try:
        config["rewrite_post"] = importlib.import_module(
            config_py_path, "rewrite_post"
        ).rewrite_post
    except (ModuleNotFoundError, AttributeError):
        config["rewrite_post"] = noop

    try:
        config["rewrite_toc"] = importlib.import_module(
            config_py_path, "rewrite_toc"
        ).rewrite_toc
    except (ModuleNotFoundError, AttributeError):
        config["rewrite_toc"] = noop

    try:
        config["post_filter"] = importlib.import_module(
            config_py_path, "post_filter"
        ).post_filter
    except (ModuleNotFoundError, AttributeError):
        config["post_filter"] = lambda: True

    return config
