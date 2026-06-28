from .base_instrument import BaseInstrumentAgent


class BrassAgent(BaseInstrumentAgent):
    @property
    def instrument_name(self) -> str:
        return "Brass"

    @property
    def valid_note_range(self) -> tuple[str, str]:
        return ("E2", "C6")
