#!/usr/bin/env python

import configparser as cnfg

from click.utils import echo
from pathlib import Path
from typing import Optional

# Set up default configuation
defaults = cnfg.ConfigParser()
defaults.read(str(Path(__file__).parent.parent / "resources" / "default.config"))


def get_param(user_config: Optional[cnfg.ConfigParser], section: str, param: str,
              cli_val: Optional[str], format: str = 'float'):
    """
    get a parameter in the user config

    :param user_config: user configuration dictionary
    :param section: section in config file
    :param param: parameter name
    :param cli_val: value from command line interface
    :param format: format of the parameter (float, int, bool, str)
    :return: parameter value
    """
    if cli_val is not None:
        # return CLI value if entered
        return cli_val
    elif user_config is not None:
        cfg = user_config
        # check if parameter is in user config and use default if it's not
        try:
            if user_config[section][param] == "None":
                return None
        except Exception:
            pass
    # use default values if no CLI and no user config
    try:
        if defaults[section][param] == "None":
            return None
        else:
            cfg = defaults
    except Exception:
        return None

    if format == 'float':
        return float(cfg[section][param])
    elif format == 'int':
        return int(cfg[section][param])
    elif format == 'bool':
        return cfg[section].getboolean(param)
    else:
        return cfg[section][param]
