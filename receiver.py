"""Serial protocol: parse measurement lines and read them on a background thread."""
import re
import threading

# Firmware sends e.g. "Angle: 90°, Distance: 23 cm"
_LINE = re.compile(r"Angle:\s*(-?\d+)\D+Distance:\s*(-?\d+)")


def parse_line(line):
    """Return (angle, distance) from one line of firmware output, or None if malformed."""
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="ignore")
    match = _LINE.search(line)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


class Reader(threading.Thread):
    """Reads lines from the link and puts parsed (angle, distance) tuples on a queue.

    The thread never touches matplotlib; drawing happens on the main thread.
    """

    def __init__(self, link, out_queue):
        super().__init__(daemon=True)
        self.link = link
        self.out_queue = out_queue
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                line = self.link.readline()
            except Exception as exc:  # port unplugged, etc.
                print(f"Serial read failed: {exc}")
                break
            if not line:
                continue
            reading = parse_line(line)
            if reading is not None:
                self.out_queue.put(reading)

    def stop(self):
        self._stop_event.set()
