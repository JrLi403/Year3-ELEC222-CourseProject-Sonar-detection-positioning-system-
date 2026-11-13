"""Target detection: find the closest object in the most recent readings."""
import time


class TargetTracker:
    """Keeps the latest distance seen at each angle and picks out the nearest object.

    Readings older than ``max_age`` seconds are dropped, so an object that has
    moved away stops being reported after roughly one sweep.
    """

    def __init__(self, threshold=2, max_age=15.0, clock=time.monotonic):
        self.threshold = threshold
        self.max_age = max_age
        self._clock = clock
        self._readings = {}  # angle -> (distance, timestamp)

    def update(self, angle, distance):
        self._readings[angle] = (distance, self._clock())

    def _fresh(self):
        now = self._clock()
        self._readings = {
            a: (d, t) for a, (d, t) in self._readings.items() if now - t <= self.max_age
        }
        return self._readings

    def targets(self):
        """Return [(angle, distance), ...] within ``threshold`` cm of the closest reading."""
        readings = self._fresh()
        if not readings:
            return []
        nearest = min(d for d, _ in readings.values())
        return sorted(
            (a, d) for a, (d, _) in readings.items() if d <= nearest + self.threshold
        )

    def nearest_angle(self):
        """Angle at the middle of the closest object, or None if nothing is detected."""
        targets = self.targets()
        if not targets:
            return None
        return targets[len(targets) // 2][0]

    def clear(self):
        self._readings.clear()
