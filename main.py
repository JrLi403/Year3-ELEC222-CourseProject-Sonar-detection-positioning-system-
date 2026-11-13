"""Ultrasonic radar host program.

    python main.py --port COM6                      # Windows, real hardware
    python main.py --port /dev/tty.usbmodemXXXX     # macOS / Linux
    python main.py --simulate                       # no hardware needed
"""
import argparse
import queue

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

from radar_graph import RadarView
from receiver import Reader
from target import TargetTracker


class App:
    def __init__(self, link, r_max=100, max_points=60):
        self.link = link
        self.readings = queue.Queue()
        self.tracker = TargetTracker()
        self.view = RadarView(r_max, max_points)
        self.reader = None
        self.paused = False

        fig = self.view.fig
        specs = [
            ("System On", self.on_start),
            ("Target / Resume", self.on_target),
            ("Pause / Resume", self.on_pause),
            ("System Off", self.on_off),
        ]
        # keep references: matplotlib buttons stop working if garbage collected
        self.buttons = []
        for i, (label, handler) in enumerate(specs):
            button = Button(fig.add_axes([0.05 + i * 0.23, 0.05, 0.21, 0.075]), label)
            button.on_clicked(handler)
            self.buttons.append(button)

    # --- button handlers --------------------------------------------------
    def on_start(self, event=None):
        self.tracker.clear()
        self.paused = False
        self.link.write(b"start\n")
        if self.reader is None:
            self.reader = Reader(self.link, self.readings)
            self.reader.start()

    def on_target(self, event=None):
        """Point the sensor at the nearest object, or resume scanning if already paused."""
        if self.paused:
            self.link.write(b"continue\n")
            self.paused = False
            return
        angle = self.tracker.nearest_angle()
        if angle is None:
            print("No target")
            return
        self.link.write(b"stop\n")
        self.link.write(f"rotate {angle}\n".encode("utf-8"))
        self.paused = True
        print(f"Rotated to {angle}°")

    def on_pause(self, event=None):
        self.link.write(b"continue\n" if self.paused else b"stop\n")
        self.paused = not self.paused

    def on_off(self, event=None):
        try:
            self.link.write(b"stop\n")
        except Exception:
            pass
        if self.reader is not None:
            self.reader.stop()
        plt.close("all")
        print("System is off")

    # --- drawing (main thread only) ---------------------------------------
    def handle_reading(self, angle, distance):
        self.tracker.update(angle, distance)
        self.view.add_point(angle, distance)

    def poll(self, frame=None):
        """Drain readings from the serial thread and refresh the display."""
        updated = False
        while True:
            try:
                angle, distance = self.readings.get_nowait()
            except queue.Empty:
                break
            self.handle_reading(angle, distance)
            updated = True
        if updated:
            self.refresh()

    def refresh(self):
        self.view.set_targets(self.tracker.targets())
        self.view.redraw()


def open_link(args):
    if args.simulate:
        from simulator import SimulatedRadar

        return SimulatedRadar()
    if not args.port:
        raise SystemExit("Give the Arduino's serial port with --port, or use --simulate.")
    import serial  # imported here so --simulate works without pyserial

    return serial.Serial(args.port, args.baud, timeout=0.1)


def main():
    parser = argparse.ArgumentParser(description="Ultrasonic radar display and control")
    parser.add_argument("--port", help="serial port, e.g. COM6 or /dev/tty.usbmodemXXXX")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--simulate", action="store_true", help="run without hardware")
    parser.add_argument("--r-max", type=int, default=100, help="display range in cm")
    args = parser.parse_args()

    link = open_link(args)
    app = App(link, r_max=args.r_max)
    # keep a reference so the animation is not garbage collected
    app.animation = FuncAnimation(
        app.view.fig, app.poll, interval=50, cache_frame_data=False
    )
    try:
        plt.show()
    finally:
        link.close()


if __name__ == "__main__":
    main()
