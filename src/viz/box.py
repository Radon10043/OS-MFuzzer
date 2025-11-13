import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

csv = Path(__file__).parent.parent.parent / "data" / "experiments" / "box.csv"
df = pd.read_csv(csv)
versions = df["version"].unique().tolist()

fig = go.Figure()
fig.add_trace(
    go.Box(
        y=df[df["fuzzer"] == "OS-MFuzzer"]["crashes"].to_list(),
        x=df[df["fuzzer"] == "OS-MFuzzer"]["version"].to_list(),
        name="OS-MFuzzer",     # Actually I prefer SyzMeta or SyzMorphic :)
        marker_color="#1f77b4",
    )
)
fig.add_trace(
    go.Box(
        y=df[df["fuzzer"] == "OS-MFuzzer-E-"]["crashes"].to_list(),
        x=df[df["fuzzer"] == "OS-MFuzzer-E-"]["version"].to_list(),
        name="OS-MFuzzer<sub>E-</sub>",
        marker_color="#ff7f0e",
    )
)
fig.add_trace(
    go.Box(
        y=df[df["fuzzer"] == "OS-MFuzzer-R-"]["crashes"].to_list(),
        x=df[df["fuzzer"] == "OS-MFuzzer-R-"]["version"].to_list(),
        name="OS-MFuzzer<sub>R-</sub>",
        marker_color="#2ca02c",
    )
)
subdf = df[df["fuzzer"] == "OS-MFuzzer-RE-"]
fig.add_trace(
    go.Box(
        y=subdf[subdf["fuzzer"] == "OS-MFuzzer-RE-"]["crashes"].to_list(),
        x=subdf[subdf["fuzzer"] == "OS-MFuzzer-RE-"]["version"].to_list(),
        name="OS-MFuzzer<sub>RE-</sub>",
        marker_color="#d62728",
    )
)

fig.add_vline(x=0.5, line_width=1, line_dash="solid", line_color="lightgray")
fig.add_vline(x=1.5, line_width=1, line_dash="solid", line_color="lightgray")
fig.add_vline(x=2.5, line_width=1, line_dash="solid", line_color="lightgray")
fig.add_vline(x=3.5, line_width=1, line_dash="solid", line_color="lightgray")
fig.add_vline(x=4.5, line_width=1, line_dash="solid", line_color="lightgray")

fig.update_layout(
    width=1000,
    height=600,
    font=dict(size=24, color="black"),
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    boxmode="group",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
)
fig.update_xaxes(
    showline=True,
    linecolor="black",
)
fig.update_yaxes(
    showline=True,
    linecolor="black",
    gridcolor="lightgray",
    tickvals=list(range(0, 51, 5)),
    range=[0, 50],
)

outdir = Path(__file__).parent / "output"
fig.write_html(outdir / "box.html")
fig.write_image(outdir / "box.png", scale=2)
fig.write_image(outdir / "box.pdf", scale=2)
print(f"Box graph saved to {outdir}")