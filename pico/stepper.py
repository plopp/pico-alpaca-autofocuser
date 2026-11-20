"""Timer-driven stepper for a STEP/DIR/EN driver (TMC2209).

A periodic timer calls _tick() at steps_per_sec. Each tick moves one step
toward the target, so the caller (the HTTP server) never blocks. Pins and the
timer are passed in, so this runs on the desktop with fakes for testing.
"""


class Stepper:
    def __init__(self, step_pin, dir_pin, en_pin, timer, steps_per_sec,
                 start_position, max_step, reverse=False, hold_when_idle=True):
        self._step = step_pin
        self._dir = dir_pin
        self._en = en_pin
        self._timer = timer
        self._freq = steps_per_sec
        self._max_step = max_step
        self._reverse = reverse
        self._hold = hold_when_idle
        self._position = start_position
        self._target = start_position
        self._running = False
        self._enabled = False
        self._en.value(1)           # Active low: start with the driver off

    @property
    def position(self):
        return self._position

    @property
    def target(self):
        return self._target

    @property
    def is_moving(self):
        return self._running

    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        self._en.value(0)
        self._enabled = True

    def disable(self):
        self.halt()
        self._en.value(1)
        self._enabled = False

    def move_to(self, target):
        if target < 0 or target > self._max_step:
            raise ValueError('target out of range')
        self._target = target
        if not self._running and target != self._position:
            if not self._enabled:       # hold_when_idle=False switched it off
                self.enable()
            self._running = True
            self._timer.init(mode=self._timer.PERIODIC, freq=self._freq,
                             callback=self._tick)

    def halt(self):
        self._timer.deinit()
        self._running = False
        self._target = self._position

    def _tick(self, t=None):
        delta = self._target - self._position
        if delta == 0:
            self._timer.deinit()
            self._running = False
            if not self._hold:
                self._en.value(1)
                self._enabled = False
            return
        up = delta > 0
        self._dir.value(1 if up != self._reverse else 0)
        self._step.value(1)
        self._step.value(0)
        self._position += 1 if up else -1
        if self._position == self._target:
            self._tick()
