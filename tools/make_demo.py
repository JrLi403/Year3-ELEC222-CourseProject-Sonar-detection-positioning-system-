"""Render docs/demo.gif from the simulator (no hardware or screen needed).

    python tools/make_demo.py
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

from main import App  # noqa: E402
from simulator import SimulatedRadar  # noqa: E402

STEPS_PER_FRAME = 3
SCAN_FRAMES = 130      # a bit more than one full sweep there and back
HOLD_FRAMES = 25       # time spent pointing at the target


def main():
    sim = SimulatedRadar(step_delay=0, seed=7)
    app = App(sim)
    app.view.fig.set_size_inches(6, 4.5)
    app.on_start()
    app.reader.stop()  # this script feeds readings itself, frame by frame

    def frame(i):
        if i == SCAN_FRAMES:
            app.on_target()            # stop and rotate to the nearest object
            app.view.add_point(sim.angle, app.view.r_max + 1)  # show the beam there
        elif i == SCAN_FRAMES + HOLD_FRAMES:
            app.on_target()            # resume scanning
        for _ in range(STEPS_PER_FRAME):
            line = sim.readline()
            if line:
                from receiver import parse_line

                app.handle_reading(*parse_line(line))
            elif sim.state == "scanning":
                app.view.add_point(sim.angle, app.view.r_max + 1)  # beam, no echo
        app.refresh()

    total = SCAN_FRAMES + HOLD_FRAMES + 40
    anim = FuncAnimation(app.view.fig, frame, frames=total, cache_frame_data=False)
    out = os.path.join(ROOT, "docs", "demo.gif")
    anim.save(out, writer=PillowWriter(fps=20), dpi=70)
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
