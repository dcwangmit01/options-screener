import logging
import os
import re

from app import utils

log = logging.getLogger(__name__)


class App(object):
    _singleton = dict()

    _jinja_dict = None

    def __init__(self):
        # Return a singleton
        self.__dict__ = App._singleton

    def get_config_dict(self, ctx, list_of_files=[], initial_dict={}):
        # Manually cache, since memoization doesn't work with dict values
        if App._jinja_dict is not None:
            return App._jinja_dict

        d = initial_dict

        # Make all environment variables starting with 'OPTIONS_'
        # accessible from the dict.
        for k, v in os.environ.items():
            if k.startswith('OPTIONS_'):
                if 'env' not in d:
                    d['env'] = {}
                d['env'][k] = v

        # Add the config files as part of the dict
        for filename in list_of_files:
            m = re.match("^(.*)\.yaml$", filename)
            assert m is not None, (
                "Unable to parse config base name from file {}".format(
                    filename))
            key = m.group(1)
            d[key] = utils.YamlUtils.yaml_dict_from_file(
                os.path.join(ctx.home, filename))

        # Render values containing nested jinja variables
        r = utils.JinjaUtils.dict_self_render(d)

        # Set the cache
        App._jinja_dict = r
        return r
