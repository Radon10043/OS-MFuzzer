from pathlib import Path
import pandas as pd
import plotly.graph_objects as go


csvpath = Path(__file__).parent / "sankey.csv"
df = pd.read_csv(csvpath)

# fmt:off
doc_chunks          = df["doc chunks"].sum()
linux_chunks        = df[df["kernel"] == "Linux"]["doc chunks"].sum()
linux_kmr           = df[df["kernel"] == "Linux"]["KMR"].sum()
linux_ekmr          = df[df["kernel"] == "Linux"]["EKMR"].sum()
linux_hq            = df[df["kernel"] == "Linux"]["EKMR-high-quality"].sum()
linux_lq_nocov      = df[df["kernel"] == "Linux"]["EKMR-low-quality-nocov"].sum()
linux_lq_highvio    = df[df["kernel"] == "Linux"]["EKMR-low-quality-highvio"].sum()
# fmt:on

# Document Chunks -> KMR/No Consensus -> EKMR/Generation Failed -> High-Quality/Low-Quality (nocov/highvio) EKMRs
data = dict(
    node_labels=[
        "Document Chunks",
        "KMR",
        "No Consensus",
        "EKMR",
        "Generation Failed",
        # To put these label to the right of node, we add them manually as annotations
        # "High-Quality EKMRs",
        # "Low-Quality EKMRs<br>(No Coverage)",
        # "Low-Quality EKMRs<br>(High Violation Rate)",
    ],
    node_colors=[
        "rgba(213,94,0,0.6)",
        "rgba(204,121,167,0.8)",
        "rgba(153,153,153,0.8)",
        "rgba(230,159,0,0.8)",
        "rgba(153,153,153,0.8)",
        "rgba(86,180,233,0.8)",
        "rgba(117,112,179,0.8)",
        "rgba(153,153,153,0.8)",
    ],
    node_xs=[0.0, 0.33, 0.33, 0.66, 0.66, 1.0, 1.0, 1.0],
    node_ys=[0.5, 0.4, 0.95, 0.45, 0.9, 0.35, 0.7, 0.95],
    link_sources=[0, 0, 1, 1, 3, 3, 3],  # oh shit
    link_targets=[1, 2, 3, 4, 5, 6, 7],
    link_values=[
        linux_kmr,
        linux_chunks - linux_kmr,
        linux_ekmr,
        linux_kmr - linux_ekmr,
        linux_hq,
        linux_lq_nocov,
        linux_lq_highvio,
    ],
    link_colors=[
        "rgba(204,121,167,0.4)",
        "rgba(153,153,153,0.4)",
        "rgba(230,159,0,0.4)",
        "rgba(153,153,153,0.4)",
        "rgba(86,180,233,0.4)",
        "rgba(117,112,179,0.4)",
        "rgba(153,153,153,0.4)",
    ],
)

annotations = [
    dict(  # Node label of [High-Quality EKMRs]
        x=1.30,
        y=0.7,
        text="High-Quality EKMRs",
        showarrow=False,
    ),
    dict(  # Node label of [Low-Quality EKMRs (No Coverage)]
        x=1.3,
        y=0.2,
        text="Low-Quality EKMRs<br>(No Coverage)",
        showarrow=False,
    ),
    dict(  # Node label of [Low-Quality EKMRs (High Violation Rate)]
        x=1.3,
        y=0.00,
        text="Low-Quality EKMRs<br>(High Violation Rate)",
        showarrow=False,
    ),
    dict(  # Flow value of [doc chunks (linux)] -> [KMR]
        x=0.2,
        y=0.65,
        text=str(linux_kmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(  # Flow value of [doc chunks (linux)] -> [No Consensus]
        x=0.2,
        y=0.05,
        text=str(linux_chunks - linux_kmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(  # Flow value of [KMR] -> [EKMR] (linux)
        x=0.5,
        y=0.6,
        text=str(linux_ekmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(  # Flow value of [KMR] -> [Generation Failed] (linux)
        x=0.5,
        y=0.15,
        text=f"{linux_kmr - linux_ekmr}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(  # Flow value of [EKMR] -> [High-Quality EKMRs] (linux)
        x=0.9,
        y=0.7,
        text=f"{linux_hq}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(  # Flow value of [EKMR] -> [Low-Quality EKMRs (No Coverage)] (linux)
        x=0.9,
        y=0.35,
        text=f"{linux_lq_nocov}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(  # Flow value of [EKMR] -> [Low-Quality EKMRs (High Violation Rate)] (linux)
        x=0.95,
        y=0.03,
        text=f"{linux_lq_highvio}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
]

fig = go.Figure(
    data=go.Sankey(
        node=dict(
            pad=15,
            thickness=15,
            line=dict(color="black", width=0.5),
            label=data["node_labels"],
            color=data["node_colors"],
            x=data["node_xs"],
            y=data["node_ys"],
        ),
        link=dict(
            source=data["link_sources"],
            target=data["link_targets"],
            value=data["link_values"],
            color=data["link_colors"],
        ),
    ),
)

for ann in annotations:
    fig.add_annotation(ann)

fig.update_layout(
    width=800,
    height=400,
    font=dict(size=16, color="black"),
    margin=dict(l=10, r=200, t=10, b=10),
)

outdir = Path(__file__).parent / "output"
outdir.mkdir(exist_ok=True)
fig.write_html(outdir / "sankey.html")
fig.write_image(outdir / "sankey.png", scale=2)
fig.write_image(outdir / "sankey.pdf", scale=2)

print(f"Sankey graph saved to {outdir}")
