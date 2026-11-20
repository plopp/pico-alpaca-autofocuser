"""Shared test helpers. Board code in pico/ is imported directly on CPython."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pico'))


class FakePin:
    """Stands in for machine.Pin; records every value written."""

    def __init__(self, value=0):
        self._value = value
        self.history = []

    def value(self, v=None):
        if v is None:
            return self._value
        self._value = 1 if v else 0
        self.history.append(self._value)


class FakeTimer:
    """Stands in for machine.Timer; the test advances it with tick()."""

    PERIODIC = 1

    def __init__(self):
        self.running = False
        self.freq = None
        self._callback = None

    def init(self, mode=None, freq=None, callback=None):
        self.running = True
        self.freq = freq
        self._callback = callback

    def deinit(self):
        self.running = False

    def tick(self, n=1):
        for _ in range(n):
            if not self.running:
                return
            self._callback(self)
