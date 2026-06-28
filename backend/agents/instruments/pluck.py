from .base_instrument import BaseInstrumentAgent


class PluckAgent(BaseInstrumentAgent):
    @property
    def instrument_name(self) -> str:
        return "Pluck"

    @property
    def valid_note_range(self) -> tuple[str, str]:
        return ("C3", "C6")
