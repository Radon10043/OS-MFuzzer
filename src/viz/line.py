from pathlib import Path
from plotly import graph_objects as go
from plotly.subplots import make_subplots


VERSIONS = ["v5.4.296", "v5.10.240", "v5.15.189", "v6.1.147", "v6.6.100", "v6.12.40"]
FUZZERS = ["SyzMeta", "SyzMeta-E-", "SyzMeta-R-"]
COLORS = ["31,119,180", "255,127,14", "44,160,44", "214,39,40"]


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
):
    global TEMP
    fig.add_trace(
        go.Scatter(
            x=x + x[::-1],
            y=lower + upper[::-1],
            fill="toself",
            fillcolor=f"rgba({color},0.2)",
            line_color="rgba(255,255,255,0)",
            showlegend=False,
            name=name,
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=avg,
            line=dict(color=f"rgb({color})"),
            showlegend=False,
            name=name,
        ),
        row=row,
        col=col,
    )


# Set lines
fig = make_subplots(rows=2, cols=3, subplot_titles=VERSIONS)
root = Path(__file__).parent.parent.parent / "data" / "experiments" / "coverage"
x = list(range(0, 86400, 10))
for i in range(len(VERSIONS)):
    p = root / f"linux-{VERSIONS[i]}" / "SyzMeta"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "31,119,180", "SyzMeta")

    p = root / f"linux-{VERSIONS[i]}" / "SyzMeta-E-"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "255,127,14", "SyzMeta-E-")

    p = root / f"linux-{VERSIONS[i]}" / "SyzMeta-R-"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "44,160,44", "SyzMeta-R-")

    p = root / f"linux-{VERSIONS[i]}" / "SyzMeta-RE-"
    fs = p.rglob("*.log")
    lst2d = list()
    for f in fs:
        lst2d.append(get_cov_list(f))
    lower, upper, avg = get_lua(lst2d)
    set_subfig(fig, x, lower, upper, avg, (i // 3) + 1, (i % 3) + 1, "214,39,40", "SyzMeta-RE-")

# Set legend
fig.add_trace(go.Scatter(x=[0], y=[0], line=dict(color="rgb(31,119,180)"), showlegend=True, name="SyzMeta"), row=1, col=1)
fig.add_trace(go.Scatter(x=[0], y=[0], line=dict(color="rgb(255,127,14)"), showlegend=True, name="SyzMeta-E-"), row=1, col=1)
fig.add_trace(go.Scatter(x=[0], y=[0], line=dict(color="rgb(44,160,44)"), showlegend=True, name="SyzMeta-R-"), row=1, col=1)
fig.add_trace(go.Scatter(x=[0], y=[0], line=dict(color="rgb(214,39,40)"), showlegend=True, name="SyzMeta-RE-"), row=1, col=1)

fig.update_traces(mode="lines")
fig.update_layout(
    width=1000,
    height=600,
    font=dict(size=16, color="black"),
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.12,
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
    tickvals=[14400, 28800, 43200, 57600, 72000, 86400],
    ticktext=["4h", "8h", "12h", "16h", "20h", "24h"],
    range=[0, 86400],
)
fig.update_yaxes(
    showline=True,
    linecolor="black",
    gridcolor="lightgray",
    title_text="Coverage",
    title_standoff=0,
    tickvals=[0, 20000, 40000, 60000, 80000, 100000, 120000, 140000],
    range=[0, 140000],
)

outdir = Path(__file__).parent / "output" / "line.png"
fig.write_image(outdir, scale=2)
