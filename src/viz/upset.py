import pandas as pd
from plotly_upset.plotting import plot_upset
from pathlib import Path

# Actually I prefer SyzMeta or SyzMorphic :)
fuzzers = ["HEALER", "MOCK", "ACTOR", "SyzGPT", "KernelGPT", "MoonShine", "syzkaller", "OS-MFuzzer"]

# Get all issues
d = Path(__file__).parent.parent.parent / "data" / "experiments" / "explicits"
issues = set()
for fuzzer in fuzzers:
    f = d / f"{fuzzer}.txt"
    issues.update(f.read_text().splitlines())
issues.discard("")

# key: fuzzer, value: set of issues
issue_dict = {fuzzer: set() for fuzzer in fuzzers}
for fuzzer in fuzzers:
    f = d / f"{fuzzer}.txt"
    issue_dict[fuzzer] = set(f.read_text().splitlines())
    issue_dict[fuzzer].discard("")

# Create dataframe
df = pd.DataFrame(index=list(issues), columns=fuzzers, data=0)
for fuzzer in fuzzers:
    for issue in issue_dict[fuzzer]:
        df.at[issue, fuzzer] = 1

# Plotting
fig = plot_upset(
    dataframes=[df],
    legendgroups=["Number of Detected Issues"],
    marker_size=8,
    exclude_zeros=True,
    sorted_x="d",
    marker_colors=["gray"],
    column_widths=[0.25, 0.75],
)

fig.update_layout(
    width=1000,
    height=400,
    font=dict(size=14, color="black"),
    margin=dict(l=10, r=10, t=10, b=10),
)

outdir = Path(__file__).parent / "output"
outdir.mkdir(exist_ok=True)
fig.write_html(outdir / "upset.html")
fig.write_image(outdir / "upset.png", scale=2)
fig.write_image(outdir / "upset.pdf", scale=2)

print(f"Upset graph saved to {outdir}")
