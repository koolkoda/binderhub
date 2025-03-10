import os
from collections.abc import Mapping
from functools import lru_cache
from urllib.parse import urlparse

from ruamel.yaml import YAML

yaml = YAML(typ="safe")


def _merge_dictionaries(a, b):
    """Merge two dictionaries recursively.

    Simplified From https://stackoverflow.com/a/7205107
    """
    merged = a.copy()
    for key in b:
        if key in a:
            if isinstance(a[key], Mapping) and isinstance(b[key], Mapping):
                merged[key] = _merge_dictionaries(a[key], b[key])
            else:
                merged[key] = b[key]
        else:
            merged[key] = b[key]
    return merged


# memoize so we only load config once
@lru_cache()
def _load_values():
    """Load configuration from disk

    Memoized to only load once
    """
    cfg = {}
    for source in ("config", "secret"):
        path = f"/etc/binderhub/{source}/values.yaml"
        if os.path.exists(path):
            print(f"Loading {path}")
            with open(path) as f:
                values = yaml.load(f)
            cfg = _merge_dictionaries(cfg, values)
        else:
            print(f"No config at {path}")
    return cfg


def get_value(key, default=None):
    """
    Find an item in values.yaml of a given name & return it

    get_value("a.b.c") returns values['a']['b']['c']
    """
    # start at the top
    value = _load_values()
    # resolve path in yaml
    for level in key.split("."):
        if not isinstance(value, dict):
            # a parent is a scalar or null,
            # can't resolve full path
            return default
        if level not in value:
            return default
        else:
            value = value[level]
    return value


# load config from values.yaml
for section, sub_cfg in get_value("config", {}).items():
    c[section].update(sub_cfg)

if get_value("dind.enabled", False) and get_value("dind.hostSocketDir"):
    c.BinderHub.build_docker_host = "unix://{}/docker.sock".format(
        get_value("dind.hostSocketDir")
    )


if c.BinderHub.auth_enabled:
    hub_url = urlparse(c.BinderHub.hub_url)
    c.HubOAuth.hub_host = f"{hub_url.scheme}://{hub_url.netloc}"
    if "base_url" in c.BinderHub:
        c.HubOAuth.base_url = c.BinderHub.base_url

# load extra config snippets
for key, snippet in sorted((get_value("extraConfig") or {}).items()):
    print(f"Loading extra config: {key}")
    exec(snippet)
