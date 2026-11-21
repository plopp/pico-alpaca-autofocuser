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
        self._release = False       # switch the driver off when the current move ends
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

    def hold(self):
        """A client took over: power the driver and cancel any pending switch-off."""
        self.enable()
        self._release = False

    def disable(self):
        self.halt()
        self._en.value(1)
        self._enabled = False

    def set_position(self, position):
        """Redefine where the focuser is, without moving."""
        if self._running:
            raise ValueError('cannot set the position while moving')
        if position < 0 or position > self._max_step:
            raise ValueError('position out of range')
        self._position = position
        self._target = position

    def configure(self, steps_per_sec, reverse, hold_when_idle):
        if self._running:
            raise ValueError('cannot change settings while moving')
        self._freq = steps_per_sec
        self._reverse = reverse
        self._hold = hold_when_idle

    def move_to(self, target, release=False):
        """Move to target. release=True switches the driver off again when the move ends
        (used for manual moves while no client holds the focuser)."""
        if target < 0 or target > self._max_step:
            raise ValueError('target out of range')
        # Arm the switch-off only for a move that actually happens
        self._release = release and (self._running or target != self._position)
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
        if self._release:
            self._switch_off()

    def _switch_off(self):
        self._en.value(1)
        self._enabled = False
        self._release = False

    def _tick(self, t=None):
        delta = self._target - self._position
        if delta == 0:
            self._timer.deinit()
            self._running = False
            if self._release or not self._hold:
                self._switch_off()
            return
        up = delta > 0
        self._dir.value(1 if up != self._reverse else 0)
        self._step.value(1)
        self._step.value(0)
        self._position += 1 if up else -1
        if self._position == self._target:
            self._tick()
