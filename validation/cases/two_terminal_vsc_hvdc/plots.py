"""Show PCC active-power direction, B-side DC recovery and DC-line transfer."""

import matplotlib


def plot_comparison(path, grids, timing):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(3, 2, figsize=(11, 8), sharex="col", sharey="row", layout="constrained")
    panels = (("PCC active power (W)", ("a_p_mean_w", "b_p_mean_w"), ("Station A", "Station B")),
              ("Station B DC voltage (V)", ("b_dc_mean_v",), ("B DC voltage",)),
              ("Bipolar DC-line power (W)", ("dc_sent_w", "dc_received_w"), ("Sent at A", "Received at B")))
    try:
        for column, (grid, (time, candidate, native)) in enumerate(grids.items()):
            axes[0, column].set_title("5 µs" if grid == "5us" else "2.5 µs")
            step = time[1] - time[0]
            interval = round(.001 / step)
            stop = interval * ((len(time)-1) // interval) + 1
            average_time = time[1:stop].reshape(-1, interval).mean(axis=1) * 1000
            for row, (title, keys, labels) in enumerate(panels):
                axis = axes[row, column]
                if column == 0:
                    axis.set_ylabel(title)
                for index, (key, label) in enumerate(zip(keys, labels, strict=True)):
                    color = ("#176581", "#a95034")[index]
                    for platform, trace, style, width in (("PSCAD", native, "-", 1.8), ("PyCy", candidate, "--", .9)):
                        if row == 1:
                            x, y = time[::interval] * 1000, trace[key][::interval]
                        else:
                            x, y = average_time, trace[key][1:stop].reshape(-1, interval).mean(axis=1)
                        axis.plot(x, y, style, color=color, linewidth=width, label=f"{label} · {platform}")
                for lo, hi in timing["power_windows_s"].values():
                    axis.axvspan(lo * 1000, hi * 1000, color="#667b66", alpha=.08)
                if row == 0:
                    axis.axhline(0, color="#686868", linewidth=.65)
                axis.grid(axis="y", alpha=.22)
                if column == 0:
                    axis.legend(loc="best", fontsize=7)
            axes[-1, column].set_xlabel("Time since snapshot (ms)")
        figure.suptitle("Two-terminal VSC-HVDC load transfer · power displayed as 1 ms means")
        figure.savefig(path, dpi=150)
    finally:
        plt.close(figure)
