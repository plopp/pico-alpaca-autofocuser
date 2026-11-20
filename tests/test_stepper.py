import pytest

from conftest import FakePin, FakeTimer
from stepper import Stepper


def make(**kw):
    step, dirp, en, timer = FakePin(), FakePin(), FakePin(), FakeTimer()
    args = dict(steps_per_sec=800, start_position=50000, max_step=100000)
    args.update(kw)
    s = Stepper(step, dirp, en, timer, **args)
    return s, step, dirp, en, timer


def rising_edges(pin):
    return sum(1 for a, b in zip([0] + pin.history, pin.history) if a == 0 and b == 1)


def test_starts_disabled_at_start_position():
    s, step, dirp, en, timer = make()
    assert en.history == [1]
    assert s.position == 50000
    assert s.target == 50000
    assert s.is_moving is False
    assert s.enabled is False


def test_move_steps_to_target():
    s, step, dirp, en, timer = make()
    s.enable()
    s.move_to(50003)
    assert s.is_moving is True
    assert timer.running and timer.freq == 800
    timer.tick(10)
    assert s.position == 50003
    assert rising_edges(step) == 3
    assert s.is_moving is False
    assert timer.running is False


def test_direction_and_reverse():
    s, step, dirp, en, timer = make()
    s.move_to(49999)
    timer.tick()
    assert dirp.value() == 0
    s.move_to(50000)
    timer.tick()
    assert dirp.value() == 1

    r, _, rdir, _, rtimer = make(reverse=True)
    r.move_to(50001)
    rtimer.tick()
    assert rdir.value() == 0


@pytest.mark.parametrize('bad', [-1, 100001])
def test_move_out_of_range_raises(bad):
    s, *_ = make()
    with pytest.raises(ValueError):
        s.move_to(bad)


def test_move_while_moving_retargets():
    s, step, dirp, en, timer = make()
    s.move_to(50010)
    timer.tick(3)
    s.move_to(49990)
    timer.tick(100)
    assert s.position == 49990
    assert s.is_moving is False


def test_halt_stops_at_current_position():
    s, step, dirp, en, timer = make()
    s.move_to(50010)
    timer.tick(4)
    s.halt()
    assert s.position == 50004
    assert s.target == 50004
    assert s.is_moving is False
    assert timer.running is False


def test_hold_when_idle_false_disables_after_move():
    s, step, dirp, en, timer = make(hold_when_idle=False)
    s.enable()
    s.move_to(50002)
    timer.tick(5)
    assert en.value() == 1
    assert s.enabled is False


def test_hold_when_idle_true_keeps_enabled():
    s, step, dirp, en, timer = make()
    s.enable()
    s.move_to(50002)
    timer.tick(5)
    assert en.value() == 0
    assert s.enabled is True


def test_disable_halts():
    s, step, dirp, en, timer = make()
    s.enable()
    s.move_to(50010)
    timer.tick(2)
    s.disable()
    assert s.is_moving is False
    assert en.value() == 1
