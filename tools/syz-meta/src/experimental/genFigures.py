import argparse
import os

import pandas as pd
import numpy as np
import seaborn as sns
import seaborn.objects as so
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


########## GLOBAL VARIABLES ##########
FONT_SIZE = 14
FONT_FAMILY = "Consolas"
######################################


def genCrashFig(args: argparse.Namespace):
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


def genMRIdenFig(args: argparse.Namespace):
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


def main(args: argparse.Namespace):
    """Main function to generate figures based on command line arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    prepare()
    for fig in args.figs:
        if fig == "all" or fig == "MRIden":
            genMRIdenFig(args)
        elif fig == "all" or fig == "crash":
            genCrashFig(args)
        else:
            print(f"Unknown figure type: {fig}. Skipping.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draw plots from data")
    parser.add_argument("--excel", type=str, required=True, help="Path to the Excel file containing data")
    parser.add_argument("--figs", nargs="+", default="all", choices=["all", "MRIden", "crash"], help="Type of figures to generate")
    args = parser.parse_args()
    main(args)
