from .base_instrument import BaseInstrumentAgent


class StringsAgent(BaseInstrumentAgent):
    @property
    def instrument_name(self) -> str:
        return "Strings"

    @property
    def valid_note_range(self) -> tuple[str, str]:
        return ("C3", "E6")
