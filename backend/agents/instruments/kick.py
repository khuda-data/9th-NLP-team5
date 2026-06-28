from .base_instrument import BaseInstrumentAgent


class KickAgent(BaseInstrumentAgent):
    @property
    def instrument_name(self) -> str:
        return "Kick"

    @property
    def valid_note_range(self) -> tuple[str, str]:
        # Kick drum: single pitch trigger
        return ("C1", "C1")
