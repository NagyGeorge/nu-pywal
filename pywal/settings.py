"""
                                      '||
... ...  .... ... ... ... ...  ....    ||
 ||'  ||  '|.  |   ||  ||  |  '' .||   ||
 ||    |   '|.|     ||| |||   .|' ||   ||
 ||...'     '|       |   |    '|..'|' .||.
 ||      .. |
''''      ''
Created by Dylan Araps.
"""

import os
import platform

__version__: str = "0.9.1"
__cache_version__: str = "1.1.0"


HOME: str = os.getenv("HOME") or os.getenv("USERPROFILE") or os.path.expanduser("~")
XDG_CACHE_DIR: str = os.getenv("XDG_CACHE_HOME", os.path.join(HOME, ".cache"))
XDG_CONF_DIR: str = os.getenv("XDG_CONFIG_HOME", os.path.join(HOME, ".config"))

CACHE_DIR: str = os.getenv("PYWAL_CACHE_DIR", os.path.join(XDG_CACHE_DIR, "wal"))
CONF_DIR: str = os.path.join(XDG_CONF_DIR, "wal")
MODULE_DIR: str = os.path.dirname(__file__)

OS: str = platform.uname()[0]
