import importlib
import os

DIGMA_CONFIG_MODULE = 'DIGMA_CONFIG_MODULE'


class LazyConfig:
    _wrapped_config = None

    def _setup(self):
        config_module = os.environ.get(DIGMA_CONFIG_MODULE)
        if not config_module:
            raise ValueError(f'{DIGMA_CONFIG_MODULE} env must be set')
        self._wrapped_config = Config(config_module)

    def __getattr__(self, name):
        print('__getattr__')
        if self._wrapped_config is None:
            self._setup()

        val = getattr(self._wrapped_config, name)
        self.__dict__[name] = val
        return val


class Config:
    def __init__(self, settings_module: str):
        module = importlib.import_module(settings_module)
        for field in dir(module):
            if field.isupper():
                val = getattr(module, field)
                setattr(self, field, val)


config = LazyConfig()
