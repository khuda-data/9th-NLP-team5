from .bass import BassAgent
from .kick import KickAgent
from .pluck import PluckAgent
from .brass import BrassAgent
from .strings import StringsAgent

INSTRUMENT_REGISTRY: dict[str, type] = {
    "bass": BassAgent,
    "kick": KickAgent,
    "pluck": PluckAgent,
    "brass": BrassAgent,
    "strings": StringsAgent,
}

ALL_INSTRUMENTS = list(INSTRUMENT_REGISTRY.keys())
