from functools import lru_cache
from dynaconf import Dynaconf
import typing


@lru_cache()
def get_settings() -> typing.Any:
    return Dynaconf(
        settings_files=["settings.toml"],
        default_env="default",
        environments=True,
    )
