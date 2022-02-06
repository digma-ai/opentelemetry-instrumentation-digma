import importlib
import logging
import os
from typing import Optional

from conf.environment_variables import DIGMA_CONFIG_MODULE, PROJECT_ROOT

logger = logging.getLogger(__name__)


class LazyConfig:
    _wrapped_config = None

    def _setup(self):
        config_module = os.environ.get(DIGMA_CONFIG_MODULE)
        if not config_module:
            raise ValueError(f'{DIGMA_CONFIG_MODULE} env must be set')
        self._wrapped_config = Config(config_module)

    def __getattr__(self, name):
        if self._wrapped_config is None:
            self._setup()

        val = getattr(self._wrapped_config, name)
        self.__dict__[name] = val
        return val


class Config:
    def __init__(self, settings_module: str):
        try:
            module = importlib.import_module(settings_module)
            for field in dir(module):
                if field.isupper():
                    val = getattr(module, field)
                    setattr(self, field, val)
        except ModuleNotFoundError:
            logger.error(f"""Couldn't import DIGMA_CONFIG_MODULE: '{settings_module}'.
            Are you sure it's installed and available on your PYTHONPATH env?
            Did you forget to activate a virtual environment""")
            raise


config = LazyConfig()


def try_get_project_root() -> Optional[str]:
    try:
        if PROJECT_ROOT in os.environ:
            project_root = os.environ.get(PROJECT_ROOT)
        else:
            project_root = config.PROJECT_ROOT
        return project_root
    except Exception as e:
        logger.exception(e)
        return None
