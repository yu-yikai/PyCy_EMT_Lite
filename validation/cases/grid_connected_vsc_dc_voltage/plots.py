"""Plot the two sealed native and candidate DC-link comparisons."""

from math import ceil, floor

import matplotlib
import numpy as np

GRIDS = (("5us", "5 µs"), ("2p5us", "2.5 µs"))
CARRIER_PERIOD = 1e-3
LOAD_STEP_S = 0.4


def _carrier_means(time, signal):
    """Average over complete carrier periods on the original electrical clock."""
    edges = CARRIER_PERIOD * np.arange(
        ceil(time[0] / CARRIER_PERIOD), floor(time[-1] / CARRIER_PERIOD) + 1,
    )
    integral = np.empty_like(time)
    integral[0] = 0
    np.cumsum(0.5 * (signal[:-1] + signal[1:]) * np.diff(time), out=integral[1:])
    mean = np.diff(np.interp(edges, time, integral)) / CARRIER_PERIOD
    return 0.5 * (edges[1:] + edges[:-1]), mean


def plot_comparison(path, candidate, native):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(3, 2, sharex=True, sharey="row", layout="constrained", figsize=(11, 8))
    try:
        for column, (grid, title) in enumerate(GRIDS):
            voltage, current, load = axes[:, column]
            for engine, traces, color, style in (
                ("PyCy", candidate, "#176581", "-"),
                ("PSCAD", native, "#a95034", "--"),
            ):
                trace = traces[grid]
                time = np.asarray(trace["time_s"])
                mean_time, mean_current = _carrier_means(time, np.asarray(trace["id_a"]))
                voltage.plot(time, trace["vdc_v"], style, color=color, linewidth=1, label=engine)
                current.plot(mean_time, mean_current, style, color=color, linewidth=1)
                load.plot(time, trace["load_power_w"], style, color=color, linewidth=1)

            trace = candidate[grid]
            time, command = np.asarray(trace["time_s"]), np.asarray(trace["id_ref_a"])
            changes = np.r_[0, np.flatnonzero(np.diff(command)) + 1, len(time) - 1]
            current.step(time[changes], command[changes], where="post", color="#454545", lw=.8, label="PyCy d command")
            voltage.axhline(400, color="#777777", lw=.7)
            voltage.set_title(f"{title} electrical step")
            for axis in (voltage, current, load):
                axis.axvline(LOAD_STEP_S, color="#777777", linestyle=":", lw=.9)
                axis.set_xlim(.25, .8)
                axis.grid(alpha=.22)

        axes[0, 0].set_ylabel("DC-link voltage (V)")
        axes[1, 0].set_ylabel("d current, 1 ms mean (A)")
        axes[2, 0].set_ylabel("DC load power (W)")
        axes[0, 0].legend(loc="lower right")
        axes[1, 0].legend(loc="lower right")
        figure.supxlabel("Time since initialization (s)")
        figure.savefig(path, dpi=145)
    finally:
        plt.close(figure)
