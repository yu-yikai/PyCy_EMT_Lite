"""Plot the measured PJM5 load-step response and the settled power redistribution."""

import matplotlib
import numpy as np

GRIDS = (("5us", "5 µs"), ("2p5us", "2.5 µs"))
PATHS = (("1 → 2", "to_a", 0), ("3 → 2", "from_a", 3))  # line order 12, 14, 15, 23, 34, 45
PRE_WINDOW = (0.24, 0.29)
POST_WINDOW = (0.55, 0.60)


def _window_mean(time, values, window):
    step = time[1] - time[0]
    start, stop = (round((bound - time[0]) / step) for bound in window)
    selected = slice(start, stop + 1)
    return np.trapezoid(values[selected], time[selected]) / (time[stop] - time[start])


def _path_changes(trace):
    time, voltage = trace["time_s"], trace["voltage_v"][:, 1]
    changes = []
    for _, port, index in PATHS:
        # The native port current is positive into the line and negative into bus 2.
        power = -np.sum(voltage * trace[port][:, index], axis=1)
        changes.append((_window_mean(time, power, POST_WINDOW) - _window_mean(time, power, PRE_WINDOW)) / 1e6)
    return changes


def plot_comparison(destination, candidate, native):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 2, sharey="row", layout="constrained", figsize=(10, 6.4))
    paths = np.arange(len(PATHS))
    try:
        for column, (grid, title) in enumerate(GRIDS):
            voltage_axis, power_axis = axes[:, column]
            for name, traces, color, line, offset in (
                ("PyCy", candidate, "#176581", "-", -0.17),
                ("PSCAD", native, "#a95034", "--", 0.17),
            ):
                trace = traces[grid]
                time = trace["time_s"]
                zoom = (time >= 0.295) & (time <= 0.315)
                bus2 = trace["voltage_v"][zoom, 1]
                phase_rms = np.sqrt(np.mean(bus2**2, axis=1))
                voltage_axis.plot(1000 * time[zoom], phase_rms / 1000, line, color=color, lw=1, label=name)
                power_axis.bar(paths + offset, _path_changes(trace), width=0.30, color=color)

            voltage_axis.set_title(f"{title} electrical step")
            voltage_axis.axvline(300, color="#666666", linestyle=":", lw=.9)
            voltage_axis.set(xlabel="Time (ms)", xlim=(295, 315))
            power_axis.set_xticks(paths, [label for label, _, _ in PATHS])
            power_axis.set_xlabel("Path into bus 2")
            for axis in (voltage_axis, power_axis):
                axis.grid(axis="y", alpha=.25)

        axes[0, 0].set_ylabel("Bus 2 phase RMS (kV)")
        axes[1, 0].set_ylabel("Settled import increase (MW)")
        axes[0, 0].legend(loc="lower right")
        figure.savefig(destination, dpi=145)
    finally:
        plt.close(figure)
