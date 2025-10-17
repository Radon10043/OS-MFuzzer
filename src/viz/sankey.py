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
android_chunks      = df[df["kernel"] == "Android"]["doc chunks"].sum()
android_kmr         = df[df["kernel"] == "Android"]["KMR"].sum()
android_ekmr        = df[df["kernel"] == "Android"]["EKMR"].sum()
android_hq          = df[df["kernel"] == "Android"]["EKMR-high-quality"].sum()
android_lq_nocov    = df[df["kernel"] == "Android"]["EKMR-low-quality-nocov"].sum()
android_lq_highvio  = df[df["kernel"] == "Android"]["EKMR-low-quality-highvio"].sum()
# fmt:on

# Document Chunks -> Linux/Android -> KMR/No Consensus -> EKMR/Generation Failed -> High-Quality/Low-Quality (nocov/highvio) EKMRs
data = dict(
    node_labels=[
        "Document Chunks",
        "Document Chunks<br>(Linux)",
        "Document Chunks<br>(Android)",
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
        "rgba(0,114,178,0.6)",
        "rgba(0,158,115,0.6)",
        "rgba(204,121,167,0.8)",
        "rgba(153,153,153,0.8)",
        "rgba(230,159,0,0.8)",
        "rgba(153,153,153,0.8)",
        "rgba(86,180,233,0.8)",
        "rgba(117,112,179,0.8)",
        "rgba(153,153,153,0.8)",
    ],
    node_xs=[0.0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1.0, 1.0, 1.0],
    node_ys=[0.5, 0.25, 0.8, 0.45, 0.9, 0.45, 0.85, 0.3, 0.7, 0.95],
    link_sources=[0, 0, 1, 1, 2, 2, 3, 3, 3, 3, 5, 5, 5, 5, 5, 5],  # oh shit
    link_targets=[1, 2, 3, 4, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    link_values=[
        linux_chunks,
        android_chunks,
        linux_kmr,
        linux_chunks - linux_kmr,
        android_kmr,
        android_chunks - android_kmr,
        linux_ekmr,
        android_ekmr,
        linux_kmr - linux_ekmr,
        android_kmr - android_ekmr,
        linux_hq,
        android_hq,
        linux_lq_nocov,
        android_lq_nocov,
        linux_lq_highvio,
        android_lq_highvio,
    ],
    link_colors=[
        "rgba(213,94,0,0.4)",
        "rgba(213,94,0,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,158,115,0.4)",
        "rgba(0,158,115,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,158,115,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,158,115,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,158,115,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,158,115,0.4)",
        "rgba(0,114,178,0.4)",
        "rgba(0,158,115,0.4)",
    ],
)

annotations = [
    dict(   # Node label of [High-Quality EKMRs]
        x=1.22,
        y=0.7,
        text="High-Quality EKMRs",
        showarrow=False,
    ),
    dict(   # Node label of [Low-Quality EKMRs (No Coverage)]
        x=1.22,
        y=0.2,
        text="Low-Quality EKMRs<br>(No Coverage)",
        showarrow=False,
    ),
    dict(   # Node label of [Low-Quality EKMRs (High Violation Rate)]
        x=1.23,
        y=0.00,
        text="Low-Quality EKMRs<br>(High Violation Rate)",
        showarrow=False,
    ),
    dict(   # Flow value of [doc chunks] -> [doc chunks (linux)]
        x=0.1,
        y=0.7,
        text=str(linux_chunks),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [doc chunks] -> [doc chunks (android)]
        x=0.1,
        y=0.2,
        text=str(android_chunks),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [doc chunks (linux)] -> [KMR]
        x=0.27,
        y=0.65,
        text=str(linux_kmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [doc chunks (linux)] -> [No Consensus]
        x=0.27,
        y=0.53,
        text=str(linux_chunks - linux_kmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [doc chunks (android)] -> [KMR]
        x=0.27,
        y=0.1,
        text=str(android_kmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [doc chunks (android)] -> [No Consensus]
        x=0.35,
        y=0.01,
        text=str(android_chunks - android_kmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [KMR] -> [EKMR] (linux)
        x=0.6,
        y=0.7,
        text=str(linux_ekmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [KMR] -> [EKMR] (android)
        x=0.6,
        y=0.4,
        text=str(android_ekmr),
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [KMR] -> [Generation Failed] (linux/android)
        x=0.62,
        y=0.15,
        text=f"{linux_kmr - linux_ekmr} / {android_kmr - android_ekmr}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [EKMR] -> [High-Quality EKMRs] (linux)
        x=0.9,
        y=0.83,
        text=f"{linux_hq}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [EKMR] -> [High-Quality EKMRs] (android)
        x=0.9,
        y=0.65,
        text=f"{android_hq}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [EKMR] -> [Low-Quality EKMRs (No Coverage)] (linux)
        x=0.9,
        y=0.45,
        text=f"{linux_lq_nocov}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [EKMR] -> [Low-Quality EKMRs (No Coverage)] (android)
        x=0.9,
        y=0.2,
        text=f"{android_lq_nocov}",
        font=dict(size=12, shadow="auto"),
        showarrow=False,
    ),
    dict(   # Flow value of [EKMR] -> [Low-Quality EKMRs (High Violation Rate)] (linux/android)
        x=0.95,
        y=0.05,
        text=f"{linux_lq_highvio} / {android_lq_highvio}",
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
    width=1000,
    height=400,
    font=dict(size=16, color="black"),
    margin=dict(l=10, r=200, t=10, b=10),
)

outdir = Path(__file__).parent / "output"
outdir.mkdir(exist_ok=True)
fig.write_html(outdir / "sankey.html")
fig.write_image(outdir / "sankey.png", scale=2)
fig.write_image(outdir / "sankey.pdf", scale=2)

print(f"Sankey figure saved to {outdir}")
