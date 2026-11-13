import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from receiver import parse_line
from simulator import SimulatedRadar
from target import TargetTracker


def test_parse_line():
    assert parse_line("Angle: 90°, Distance: 23 cm") == (90, 23)
    assert parse_line("Angle: 0°, Distance: 5 cm\r\n".encode("utf-8")) == (0, 5)
    assert parse_line("garbage") is None
    assert parse_line(b"") is None


def test_tracker_empty():
    tracker = TargetTracker()
    assert tracker.targets() == []
    assert tracker.nearest_angle() is None


def test_tracker_picks_middle_of_nearest_object():
    tracker = TargetTracker(threshold=2)
    for angle in range(30, 40):
        tracker.update(angle, 80)
    for angle in range(90, 101):
        tracker.update(angle, 35)
    assert tracker.nearest_angle() == 95
    assert all(d <= 37 for _, d in tracker.targets())


def test_tracker_forgets_object_that_left():
    now = [0.0]
    tracker = TargetTracker(max_age=10, clock=lambda: now[0])
    tracker.update(50, 20)
    now[0] = 20.0
    tracker.update(120, 70)
    assert tracker.targets() == [(120, 70)]


def _read_lines(sim, count):
    return [parse_line(line) for line in (sim.readline() for _ in range(count)) if line]


def test_simulator_protocol():
    sim = SimulatedRadar(step_delay=0, seed=1)
    assert sim.readline() == b""  # idle until started

    sim.write(b"start\n")
    readings = _read_lines(sim, 181)
    assert readings and all(r is not None for r in readings)
    assert all(0 <= a <= 180 and 0 < d <= 100 for a, d in readings)

    sim.write(b"stop\n")
    assert sim.readline() == b""
    sim.write(b"rotate 100\n")
    assert sim.angle == 100 and sim.readline() == b""
    sim.write(b"continue\n")
    assert _read_lines(sim, 5)[0][0] == 100


def test_end_to_end_finds_nearest_simulated_object():
    sim = SimulatedRadar(step_delay=0, seed=1)
    tracker = TargetTracker()
    sim.write(b"start\n")
    for angle, distance in _read_lines(sim, 181):
        tracker.update(angle, distance)
    assert 90 <= tracker.nearest_angle() <= 110  # the object at 100 deg, 35 cm
