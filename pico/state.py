"""State shared by the Alpaca API and the control page."""


class FocuserState:
    def __init__(self, settings, sensor=None, settings_path='config.toml', restart=None):
        self.settings = settings            # live settings dict (load_settings result)
        self.sensor = sensor                # TemperatureSensor or None
        self.settings_path = settings_path
        self.restart = restart              # e.g. machine.reset on the Pico
        self.connected = False              # an Alpaca client (NINA) is connected
        self._txn = 0

    def next_txn(self):
        self._txn += 1
        return self._txn
