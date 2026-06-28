from .base_instrument import BaseInstrumentAgent


class BassAgent(BaseInstrumentAgent):
    @property
    def instrument_name(self) -> str:
        return "Bass"

    @property
    def valid_note_range(self) -> tuple[str, str]:
        return ("E1", "G3")
