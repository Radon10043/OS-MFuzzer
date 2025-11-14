from pathlib import Path
from plotly import graph_objects as go
from plotly.subplots import make_subplots


VERSIONS = ["v5.4.296", "v5.10.240", "v5.15.189", "v6.1.147", "v6.6.100", "v6.12.40"]


def get_cov_list(f: Path) -> list[int]:
    """Get coverage list from syzkaller-based fuzzer's log

    Parameters
    ----------
    f : Path
        Path to syzkaller-based fuzzer's log

    Returns
    -------
    list[int]
        Coverage list
    """
    cov_list = list()
    prev_cov = -1
    lines = f.read_text().splitlines()
    for line in lines:
        if not "coverage=" in line:
            continue
        fv = line.split()[4]
        _, v = fv.split("=")
        cov_list.append(int(v))
        prev_cov = int(v)
    while len(cov_list) < 8640:
        cov_list.append(prev_cov)
    return cov_list


def get_lua(l: list[list[int]]) -> list[list[int]]:
    """Get lower, upper, and average

    Parameters
    ----------
    l : list[list[int]]
        2d list

    Returns
    -------
    list[list[int]]
        [lower, upper, average]
    """
    lower = [min(x) for x in zip(*l)]
    upper = [max(x) for x in zip(*l)]
    average = [sum(x) // len(x) for x in zip(*l)]
    return [lower, upper, average]


def set_subfig(
    fig: go.Figure,
    x: list,
    lower: list,
    upper: list,
    avg: list,
    row: int,
    col: int,
    color: str,
    name: str,
    symbol: str,
):
    fig.add_trace(
        go.Scatter(
            x=x,
            y=avg,
            mode="lines",
            line=dict(
                color=f"rgb({color})",
            ),
            showlegend=False,
            name=name,
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=x[::1000],
            y=avg[::1000],
            mode="markers",
            marker=dict(size=8, symbol=symbol, color=f"rgb({color})"),
            showlegend=False,
            name=name,
        ),
        row=row,
        col=col,
    )


# Set lines
fig = make_subplots(
    rows=2,
    cols=3,
    horizontal_spacing=0.1,
    vertical_spacing=0.12,
    subplot_titles=VERSIONS,
)
root = Path(__file__).parent.parent.parent / "data" / "experiments" / "coverage"
x = list(range(0, 86400, 10))
for i in range(len(VERSIONS)):
    p = root / f"linux-{VERSIONS[i]}" / "OS-MFuzzer"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    # Actually I prefer SyzMeta or SyzMorphic :)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "31,119,180", "OS-MFuzzer", "circle")

    p = root / f"linux-{VERSIONS[i]}" / "OS-MFuzzer-E-"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "255,127,14", "OS-MFuzzer<sub>/E</sub>", "diamond")

    p = root / f"linux-{VERSIONS[i]}" / "OS-MFuzzer-R-"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "44,160,44", "OS-MFuzzer<sub>/R</sub>", "square")

    p = root / f"linux-{VERSIONS[i]}" / "OS-MFuzzer-RE-"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "214,39,40", "OS-MFuzzer<sub>/RE</sub>", "star")

# Set legend
fig.add_trace(
    go.Scatter(
        x=[None],
        y=[None],
        mode="lines+markers",
        line=dict(color="rgb(31,119,180)"),
        marker=dict(color="rgb(31,119,180)", symbol="circle", size=8),
        showlegend=True,
        name="OS-MFuzzer",
    ),
)
fig.add_trace(
    go.Scatter(
        x=[None],
        y=[None],
        mode="lines+markers",
        line=dict(color="rgb(255,127,14)"),
        marker=dict(color="rgb(255,127,14)", symbol="diamond", size=8),
        showlegend=True,
        name="OS-MFuzzer<sub>/E</sub>",
    ),
)
fig.add_trace(
    go.Scatter(
        x=[None],
        y=[None],
        mode="lines+markers",
        line=dict(color="rgb(44,160,44)"),
        marker=dict(color="rgb(44,160,44)", symbol="square", size=8),
        showlegend=True,
        name="OS-MFuzzer<sub>/R</sub>",
    ),
)
fig.add_trace(
    go.Scatter(
        x=[None],
        y=[None],
        mode="lines+markers",
        line=dict(color="rgb(214,39,40)"),
        marker=dict(color="rgb(214,39,40)", symbol="star", size=8),
        showlegend=True,
        name="OS-MFuzzer<sub>/RE</sub>",
    ),
)

# Fine-tune
fig.update_yaxes(range=[20000, 100000], row=1, col=1)
fig.update_yaxes(range=[30000, 105000], row=1, col=2)
fig.update_yaxes(range=[30000, 125000], row=1, col=3)
fig.update_yaxes(range=[30000, 120000], row=2, col=1)
fig.update_yaxes(range=[30000, 120000], row=2, col=2)
fig.update_yaxes(range=[40000, 125000], row=2, col=3)

fig.update_layout(
    width=1000,
    height=1000,
    font=dict(size=24, color="black"),
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5,
    ),
)
fig.update_xaxes(
    showline=True,
    linecolor="black",
    gridcolor="lightgray",
    title_standoff=0,
    title_text="Time",
    tickvals=[21600, 43200, 64800, 86400],
    ticktext=["6h", "12h", "18h", "24h"],
    range=[0, 86400],
)
fig.update_yaxes(
    showline=True,
    linecolor="black",
    gridcolor="lightgray",
    title_text="Edge Coverage",
    title_standoff=0,
    tickvals=[0, 20000, 40000, 60000, 80000, 100000, 120000, 140000],
)

fig.update_annotations(font_size=24)

outdir = Path(__file__).parent / "output"
fig.write_html(outdir / "line.html")
fig.write_image(outdir / "line.png", scale=2)
fig.write_image(outdir / "line.pdf", scale=2)
print(f"Line graph saved to {outdir}")
