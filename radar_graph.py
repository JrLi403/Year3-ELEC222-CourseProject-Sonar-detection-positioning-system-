"""The radar display: a half-circle polar plot with a fading sweep and recent echoes."""
from collections import deque

import numpy as np
import matplotlib.pyplot as plt


class RadarView:
    def __init__(self, r_max=100, max_points=60, sweep_lines=10):
        self.r_max = r_max
        self.sweep_lines = sweep_lines
        self._points = deque(maxlen=max_points)  # (angle_rad, distance)
        self._sweep = deque(maxlen=sweep_lines)  # recent beam angles in radians

        self.fig, self.ax = plt.subplots(subplot_kw={"projection": "polar"})
        try:
            self.fig.canvas.manager.set_window_title("Radar Plot")
        except AttributeError:
            pass  # headless backends have no window
        self.fig.subplots_adjust(bottom=0.2)

        ax = self.ax
        ax.set_facecolor("#006b70")
        ax.tick_params(axis="both", colors="white")
        ax.set_ylim([0.0, r_max])
        ax.set_xlim([0.0, np.pi])
        ticks = [0, 30, 60, 90, 120, 150, 180]
        ax.set_xticks(np.radians(ticks))
        ax.set_xticklabels([f"{t}°" for t in ticks], fontsize=10, color="black")
        ax.grid(color="white", linestyle="--", linewidth=0.5)

        self._scatter = ax.scatter([], [], color="white", s=6)
        self._targets = ax.scatter([], [], color="red", s=18, zorder=3)
        self._lines = [
            ax.plot([], [], color="white", linewidth=1)[0] for _ in range(sweep_lines)
        ]

    def add_point(self, angle, distance):
        """Record one echo. Call redraw() afterwards to update the screen."""
        angle_rad = np.radians(angle)
        self._sweep.append(angle_rad)
        if distance <= self.r_max:
            self._points.append((angle_rad, distance))

    def set_targets(self, targets):
        """targets: [(angle_deg, distance), ...] to highlight in red."""
        if targets:
            offsets = [(np.radians(a), d) for a, d in targets]
        else:
            offsets = np.empty((0, 2))
        self._targets.set_offsets(offsets)

    def redraw(self):
        if self._points:
            self._scatter.set_offsets(list(self._points))
            self._scatter.set_alpha(np.linspace(0.1, 1.0, len(self._points)))
        # newest beam is brightest, older ones fade out
        recent = list(self._sweep)[::-1]
        alphas = np.linspace(0.8, 0.05, self.sweep_lines)
        for i, line in enumerate(self._lines):
            if i < len(recent):
                line.set_data([0, recent[i]], [0, self.r_max])
                line.set_alpha(alphas[i])
            else:
                line.set_data([], [])
        self.fig.canvas.draw_idle()
