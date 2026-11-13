"""A stand-in for the Arduino so the program can run without hardware.

It speaks the same protocol as the firmware: it accepts start / stop /
continue / rotate <deg> and produces "Angle: N°, Distance: M cm" lines.
"""
import random
import time


class SimulatedRadar:
    # (centre angle in degrees, half width in degrees, distance in cm)
    OBJECTS = [(40, 8, 60), (100, 10, 35), (150, 6, 80)]

    def __init__(self, step_delay=0.03, seed=None):
        self.step_delay = step_delay
        self._rng = random.Random(seed)
        self.state = "idle"  # idle | scanning | paused
        self.angle = 0
        self._direction = 1
        self._buffer = b""

    # --- host -> device -------------------------------------------------
    def write(self, data):
        self._buffer += data
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            self._handle(line.decode("utf-8", errors="ignore").strip())
        return len(data)

    def _handle(self, cmd):
        if cmd == "start":
            self.angle, self._direction, self.state = 0, 1, "scanning"
        elif cmd == "stop":
            if self.state == "scanning":
                self.state = "paused"
        elif cmd == "continue":
            if self.state == "paused":
                self.state = "scanning"
        elif cmd.startswith("rotate"):
            try:
                target = int(cmd[6:].strip())
            except ValueError:
                return
            self.angle = max(0, min(180, target))
            self.state = "paused"

    # --- device -> host -------------------------------------------------
    def readline(self):
        """Return the next measurement line, or b"" if there is nothing to report."""
        if self.step_delay:
            time.sleep(self.step_delay)
        if self.state != "scanning":
            return b""

        angle = self.angle
        distance = self._measure(angle)

        self.angle += self._direction
        if self.angle >= 180:
            self.angle, self._direction = 180, -1
        elif self.angle <= 0:
            self.angle, self._direction = 0, 1

        if distance is None:  # no echo: the firmware sends nothing
            return b""
        return f"Angle: {angle}°, Distance: {distance} cm\n".encode("utf-8")

    def _measure(self, angle):
        for centre, half_width, distance in self.OBJECTS:
            if abs(angle - centre) <= half_width:
                return distance + self._rng.choice((-1, 0, 0, 1))
        return None

    def close(self):
        self.state = "idle"
