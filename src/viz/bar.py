from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

VERS = ["v5.4.296", "v5.10.240", "v5.15.189", "v6.1.147", "v6.6.100", "v6.12.40"]
FUZZERS = ["OS-MFuzzer", "syzkaller", "MoonShine", "ACTOR", "HEALER", "MOCK", "KernelGPT", "SyzGPT"] # Actually I prefer SyzMeta or SyzMorphic :)
PATTERNS = ["", "\\", "-", "|", ".", "/", "+", "x"]
COLORS = [
    "rgba(78,121,167,0.8)",
    "rgba(242,142,43,0.8)",
    "rgba(225,87,89,0.8)",
    "rgba(118,183,178,0.8)",
    "rgba(89,161,79,0.8)",
    "rgba(237,201,72,0.8)",
]

csvpath = Path(__file__).parent.parent.parent / "data" / "experiments" / "bar.csv"
df = pd.read_csv(csvpath)

fig = go.Figure()
for i, fuzzer in enumerate(FUZZERS):
    subdf = df[df["fuzzer"] == fuzzer]
    labels = list()
    for ver in VERS:
        crashes = subdf[subdf["version"] == ver]["crashes"].mean()
        if crashes % 1 == 0:
            labels.append(f"{int(crashes)}")
        else:
            labels.append(f"{crashes:.1f}")
    fig.add_trace(
        go.Bar(
            x=VERS,
            y=[subdf[subdf["version"] == ver]["crashes"].mean() for ver in VERS],
            name=fuzzer,
            marker=dict(
                pattern=dict(shape=PATTERNS[i % len(PATTERNS)], fgcolor="black", size=5, solidity=0.5),
                color="white",
                line=dict(color="black", width=1),
            ),
            text=labels,
            textposition="outside",
            textangle=-90,
            textfont=dict(size=16, color="black"),
        )
    )
fig.update_layout(barmode="group")

fig.update_layout(
    width=1200,
    height=400,
    font=dict(size=20, color="black"),
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
)

fig.update_xaxes(
    showline=True,
    linecolor="black",
    title_text="Kernel Version",
)

fig.update_yaxes(
    showline=True,
    linecolor="black",
    gridcolor="lightgray",
    range=[0, 40],
    title_text="Number of Detected Issues",
)

outdir = Path(__file__).parent.parent / "viz" / "output"
outdir.mkdir(exist_ok=True)
fig.write_html(outdir / "bar.html")
fig.write_image(outdir / "bar.png", scale=2)
fig.write_image(outdir / "bar.pdf", scale=2)

print(f"Bar graph saved to {outdir}")
