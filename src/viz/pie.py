import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

csvpath = Path(__file__).parent.parent.parent / "data" / "experiments" / "pie.csv"
df = pd.read_csv(csvpath)

fig = go.Figure(
    data=[
        go.Pie(
            labels=df["version"],
            values=df["implicit_issues"],
            textposition="outside",
            marker=dict(
                line=dict(color="black", width=1),
                pattern=dict(
                    shape=["", "/", "|", ".", "x", "-"],
                    fgcolor="black",
                    size=5,
                    solidity=0.2,
                )
            ),
        )
    ],
)
fig.update_traces(hoverinfo="label+percent", textinfo="value", textfont_size=20)

fig.update_layout(
    width=600,
    height=300,
    font=dict(size=20, color="black"),
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(
        orientation="v",
        yanchor="middle",
        y=0.5,
        xanchor="right",
        x=1.15,
    ),
)

outdir = Path(__file__).parent / "output"
outdir.mkdir(exist_ok=True)
fig.write_html(outdir / "pie.html")
fig.write_image(outdir / "pie.png", scale=2)
fig.write_image(outdir / "pie.pdf", scale=2)

print(f"Pie graph saved to {outdir}.")
