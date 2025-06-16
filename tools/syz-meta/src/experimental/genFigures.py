import argparse
import os
import re

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from matplotlib.lines import Line2D


########## GLOBAL VARIABLES ##########
FONT_SIZE = 14
FONT_FAMILY = "Consolas"
######################################


def parse_log_line(line: str) -> dict:
    """Parse a line from the fuzzing log file to extract relevant data.

    Parameters
    ----------
    line : str
        A line from the fuzzing log file.

    Returns
    -------
    dict
        A dictionary containing the extracted data.
    """
    kvs = line.split(" ")
    kvs = kvs[2:-1]
    datum = dict()
    for kv in kvs:  # Shit
        if kv == "exec":
            continue
        if kv.endswith("/sec)"):
            datum["speed"] = int(kv[1:-5])
            continue
        k, v = kv.split("=")
        if k == "total":
            k = "exec total"
        datum[k] = int(v)
    return datum


def read_fuzzing_log(log: str, gap: int = 60) -> list:
    """Read a fuzzing log file and extract related information.

    Parameters
    ----------
    log : str
        Path to the log file.
    gap : int, optional
        Time gap between each data point in seconds, by default 60

    Returns
    -------
    list
        A list of dictionaries containing the extracted information.
    """
    # Read the log file and filter lines
    lines = list()
    with open(log, "r") as f:
        tmp = f.readlines()
    for elem in tmp:
        if not "coverage=" in elem:
            continue
        lines.append(elem)

    # Extract related information from the log
    data = list()
    timepoint = 0
    for i in range(0, len(lines), int(gap / 10)):
        datum = parse_log_line(lines[i])
        datum["timepoint"] = timepoint
        data.append(datum)
        timepoint += gap

    return data


def gen_coverage_figure(args: argparse.Namespace):
    """Generate figure of coverage results.
       args.logdir should be the following structure:
       logdir/[kernel version]/[fuzzer name]/*.log

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    # Get unique kernel versions and fuzzers from the log directory
    vers = os.listdir(args.logdir)
    vers.sort()
    fuzzers = set()
    for ver in vers:
        vals = os.listdir(os.path.join(args.logdir, ver))
        for val in vals:
            fuzzers.add(val)
    fuzzers = list(fuzzers)
    fuzzers.sort()

    # Prepare the data for coverage & exec speed line graph
    plot_data_list = list()
    data2d = list()
    samplen = int(1e9 + 7)
    for ver in vers:
        for fuzzer in fuzzers:
            logs = os.listdir(os.path.join(args.logdir, ver, fuzzer))
            for log in logs:
                log_path = os.path.join(args.logdir, ver, fuzzer, log)
                data = read_fuzzing_log(log_path, gap=600)
                last_datum = read_fuzzing_log(log_path, gap=10)[-1]
                for datum in data:
                    datum["kernel version"] = last_datum["kernel version"] = ver
                    datum["fuzzer"] = last_datum["fuzzer"] = fuzzer
                last_datum["timepoint"] = 86400  # Timepoint of the last datum is set to 86400s (24h), I'm not sure if this is appropriate
                data.append(last_datum)
                data2d.append(data)

    # Uniform the length of data list
    for data in data2d:
        samplen = min(samplen, len(data))
    samplen -= 1  # We need to keep the last datum, so we reduce the sample length by 1
    for data in data2d:
        plot_data_list.extend(data[0:samplen] + [data[-1]])  # Keep the last datum
    plot_data = pd.DataFrame(plot_data_list)

    # Plot the line graph for coverage & exec speed
    fig, ax1 = plt.subplots(figsize=(8, 6))

    # Line graph for coverage & exec speed
    sns.lineplot(data=plot_data, x="timepoint", y="coverage", hue="fuzzer", ax=ax1, palette="bright")
    ax2 = ax1.twinx()
    sns.lineplot(data=plot_data, x="timepoint", y="speed", hue="fuzzer", ax=ax2, legend=False, linestyle="dashed", palette="bright")

    # Set properties of legend
    line_cov = Line2D([], [], color="black", label="Edge coverage")
    line_speed = Line2D([], [], color="black", linestyle="dashed", label="Execution speed")
    handles, labels = ax1.get_legend_handles_labels()
    handles.extend([line_cov, line_speed])
    labels.extend(["Edge coverage", "Execution speed"])
    ax1.legend(handles=handles, labels=labels, loc="upper left", prop={"size": FONT_SIZE - 2, "family": FONT_FAMILY}, frameon=True)

    # Set properties of x-axis & y-axis
    ax1.set_xticks(np.arange(0, 86401, 14400), [f"{i // 3600}h" for i in range(0, 86401, 14400)])
    ax1.set_yticks(np.arange(-50000, 250001, 50000), [str(i) for i in range(-50000, 250001, 50000)])
    ax1.set_ylim(-60000, 260000)
    ax1.set_xlabel("Fuzzing time")
    ax1.set_ylabel("Edge coverage")
    ax2.set_yticks(np.arange(0, 200, 20), [str(i) for i in range(0, 200, 20)])
    ax2.set_ylim(-5, 185)
    ax2.set_ylabel("Execution speed (exec/sec)")

    # Fine-tune & save the figure
    sns.despine(right=False)
    plt.tight_layout()
    plt.savefig("coverage.pdf")


def gen_crash_figure(args: argparse.Namespace):
    """Generate figure of crash results.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    excel = args.excel
    df = pd.read_excel(excel, sheet_name="Fuzzing", header=1, engine="calamine")

    # Get the unique kernel versions and fuzzers
    vers = df["kernel version"].unique().tolist()
    fuzzers = df["fuzzer"].unique().tolist()
    vers.sort()
    fuzzers.sort()

    # Preprocessing the data
    plot_data_list = list()
    for ver in vers:
        for fuzzer in fuzzers:
            subset = df[(df["kernel version"] == ver) & (df["fuzzer"] == fuzzer)]
            mean_total = subset["crash"].mean()
            mean_valid = subset["valid crash"].mean()
            mean_invalid = subset["invalid crash"].mean()
            plot_data_list.append({"Fuzzer & kernel version": "$\\text{" + fuzzer + "}_\\text{" + ver + "}$", "total": mean_total, "valid": mean_valid, "invalid": mean_invalid})
    plot_data = pd.DataFrame(plot_data_list)

    # Plot the "stacked" bar graph to show the distribution of valid and invalid crashes
    # Since seaborn does not support stacked bar plots directly, we plot two bars, which
    # is valid crash and total crash, to pretend that the bar is stacked.
    f, ax = plt.subplots(figsize=(8, 6))
    sns.set_theme(style="whitegrid")
    sns.set_color_codes("muted")
    sns.barplot(x="Fuzzer & kernel version", y="total", label="invalid", width=0.5, data=plot_data, color="b")
    sns.set_color_codes("pastel")
    sns.barplot(x="Fuzzer & kernel version", y="valid", label="valid", width=0.5, data=plot_data, color="b")
    ax.legend(ncol=2, loc="upper center", frameon=True, prop={"size": FONT_SIZE, "family": FONT_FAMILY})
    plt.ylabel("Number of crashes")
    plt.xticks(rotation=45, ha="right", va="top")

    # Ready to set the bar properties ...
    n = len(fuzzers) * len(vers)
    crash_types = ["invalid", "valid"]
    offset = 0.2
    ticks = ax.get_xticks()
    ntickpos = list()

    # Set bar properties
    for i, bar in enumerate(ax.patches):
        # Set position of the bar
        bar.set_x(bar.get_x() + (-1) ** i * offset)  # type: ignore

        # Prepare new x-ticks position
        if i < len(ticks):
            ntickpos.append(ticks[i] + (-1) ** i * offset)  # type: ignore

        # Add text to the bar
        crash_type = crash_types[i // n]
        fuzzer_ver = plot_data["Fuzzer & kernel version"].values[i % n]
        num = plot_data[plot_data["Fuzzer & kernel version"] == fuzzer_ver][crash_type].values[0]
        text = f"{num:.1f}"
        color = "black" if crash_type == "valid" else "white"
        x = bar.get_x() + bar.get_width() / 2  # type: ignore
        y = bar.get_height() / 2  # type: ignore
        if crash_type == "invalid":
            valid_height = plot_data[plot_data["Fuzzer & kernel version"] == fuzzer_ver]["valid"].values[0]
            y = valid_height + (bar.get_height() - valid_height) / 2  # type: ignore
        ax.text(x, y, text, ha="center", va="center", fontdict={"size": FONT_SIZE - 2, "family": FONT_FAMILY, "color": color})

    # Update x-ticks postion
    ax.set_xticks(ntickpos)

    plt.tight_layout()
    plt.savefig("crash.pdf")
    print("Successfully draw crash figure.")


def gen_mriden_figure(args: argparse.Namespace):
    """Generate figure of MR identification results.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    excel = args.excel
    df = pd.read_excel(excel, sheet_name="Metamorphic", header=1, engine="calamine")

    # Get the unique kernel versions, excluding "general"
    tmp = df["kernel version"].unique()
    indices = np.where(tmp != "general")
    vers = tmp[indices].tolist()
    vers.sort()

    # Get the unqiue drivers
    drivers = df["driver"].unique().tolist()

    # Initialize the plot
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 8))
    axes = axes.flatten()

    # Draw the figure of MR identification result
    for i in range(len(vers)):
        ver = vers[i]
        plot_data_list = list()
        for driver in drivers:
            df_driver = df[df["driver"] == driver]
            df_total = df_driver[(df_driver["kernel version"] == ver) | (df_driver["kernel version"] == "general")]
            df_gen_succ = df_total[df_total["iden succ"] & df_total["impl succ"]]
            df_legal = df_gen_succ[df_gen_succ["legal"] == True]
            df_correct = df_legal[df_legal["correct"] == True]
            cnt_total, cnt_gen_succ, cnt_legal, cnt_correct = len(df_total), len(df_gen_succ), len(df_legal), len(df_correct)
            plot_data_list.append({"driver": driver, "type": "gen_succ", "count": cnt_gen_succ, "rate": cnt_gen_succ / cnt_total})
            plot_data_list.append({"driver": driver, "type": "legal", "count": cnt_legal, "rate": cnt_legal / cnt_total})
            plot_data_list.append({"driver": driver, "type": "correct", "count": cnt_correct, "rate": cnt_correct / cnt_total})

        # Create the figure
        plot_data = pd.DataFrame(plot_data_list)
        sns.barplot(x="driver", y="rate", hue="type", data=plot_data, palette="muted", ax=axes[i])
        axes[i].set_title("(" + chr(ord("a") + i) + f") {ver}")

        # Format y-axis as percentage
        formatter = mticker.PercentFormatter(xmax=1.0, decimals=0)
        axes[i].yaxis.set_major_formatter(formatter)

        # Set bar properties
        for index, bar in enumerate(axes[i].patches):
            # Set edge color to black
            bar.set_edgecolor("black")
            bar.set_linewidth(1)

            # Invalid bar check
            if bar.get_xy() == (0, 0):  # ?
                continue

            # Get corresponding count of the bar
            driver = plot_data["driver"].unique()[index % len(drivers)]
            rate_type = plot_data["type"].unique()[(index // len(drivers)) % 3]
            cnt = plot_data[(plot_data["driver"] == driver) & (plot_data["type"] == rate_type)]["count"].values[0]

            # Write text in/on the top of the bar
            text = f"{cnt}, {bar.get_height():.2%}"
            x = bar.get_x() + bar.get_width() / 2
            y = bar.get_height()
            if y <= 0.2:
                y += 0.06 + len(text) * 0.01
            else:
                y -= 0.06 + len(text) * 0.01
            axes[i].text(x, y, text, ha="center", va="center", rotation=90, color="black", fontsize=FONT_SIZE - 4)

        # Set the x and y labels
        axes[i].set_xlabel("Drivers")
        axes[i].set_ylabel("Rate")

    # Set the legend
    handles, labels = axes[0].get_legend_handles_labels()
    for ax in axes:
        ax.get_legend().remove()
    fig.legend(handles, labels, title="Type", loc="lower center", ncols=3)

    # Adjust layout and save the figure
    plt.tight_layout(rect=(0, 0.06, 1, 1))
    plt.savefig(f"bar.pdf")
    print("Successfully draw MR identification result figure.")


def prepare():
    """Some preparation before drawing figures."""
    plt.rcParams.update({"font.size": FONT_SIZE, "font.family": FONT_FAMILY})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draw plots from data")
    subparser = parser.add_subparsers(title="subcommands", required=True)

    # Subcommand for generating figure of MR identification results
    mri_parser = subparser.add_parser("mri", help="Generate figure of MR identification results")
    mri_parser.add_argument("--excel", type=str, required=True, help="Path to the Excel file containing data")
    mri_parser.set_defaults(func=gen_mriden_figure)

    # Subcommand for generating figure of crash results
    crash_parser = subparser.add_parser("crash", help="Generate figure of crash results")
    crash_parser.add_argument("--excel", type=str, required=True, help="Path to the Excel file containing data")
    crash_parser.set_defaults(func=gen_crash_figure)

    # Subcommand for generating figure of coverage results
    coverage_parser = subparser.add_parser("coverage", help="Generate figure of coverage results")
    coverage_parser.add_argument("--logdir", type=str, required=True, help="Path to the log directory containing kernel fuzzing logs")
    coverage_parser.set_defaults(func=gen_coverage_figure)

    args = parser.parse_args()
    prepare()
    args.func(args)
